#!/usr/bin/env python3
"""Headless pipeline: vault articles -> russellbuzby.com Insights, one live per day.

Two stages, both run by the launchd job (com.russell.insights-publish) and both safe to
re-run:

  stage    Take the lowest-numbered unstaged article in the vault Posts/ folder and get it
           publication-ready with a headless Claude run (image sourced under the standing
           image rule, fact-check, humanise grader, read-aloud pre-pass, listing summary in
           Russell's voice). The result lands in the repo at src/content/queue/NNN-slug.md
           with its image beside it. Nothing is live yet. Deterministic gates verify the
           result; a failure leaves the article in the vault with a `stage_note` and a
           notification, and nothing is queued.
  release  Once per day: move the lowest-numbered queued article into src/content/insights
           dated today, commit and push (GitHub Pages rebuilds in about a minute), write the
           live URL back into the vault article and its LinkedIn teaser, move the vault
           article to Posts/Archive/, and notify.
  draft    Keep the queue fed. While fewer than three articles are in hand, take the next topic of
           the freshest weekly brief (Research/YYYY-MM-DD LinkedIn post notes.md) and have a
           headless Claude run draft the article and its LinkedIn teaser under the
           /linkedin-to-article skill. One topic per run; the next run stages what it wrote. A topic
           the publication screen catches is skipped before any drafting and noted in notes.md.
           The screen is a private note in the vault, kept out of this public repo on purpose.
  run      stage (bounded), release, then draft.  status  prints the queue.

Every run starts by finishing the vault record of any release that could not write it back: macOS
sometimes refuses the job a read of the iCloud vault, and .pipeline/published.json remembers what
went live so an article is never queued a second time. An unreadable vault is logged and notified,
never taken for an empty one.

Releases happen on weekdays only. Controls: `hold: true` in a vault article's frontmatter keeps it out of the pipeline;
a file named PAUSE in .pipeline/ stops releases and one named NO-DRAFT stops drafting; --dry-run shows what would happen.
Stdlib only. Runs on the logged-in Claude subscription (never API keys).
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

HOME = Path.home()
REPO = Path(__file__).resolve().parent.parent
VAULT = HOME / "Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault"
POSTS = VAULT / "Automation/Projects/Articles/Posts"
ARCHIVE = POSTS / "Archive"
IMAGES = VAULT / "Automation/Projects/Articles/Images"
TEASERS = VAULT / "Automation/Projects/LinkedIn posts/Posts"
QUEUE = REPO / "src/content/queue"
INSIGHTS = REPO / "src/content/insights"
ASSETS = REPO / "src/assets/insights"
STATE = REPO / ".pipeline"
LOG = STATE / "pipeline.log"
LOCK = Path("/tmp/insights-pipeline.lock")
RELEASE_STAMP = STATE / "last_release"      # YYYY-MM-DD
PAUSE = STATE / "PAUSE"
LEDGER = STATE / "published.json"           # vault filename -> {url, date, slug, recorded}, written straight after each push
NO_DRAFT = STATE / "NO-DRAFT"
BRIEF_LEDGER = STATE / "briefs.json"        # "<brief date>#<topic>" -> {outcome, detail, article, date, tries}
ARTICLES = VAULT / "Automation/Projects/Articles"
RESEARCH = VAULT / "Research"
DRAFT_TIMEOUT_S = 5400   # 90 min per topic
DRAFT_STOCK = 3          # draft only while fewer than this many articles are queued or waiting in Posts
BRIEF_MAX_AGE_DAYS = 14  # a weekly brief goes stale; leftover topics of an older one are never drafted
SCREEN = ARTICLES / "publication-screen.md"  # private note in the vault: what never goes out, one `re:` pattern per line
CLAUDE_BIN = HOME / ".local/bin/claude"
GRADER = HOME / ".agents/skills/humanise/grade.py"
READALOUD = HOME / ".agents/skills/read-aloud/read_aloud.py"
CHECK_BLURBS = REPO / "scripts/check_blurbs.py"
SITE = "https://russellbuzby.com"
STAGE_TIMEOUT_S = 2700   # 45 min per article
MAX_STAGE_PER_RUN = 2    # scheduled runs; `stage --all` lifts it
MAX_QUEUE = 10           # do not stage more than this many ahead
MAX_ATTEMPTS = 2         # Claude tries per article before it is parked with hold: true for Russell
THEMES = ["Emergency Management & Resilience", "AI in Government", "Defence", "Change & Transformation"]
TAG_TO_THEME = [
    ("emergency", THEMES[0]), ("bushfire", THEMES[0]), ("wildfire", THEMES[0]), ("resilience", THEMES[0]),
    ("disaster", THEMES[0]), ("fire", THEMES[0]), ("ai", THEMES[1]), ("artificial intelligence", THEMES[1]),
    ("automation", THEMES[1]), ("defence", THEMES[2]), ("military", THEMES[2]),
    ("change", THEMES[3]), ("transformation", THEMES[3]), ("reform", THEMES[3]), ("public sector", THEMES[3]),
    ("leadership", THEMES[3]), ("workforce", THEMES[3]),
]
ALLOWED_TOOLS = [
    "WebSearch", "WebFetch", "Read", "Edit", "Write", "Glob", "Grep", "Agent", "Skill",
    "Bash(python3:*)", "Bash(/usr/bin/python3:*)", "Bash(/opt/homebrew/bin/python3:*)",
    "Bash(curl:*)", "Bash(ls:*)", "Bash(cat:*)", "Bash(grep:*)", "Bash(find:*)", "Bash(mkdir:*)",
    "Bash(cp:*)", "Bash(mv:*)", "Bash(file:*)", "Bash(sips:*)",
]

# ----------------------------------------------------------------------------- helpers

def log(msg: str) -> None:
    STATE.mkdir(exist_ok=True)
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line)
    with LOG.open("a") as f:
        f.write(line + "\n")


def obsidian_url(path: Path) -> str:
    """obsidian:// link that opens a vault file when the notification is clicked."""
    import urllib.parse
    rel = path.relative_to(VAULT).as_posix()
    return "obsidian://open?vault=Vault&file=" + urllib.parse.quote(rel)


def obsidian_url_repo(path: Path) -> str:
    import urllib.parse
    rel = path.relative_to(REPO / "src/content").as_posix()
    return "obsidian://open?vault=content&file=" + urllib.parse.quote(rel)


def notify(title: str, message: str, open_url: str = "") -> None:
    tn = "/opt/homebrew/bin/terminal-notifier"
    if not Path(tn).exists():
        return
    cmd = [tn, "-title", title, "-message", message, "-group", "com.russell.insights-publish", "-ignoreDnD"]
    if open_url:
        cmd += ["-open", open_url]
    try:
        subprocess.run(cmd, timeout=30, capture_output=True)
    except Exception as e:  # best effort
        log(f"notify failed: {e}")


def split_fm(text: str) -> tuple[str, str]:
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("no frontmatter")
    return m.group(1), m.group(2)


def unquote(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        inner = v[1:-1]
        return inner.replace('\\"', '"') if v[0] == '"' else inner
    return v


def parse_fm(fm: str) -> dict:
    data: dict = {}
    key = None
    for line in fm.splitlines():
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m and not line.startswith((" ", "\t")):
            key, val = m.group(1), m.group(2).strip()
            data[key] = [] if val == "" else unquote(val)
        elif key is not None and re.match(r"^\s*-\s+", line):
            if not isinstance(data.get(key), list):
                data[key] = [data[key]] if data.get(key) else []
            data[key].append(unquote(re.sub(r"^\s*-\s+", "", line)))
    return data


def set_fm_field(text: str, key: str, value: str) -> str:
    """Set or add a scalar frontmatter field, keeping everything else byte for byte."""
    fm, body = split_fm(text)
    if re.search(rf"^{key}:", fm, re.M):
        fm = re.sub(rf"^{key}:.*$", f"{key}: {value}", fm, count=1, flags=re.M)
    else:
        fm += f"\n{key}: {value}"
    return f"---\n{fm}\n---\n{body}"


def yq(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def curly(s: str) -> str:
    s = re.sub(r'(^|[\s(\[])"', "\\1\u201c", s)
    s = s.replace('"', "\u201d")
    s = re.sub(r"(^|[\s(\[])'", "\\1\u2018", s)
    return s.replace("'", "\u2019")


def normalise(s: str) -> str:
    for bad, good in (("\u2011", "-"), ("\u00a0", " "), ("\u200b", ""), ("\u00ad", ""), ("\u2014", ":")):
        s = s.replace(bad, good)
    return s


def bullet_references(body: str) -> str:
    """Canonicalise a '## References' section to markdown list items.

    The site renders the small numbered reference block from '- ' items only
    (src/lib/refs.ts); a draft that writes the entries as blank-line-separated
    paragraphs would otherwise fall through to full-size body text.
    """
    m = re.search(r"^## References\s*$", body, re.M)
    if not m:
        return body
    head, tail = body[: m.end()], body[m.end():]
    after = ""
    nxt = re.search(r"^## ", tail, re.M)
    if nxt:
        after, tail = tail[nxt.start():], tail[: nxt.start()]
    lines = tail.split("\n")
    if any(l.lstrip().startswith("- ") for l in lines):
        return body
    entries, buf = [], []
    for l in lines:
        if l.strip():
            buf.append(l.strip())
        elif buf:
            entries.append(" ".join(buf))
            buf = []
    if buf:
        entries.append(" ".join(buf))
    if not entries:
        return body
    return head + "\n" + "\n".join("- " + e for e in entries) + "\n" + ("\n" + after if after else "")


def prose_only(body: str) -> str:
    """The article without its reference list, which is what the grader's gates are for.

    House rule (linkedin-to-article skill): always grade the body only, references stripped. Counting
    them pulled vocabulary-diversity under its line for two articles whose prose passed 63/63 (085 and
    086, 5 Oct 2026), a failure the prep run could not see because it grades the prose alone.
    """
    m = re.search(r"^#{2,3}\s*References\s*$", body, re.M)
    return body[: m.start()].rstrip() + "\n" if m else body


def screen_hits(text: str) -> list[str]:
    """Terms of the publication screen found in the text, in order of first appearance.

    The screen is a private note in the vault, one `re:` pattern per line (case-sensitive unless it
    starts with `(?i)`). A missing or empty screen is an error, so the run stops and says so: an
    unreadable screen must never mean that nothing is screened.
    """
    patterns = [line[3:].strip() for line in read_vault(SCREEN).splitlines() if line.startswith("re:") and line[3:].strip()]
    if not patterns:
        raise VaultUnreadable(f"{SCREEN.name} holds no patterns")
    found: list[tuple[int, str]] = []
    for pat in patterns:
        flags = re.I if pat.startswith("(?i)") else 0
        found += [(m.start(), m.group(0)) for m in re.finditer(r"\b(?:" + pat.replace("(?i)", "", 1) + r")\b", text, flags)]
    seen: list[str] = []
    for _, term in sorted(found):
        if term.lower() not in (s.lower() for s in seen):
            seen.append(term)
    return seen


def slugify(title: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()[:80].rstrip("-")


def number_of(path: Path) -> int:
    m = re.match(r"^(\d{3})-", path.name)
    return int(m.group(1)) if m else 10**6


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True)


def online() -> bool:
    try:
        import urllib.request
        urllib.request.urlopen("https://api.github.com", timeout=10)
        return True
    except Exception:
        return False


def caption_from_credit(credit: str) -> str:
    """Fallback public caption from a vault provenance record: 'Photo by X on Pexels (...)' -> 'Photo: X on Pexels.'"""
    head = re.split(r"\s+-\s+|\. ", credit, maxsplit=1)[0]
    head = re.sub(r"\s*\((?:https?://)[^)]*\)", "", head)
    head = re.sub(r",\s*(Pexels licence|free to use|Commonwealth of Australia Copyright|Defence Imagery terms of use|All Rights Reserved)[^,]*", "", head, flags=re.I)
    head = re.sub(r"^Photo by\s+", "Photo: ", head).strip().rstrip(".,")
    return (head + ".") if head and len(head.split()) <= 25 else ""


# ----------------------------------------------------------------------------- vault access

class VaultUnreadable(Exception):
    """macOS refused a read of the vault. Nothing can be assumed about it this run, least of all that it is empty."""


def read_vault(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        raise VaultUnreadable(f"cannot read {path.name}: {e.strerror}") from e


def list_vault(folder: Path, number: str = "") -> list[Path]:
    """Numbered notes in a vault folder, lowest first; only those for one article number when given.

    Lists the folder directly. Path.glob() swallows PermissionError, so a vault the job was refused
    came back as an empty one and was logged as "0 candidate(s)" for eleven days (24 Sep to 4 Oct 2026).
    """
    try:
        names = os.listdir(folder)
    except OSError as e:
        raise VaultUnreadable(f"cannot list {folder.name}/: {e.strerror}") from e
    pat = re.compile("^" + (re.escape(number) if number else "[0-9]{3}") + r"-.*\.md$")
    return sorted((folder / n for n in names if pat.match(n)), key=number_of)


def claim_vault() -> None:
    """Make this run's first vault read now, before anything executes git.

    /usr/bin/python3 and /usr/bin/git are one file under two names (the Xcode tool shim, 78 hard
    links) and only the python3 name holds Full Disk Access. macOS settles which name a process
    answers to at its first protected read: one that has already run git is taken for /usr/bin/git
    and refused for good, and one let in stays in whatever it runs afterwards. The pull at the top of
    every run is what blinded this job from 24 Sep to 5 Oct 2026. A refusal here means some other
    process ran git in the last few seconds; only a fresh run can try again.
    """
    list_vault(POSTS)


def vault_alert(e: VaultUnreadable) -> None:
    log(f"VAULT UNREADABLE ({e}); staging and vault records wait for the next run")
    notify("Insights pipeline ⚠️", f"macOS would not let the job read the vault ({e}). Nothing staged; the next slot retries.")


# ----------------------------------------------------------------------------- queue views

def slug_of(title: str) -> str:
    """The URL slug a vault title publishes under."""
    return slugify(normalise(curly(str(title))))


def live_copy(slug: str) -> Path | None:
    """The insights file already using this slug, under any date and pulled or not; None if there is none."""
    hits = sorted(INSIGHTS.glob(f"[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]-{slug}.md")) if slug else []
    return hits[-1] if hits else None


def ledger() -> dict:
    """Releases by vault filename: {url, date, slug, recorded}. `recorded` turns true once the vault says so too."""
    try:
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_ledger(book: dict) -> None:
    STATE.mkdir(exist_ok=True)
    LEDGER.write_text(json.dumps(book, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def vault_survey() -> tuple[list[Path], list[tuple[Path, Path]]]:
    """Numbered vault articles still to stage (lowest first), and those held back because their title is already live.

    Anything the ledger shows as released is left to reconcile(). A title that is already on the site
    with no ledger entry may or may not be the same article, so it is never queued and a person decides.
    """
    todo, clashes = [], []
    queued = {number_of(p) for p in QUEUE.glob("*.md")} if QUEUE.exists() else set()
    released = ledger()
    for p in list_vault(POSTS):
        d = parse_fm(split_fm(read_vault(p))[0])
        if p.name in released:
            continue
        if str(d.get("hold", "")).lower() == "true":
            continue
        if d.get("status") == "published" or d.get("url"):
            continue
        if number_of(p) in queued:
            continue
        live = live_copy(slug_of(d.get("title", "")))
        if live:
            clashes.append((p, live))
            continue
        todo.append(p)
    return todo, clashes


def vault_candidates() -> list[Path]:
    """Numbered vault articles not yet queued or published, not on hold, lowest number first."""
    return vault_survey()[0]


def queued() -> list[Path]:
    return sorted(QUEUE.glob("[0-9][0-9][0-9]-*.md"), key=number_of) if QUEUE.exists() else []


# ----------------------------------------------------------------------------- stage

STAGE_PROMPT = """You are preparing one article for publication on russellbuzby.com. This is a headless run \
(launchd com.russell.insights-publish); Russell is not at the keyboard, and nothing you do goes live: the \
result is queued and released by a separate deterministic step. Work only on this article.

Article: {article}
Images folder: {images}
Voice file: {voice}
Standing rules: ~/.claude/CLAUDE.md (image sourcing, fact-check, humanise grader, read-aloud, curly quotes, \
no em dashes, Australian English). The screen at {screen} sets out what never goes out under Russell's name and \
is absolute: if this article falls under it, write `stage_note: "SCREENED: <what>"` and stop. Never reword around it.

{stage_note}Do these in order and stop if a step cannot be completed honestly:

1. IMAGE. If the frontmatter `image` is TBD, or names a file that does not exist in the images folder, source \
one under the standing image rule: NSW RFS Flickr (pre-2019 archive) is the required primary source for fire, \
bushfire or emergency topics; Pexels free-use for everything else, and as the documented fallback. Download it \
to the images folder as `{number}-<short-slug>.jpg` at 1600px on the long side (use sips to resize if needed), \
and write `image:` (the filename), `image_credit:` (the full provenance record for the vault: photographer or \
agency, the asset URL, the licence, why it was chosen, any resize) and `image_caption:` (the PUBLIC caption that \
prints under the photo on the site: one line, at most 20 words, of the form "Photo: <photographer or agency>, \
<source>." plus at most one short phrase of what or when, e.g. "Photo: NSW Rural Fire Service, via the NSW RFS \
Flickr archive. Pre-deployment briefing, July 2017." Never put URLs, licence terms, resize notes, HTTP results or \
selection reasoning in the caption) in the frontmatter. Never invent an asset ID or a credit; if no usable image can be verified, write \
`stage_note: "IMAGE NOT SOURCED: <why>"` in the frontmatter and stop.
2. FACT-CHECK. Run the /fact-check skill over the article body. Fix anything it finds against the sources \
in the reference list; if a load-bearing claim cannot be verified, write `stage_note:` explaining it and stop.
3. GRADER. Run `python3 {grader} "{article}"` and fix every failing hard gate in the body (not the \
frontmatter), re-running until every hard gate passes (ignore `no-markdown-headings`; advisory warnings are \
fine). Keep the argument intact; fix the prose. Two gates need a particular method: `vocabulary-diversity` \
(type-token ratio under 0.40) is cleared by cutting sentences that repeat vocabulary already used, trimming \
the body by 5 to 10 per cent rather than swapping in synonyms; `no-triad-density` is cleared by turning \
lists of three into two items or four, except inside verbatim quotations. Do not stop at 61/63: a hard gate \
left failing means the article is not queued.
4. READ-ALOUD. Run `python3 {readaloud} "{article}"` and fix the high-confidence flags where a fix does not \
break a grader gate; re-run the grader after.
5. SUMMARY. Write a `summary:` field in the frontmatter: one or two sentences, 25 to 45 words, stating the \
article's argument in Russell's voice as he would put it to a senior public servant. Only facts the article \
carries. Australian spelling, curly quotes, no em dashes, no rhetorical questions, no lists of three, no \
"not X but Y", none of: delve, tapestry, leverage, utilise, surface (verb), land (verb), load-bearing, \
sharp, bank (verb), playbook, navigate, unpack, underscore, highlight, crucial, robust, landscape, explores, \
examines, argues that. Do not open with "The" plus an abstract noun.
6. THEME. Write `theme:` with exactly one of: {themes}.
7. Set `status: ready`. Do not change `title`, `date`, `references` or `tags`, and do not move the file.

Report in five lines: image source, fact-check result, grader score, read-aloud flags left, summary."""


def stage_one(article: Path, dry: bool) -> bool:
    """Run the headless Claude prep on one vault article, then verify and copy it into the queue."""
    n = number_of(article)
    d = parse_fm(split_fm(read_vault(article))[0])
    log(f"stage {article.name}: status={d.get('status')} image={d.get('image')}")
    if d.get("status") != "ready":
        if dry:
            print(f"  would run Claude prep on {article.name}")
            return False
        if not CLAUDE_BIN.exists():
            log("claude binary missing; cannot stage")
            return False
        note = str(d.get("stage_note", "")).strip()
        prompt = STAGE_PROMPT.format(
            stage_note=(f"A previous attempt failed its gates: {note}. Fix that first.\n\n" if note else ""),
            article=str(article), images=str(IMAGES), number=f"{n:03d}", screen=str(SCREEN),
            voice=str(VAULT / "Automation/Projects/Articles/voice.md"),
            grader=str(GRADER), readaloud=str(READALOUD), themes=", ".join(f'"{t}"' for t in THEMES),
        )
        cmd = ["/usr/bin/caffeinate", "-i", str(CLAUDE_BIN), "-p", prompt,
               "--model", "claude-opus-5", "--permission-mode", "acceptEdits",
               "--allowedTools"] + ALLOWED_TOOLS
        env = dict(os.environ, PATH=f"{HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
        try:
            res = subprocess.run(cmd, cwd=str(HOME), env=env, timeout=STAGE_TIMEOUT_S, capture_output=True, text=True)
        except subprocess.TimeoutExpired:
            log(f"stage TIMEOUT on {article.name}")
            notify(f"Insights: {n:03d} timed out", f"{d.get('title', article.name)}: Claude run hit 45 min; will retry next slot · click to open", open_url=obsidian_url(article))
            return False
        log(f"claude exit {res.returncode}; tail: {(res.stdout or '').strip()[-300:]}")
        if res.returncode != 0:
            err = (res.stderr or "").strip()[-300:]
            log(f"stderr: {err}")
            if re.search(r"log ?in|OAuth|authentication|401", err + (res.stdout or ""), re.I):
                notify("Insights pipeline ⚠️", "Claude login has expired; run `claude /login` in a terminal")
            return False
        d = parse_fm(split_fm(read_vault(article))[0])

    # ---- deterministic gates on what Claude left behind
    problems = []
    if d.get("stage_note"):
        problems.append(f"stage_note: {d['stage_note'][:160]}")
    if d.get("status") != "ready":
        problems.append(f"status is {d.get('status')!r}, not ready")
    img = IMAGES / str(d.get("image", ""))
    if not d.get("image") or str(d.get("image")).upper() == "TBD" or not img.exists():
        problems.append(f"image missing: {d.get('image')}")
    credit = str(d.get("image_credit", ""))
    if not credit or credit.upper().startswith(("NOT YET", "TBD")):
        problems.append("image_credit unset")
    caption = str(d.get("image_caption", "")).strip() or caption_from_credit(credit)
    if not caption or len(caption.split()) > 25 or re.search(r"http|resized|brief|attempt|licen[cs]e|variant|preview", caption, re.I):
        problems.append(f"image_caption unusable: {caption[:80]!r}")
    summary = str(d.get("summary", "")).strip()
    if not (18 <= len(summary.split()) <= 50):
        problems.append(f"summary is {len(summary.split())} words")
    if "'" in summary or '"' in summary or "\u2014" in summary or "?" in summary:
        problems.append("summary typography (straight quote, dash or question)")
    if d.get("theme") not in THEMES:
        problems.append(f"theme not set: {d.get('theme')}")
    live = live_copy(slug_of(d.get("title", "")))
    if live:
        problems.append(f"already on the site as {live.name}")
    # grader on the body
    body = split_fm(read_vault(article))[1]
    flagged = screen_hits("\n".join([str(d.get("title", "")), summary, prose_only(body)]
                                   + [read_vault(t) for t in list_vault(TEASERS, f"{n:03d}")]))
    if flagged:
        problems.append("screen: " + ", ".join(flagged))
    tmp = STATE / f"grade-{n:03d}.md"
    STATE.mkdir(exist_ok=True)
    tmp.write_text(prose_only(body), encoding="utf-8")
    try:
        g = subprocess.run([sys.executable, str(GRADER), str(tmp)], capture_output=True, text=True, timeout=300)
        js = json.loads(g.stdout[g.stdout.find("{"):])
        rate = js.get("pass_rate", "0/0")
        passed, total = (int(x) for x in rate.split("/"))
        fails = [x["text"] for x in js.get("expectations", []) if x.get("passed") is False and x["text"] != "no-markdown-headings"]
        if fails:
            problems.append(f"grader {rate}: " + ", ".join(fails[:4]))
    except Exception as e:
        problems.append(f"grader could not run: {e}")
    finally:
        tmp.unlink(missing_ok=True)

    if problems:
        attempts = int(str(d.get("stage_attempts", "0")) or 0) + 1
        why = " | ".join(problems)
        log(f"stage gates FAILED (attempt {attempts}): {why}")
        text = read_vault(article)
        text = set_fm_field(text, "stage_note", yq(f"GATES FAILED {dt.date.today().isoformat()} (attempt {attempts}): {why}"))
        text = set_fm_field(text, "stage_attempts", str(attempts))
        if d.get("status") == "ready":
            text = set_fm_field(text, "status", "draft")
        parked = attempts >= MAX_ATTEMPTS or bool(flagged)   # a screen hit gets no second try: a retry would only reword around it
        if parked:
            text = set_fm_field(text, "hold", "true")
        article.write_text(text, encoding="utf-8")
        head = (f"{n:03d} held by the screen" if flagged else f"{n:03d} parked after {attempts} tries" if parked
                else f"{n:03d} held back (try {attempts} of {MAX_ATTEMPTS})")
        notify(f"Insights: {head}", f"{d.get('title', article.name)}: {why}"[:230] + (" · click to open" if len(why) < 200 else " · click to open"),
               open_url=obsidian_url(article))
        return False

    # ---- copy into the queue (and clear any old stage_note in the vault file)
    if d.get("stage_note") or d.get("stage_attempts"):
        vt = read_vault(article)
        vt = re.sub(r"^(stage_note|stage_attempts):.*\n?", "", vt, flags=re.M)
        article.write_text(vt, encoding="utf-8")
    QUEUE.mkdir(parents=True, exist_ok=True)
    title = normalise(curly(str(d["title"])))
    slug = slug_of(d["title"])
    ext = img.suffix.lower() or ".jpg"
    qmd = QUEUE / f"{n:03d}-{slug}.md"
    qimg = QUEUE / f"{n:03d}-{slug}{ext}"
    shutil.copy2(img, qimg)
    refs = d.get("references") or []
    body = normalise(body).strip()
    if refs and not re.search(r"^## References\s*$", body, re.M):
        body += "\n\n## References\n" + "\n".join("- " + normalise(r) for r in refs) + "\n"
    body = bullet_references(body)
    front = ["---", f"title: {yq(title)}", f"summary: {yq(normalise(curly(summary)))}", "themes:", f"  - {yq(d['theme'])}",
             f"image: ./{qimg.name}", f"imageCredit: {yq(normalise(curly(caption)))}", f"queue: {n}", f"vault: {yq(article.name)}", "---", ""]
    qmd.write_text("\n".join(front) + body + "\n", encoding="utf-8")
    git("add", str(qmd), str(qimg))
    git("commit", "-q", "-m", f"Queue: {title}")
    log(f"queued {qmd.name}")
    notify(f"Insights: {n:03d} queued", f"{title} · click to open the queued copy", open_url=obsidian_url_repo(qmd))
    return True


def stage(dry: bool, all_: bool = False) -> int:
    try:
        cands, clashes = vault_survey()
    except VaultUnreadable as e:
        vault_alert(e)
        return 0
    q = queued()
    log(f"stage: {len(cands)} candidate(s) in vault, {len(q)} queued")
    for p, live in clashes:
        log(f"{p.name} has the title of {live.name}, already on the site; not queued")
        if not dry:
            notify(f"Insights: {number_of(p):03d} not queued", f"Same title as {live.name}, already on the site. Retitle it, or mark it published · click to open",
                   open_url=obsidian_url(p))
    room = MAX_QUEUE - len(q)
    if room <= 0:
        log("queue full; not staging")
        return 0
    limit = len(cands) if all_ else MAX_STAGE_PER_RUN
    done = 0
    for a in cands[:min(limit, room)]:
        try:
            if stage_one(a, dry):
                done += 1
        except VaultUnreadable as e:
            vault_alert(e)
            break
    return done


# ----------------------------------------------------------------------------- vault record

def set_teaser_url(number: str, url: str) -> None:
    """Fill article_url on this article's LinkedIn teaser, wherever it has been filed."""
    for folder in (TEASERS, TEASERS / "Archive"):
        try:
            teasers = list_vault(folder, number)
        except VaultUnreadable:
            if folder == TEASERS:
                raise
            continue
        for t in teasers:
            old = read_vault(t)
            new = set_fm_field(old, "article_url", url)
            if new == old:
                continue
            try:
                t.write_text(new, encoding="utf-8")
            except OSError as e:
                raise VaultUnreadable(f"cannot write {t.name}: {e.strerror}") from e
            log(f"teaser {t.name}: article_url set")


def write_back(name: str, url: str, iso: str) -> None:
    """Record a release in the vault: url and status on the article, the article into Archive/, the link on its teaser.

    Safe to repeat. The Posts copy goes only after the Archive copy is written, so a run that dies
    part-way leaves the next one something to finish.
    """
    src, dest = POSTS / name, ARCHIVE / name
    try:
        here = src if src.exists() else dest if dest.exists() else None
    except OSError as e:
        raise VaultUnreadable(f"cannot find {name}: {e.strerror}") from e
    if here is None:
        log(f"vault: {name} is in neither Posts/ nor Archive/; teaser only")
    else:
        old = read_vault(here)
        text = old
        for key, value in (("url", url), ("status", "published"), ("published_date", iso)):
            text = set_fm_field(text, key, value)
        if here == src or text != old:
            try:
                ARCHIVE.mkdir(exist_ok=True)
                dest.write_text(text, encoding="utf-8")
                if here == src:
                    src.unlink()
            except OSError as e:
                raise VaultUnreadable(f"cannot archive {name}: {e.strerror}") from e
            log(f"vault: {name} -> Archive/ with url")
    set_teaser_url(name[:3], url)


def reconcile(dry: bool) -> None:
    """Finish the vault record of every release the ledger shows as unrecorded, or as back in Posts.

    A release that could not write back used to leave its article in Posts looking unpublished, and
    the next run would have queued it and sent it out a second time (5 Oct 2026).
    """
    book = ledger()
    for name, rec in book.items():
        try:
            pending = not rec.get("recorded") or (POSTS / name).exists()
        except OSError as e:
            raise VaultUnreadable(f"cannot find {name}: {e.strerror}") from e
        if not pending:
            continue
        insight = INSIGHTS / f"{rec['date']}-{rec['slug']}.md"
        if not insight.exists() or str(parse_fm(split_fm(insight.read_text(encoding="utf-8"))[0]).get("draft", "")).lower() == "true":
            log(f"{name} was released and has since been pulled from the site; vault record left alone")
            continue
        if dry:
            print(f"  would finish the vault record for {name}")
            continue
        write_back(name, rec["url"], rec["date"])
        rec["recorded"] = True
        save_ledger(book)


# ----------------------------------------------------------------------------- release

def release(dry: bool, force: bool = False) -> bool:
    today = dt.date.today()
    iso = today.isoformat()
    if PAUSE.exists():
        log("PAUSE file present; no release")
        return False
    if not force and today.weekday() >= 5:
        log("weekend; no release")
        return False
    if not force and RELEASE_STAMP.exists() and RELEASE_STAMP.read_text().strip() == iso:
        log("already released today")
        return False
    q = queued()
    if not q:
        log("queue empty; nothing to release")
        return False
    # an article never goes out twice: pass over anything queued whose slug is already on the site
    qmd = None
    for cand in q:
        live = live_copy(cand.stem[4:])
        if live is None:
            qmd = cand
            break
        log(f"{cand.name} is already live as {live.name}; not released again")
        if not dry:
            notify("Insights pipeline ⚠️", f"{cand.name} is already on the site as {live.name}; delete the queued copy")
    if qmd is None:
        return False
    text = qmd.read_text(encoding="utf-8")
    d = parse_fm(split_fm(text)[0])
    slug = qmd.stem[4:]
    qimg = QUEUE / re.sub(r"^\./", "", str(d["image"]))
    out_md = INSIGHTS / f"{iso}-{slug}.md"
    out_img = ASSETS / f"{slug}{qimg.suffix}"
    url = f"{SITE}/{iso[:4]}/{iso[5:7]}/{iso[8:10]}/{slug}/"
    log(f"release {qmd.name} -> {url}")
    if dry:
        print(f"  would publish {qmd.name} as {out_md.name}, image {out_img.name}")
        return False
    if not online():
        log("offline; leaving the release to the next slot")
        return False

    # rewrite frontmatter for the site collection
    fm, body = split_fm(text)
    fm = re.sub(r"^image:.*$", f"image: ../../assets/insights/{out_img.name}", fm, flags=re.M)
    fm = re.sub(r"^queue:.*\n?", "", fm, flags=re.M)
    fm = re.sub(r"^vault:.*\n?", "", fm, flags=re.M)
    fm = fm.rstrip() + f"\ndate: {iso}"
    body = bullet_references(body)
    if re.search(r"^## References\s*$", body, re.M) and not re.search(r"^- ", body, re.M):
        log("references section is not a list; release aborted")
        notify("Insights pipeline \u26a0\ufe0f", f"{qmd.name}: references would render as body text; release skipped")
        return False
    ASSETS.mkdir(parents=True, exist_ok=True)
    shutil.move(str(qimg), out_img)
    out_md.write_text(f"---\n{fm}\n---\n{body}", encoding="utf-8")
    qmd.unlink()
    git("add", "-A")
    c = git("commit", "-q", "-m", f"Publish: {d['title']}")
    p = git("push", "-q")
    if p.returncode != 0:
        log(f"push failed: {p.stderr.strip()[-300:]}")
        notify("Insights pipeline ⚠️", "Push to GitHub failed; the article is committed locally. Run scripts/publish.sh when online.")
        return False
    RELEASE_STAMP.write_text(iso)
    log(f"pushed; live in about a minute at {url}")
    vault_name = str(d.get("vault", ""))
    if vault_name:
        book = ledger()
        book[vault_name] = {"url": url, "date": iso, "slug": slug, "recorded": False}
        save_ledger(book)
    notify("Insights published", str(d["title"]), open_url=url)

    # the vault record comes last: macOS can refuse the read, and the ledger lets the next run finish it
    try:
        if vault_name:
            reconcile(dry=False)
        else:
            set_teaser_url(qmd.stem[:3], url)
    except VaultUnreadable as e:
        log(f"vault record deferred ({e}); the next run retries it")
        notify("Insights pipeline ⚠️", f"{d['title']} is live, but the vault could not be updated ({e}). The next run retries.")
    return True


# ----------------------------------------------------------------------------- draft

DRAFT_PROMPT = """You are drafting one article, and its LinkedIn teaser, for russellbuzby.com from one topic of Russell's \
weekly research brief. This is a headless run (launchd com.russell.insights-publish). Russell is not at the keyboard and \
will not read the draft before a second headless run fact-checks it again, sources its image and queues it for release, so \
what you write is what goes out under his name. Work on this topic only.

Brief: {brief}
Topic: Topic {n}: {heading}
Article: {posts}/{number}-<short-slug>.md
Teaser: {teasers}/{number}-<the same short-slug>.md
Result file: {result}

Follow the /linkedin-to-article skill for the workflow, the Articles project files (context.md, voice.md, notes.md in \
{articles}) for voice and conventions, and the standing rules in ~/.claude/CLAUDE.md. In order, stopping where a step says stop:

1. SCREEN. Read {screen}. It sets out what never goes out under Russell's name, and it is absolute. If the topic falls \
under it, or cannot be argued without that material, write the result file with outcome "screened" and stop. Never draft \
a version that only avoids the listed words.
2. OVERLAP AND TIMELINESS (skill Step 2.5). Check this topic's specific hooks against the last 12 `Articles produced` entries \
in notes.md and against those articles' `source_notes`. If it is spent, or its news hook has gone stale and no argument \
outlives it, bank the unused material in notes.md, write the result file with outcome "cut" and stop. If it is pivotable, \
pivot to unused material and record the exclusions in `source_notes`.
3. VERIFY FIRST. Before drafting, build a claim sheet in {articles}/Research/ (one file: every claim with its URL and a \
verification status, and a research-flags section at the end) from the digests and from primary sources. The brief is a \
lead, never a source: briefs have carried invented authors, wrong figures and items that do not exist. Draft only from what \
the claim sheet verifies.
4. ARTICLE. Write it to the article path: 1,100 to 1,300 words in the body (ceiling 1,500), frontmatter as the skill sets out \
(title, `status: draft`, date, `image: TBD`, word_count, references, tags, `linkedin_source: "Topic {n} of `{brief_name}`"`, \
source_notes), no subheadings, then `## References` as `- ` list items in APA style. Vary the title construction against the \
last five. Hyperlink any cross-reference to its live russellbuzby.com URL after checking it resolves.
5. TEASER. Write it to the teaser path: a no-graphic LinkedIn post of 150 to 280 words in Russell's voice that makes the \
article's point and leads to it, with frontmatter shaped like the newest teaser in that folder (`status: draft`, an empty \
`article_url:` that the pipeline fills on release, word_count, sources, source_notes). Vary the sign-off against the last \
few teasers, never say "this week's article", and never "link in comments".
6. GATES, on the article and then the teaser: /fact-check in apply mode; the humanise grader on the body only until every \
hard gate passes; the portfolio habit audit (habits.py --last 12 --draft); the read-aloud pre-pass; the semantic pass (skill \
Step 5.7) on the article. Re-grade after every fix. A load-bearing claim that cannot be verified is cut or recast; if the \
article cannot stand without it, delete nothing, write the result file with outcome "stopped" and stop.
7. RECORD. Add the `Articles produced` entry (number {number}) and a short note on the run to notes.md. Leave the image to the \
staging run.
8. RESULT. Write the result file as JSON: {{"outcome": "drafted" | "cut" | "screened" | "stopped", "article": "<article \
filename, or empty>", "title": "<title, or empty>", "detail": "<one sentence>"}}.

Set no status other than `draft`, touch no other article, and do not queue, commit, push or publish anything.
Report in six lines: outcome, title, word count, fact-check result, grader score, anything left open."""


def recent_briefs() -> list[Path]:
    """Weekly briefs still fresh enough to draft from, newest first."""
    try:
        names = os.listdir(RESEARCH)
    except OSError as e:
        raise VaultUnreadable(f"cannot list {RESEARCH.name}/: {e.strerror}") from e
    today, out = dt.date.today(), []
    for name in names:
        m = re.match(r"^(\d{4}-\d{2}-\d{2}) LinkedIn post notes\.md$", name)
        if m and -1 <= (today - dt.date.fromisoformat(m.group(1))).days <= BRIEF_MAX_AGE_DAYS:
            out.append(RESEARCH / name)
    return sorted(out, reverse=True)


def brief_topics(brief: Path) -> list[tuple[int, str, str]]:
    """(number, heading, text) for each `## Topic N` section of a weekly brief."""
    out = []
    for part in re.split(r"^## ", read_vault(brief), flags=re.M)[1:]:
        m = re.match(r"Topic (\d+)\s*[—–:-]\s*(.+)", part)
        if m:
            out.append((int(m.group(1)), m.group(2).strip(), part))
    return out


def topics_with_articles() -> set[tuple[str, int]]:
    """(brief date, topic number) for every topic an article already claims in its linkedin_source."""
    out = set()
    for folder in (POSTS, ARCHIVE):
        for p in list_vault(folder):
            try:
                src = str(parse_fm(split_fm(read_vault(p))[0]).get("linkedin_source", ""))
            except ValueError:
                continue
            day, topic = re.search(r"(\d{4}-\d{2}-\d{2}) LinkedIn post notes", src), re.search(r"Topic (\d+)", src)
            if day and topic:
                out.add((day.group(1), int(topic.group(1))))
    return out


def brief_ledger() -> dict:
    """What became of brief topics, by "<brief date>#<topic>": {outcome, detail, article, date, tries}."""
    try:
        return json.loads(BRIEF_LEDGER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def note_topic(brief: Path, n: int, outcome: str, detail: str = "", article: str = "") -> None:
    book, key = brief_ledger(), f"{brief.name[:10]}#{n}"
    tries = book.get(key, {}).get("tries", 0) + (1 if outcome == "failed" else 0)
    book[key] = {"outcome": outcome, "detail": detail, "article": article, "date": dt.date.today().isoformat(), "tries": tries}
    STATE.mkdir(exist_ok=True)
    BRIEF_LEDGER.write_text(json.dumps(book, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def waiting_topics() -> list[tuple[Path, int, str, str]]:
    """Brief topics nothing has dealt with yet, freshest brief first: (brief, number, heading, text)."""
    done, book, out = topics_with_articles(), brief_ledger(), []
    for brief in recent_briefs():
        for n, heading, text in brief_topics(brief):
            rec = book.get(f"{brief.name[:10]}#{n}")
            settled = rec and (rec["outcome"] != "failed" or rec.get("tries", 0) >= MAX_ATTEMPTS)
            if (brief.name[:10], n) not in done and not settled:
                out.append((brief, n, heading, text))
    return out


def next_number() -> int:
    """The next free article number across the vault's articles and teasers and the queue."""
    used = [number_of(p) for p in queued()]
    for folder in (POSTS, ARCHIVE, TEASERS, TEASERS / "Archive"):
        try:
            used += [number_of(p) for p in list_vault(folder)]
        except VaultUnreadable:
            if folder in (POSTS, ARCHIVE):
                raise
    return max(used or [0]) + 1


def bank_skip(brief: Path, n: int, heading: str, why: str) -> None:
    """Note a topic skipped at selection in the Articles notes, where the standing rule asks for it."""
    notes, head = ARTICLES / "notes.md", "## Topics the pipeline skipped at selection"
    line = f"- {dt.date.today():%-d %b %Y}: Topic {n} of `{brief.name}` (“{heading}”): {why}."
    text = read_vault(notes)
    if head in text:
        before, after = text.split(head, 1)
        text = before + head + "\n\n" + line + "\n" + after.lstrip("\n")
    else:
        text = text.rstrip("\n") + f"\n\n{head}\n\n{line}\n"
    try:
        notes.write_text(text, encoding="utf-8")
    except OSError as e:
        raise VaultUnreadable(f"cannot write {notes.name}: {e.strerror}") from e


def draft_one(brief: Path, n: int, heading: str, number: int) -> tuple[str, str, str, str]:
    """Have a headless Claude run draft one brief topic. Returns (outcome, detail, article filename, title);
    the outcome is drafted, cut, screened, stopped or failed."""
    result = STATE / "draft-result.json"
    result.unlink(missing_ok=True)
    prompt = DRAFT_PROMPT.format(brief=str(brief), brief_name=brief.name, n=n, heading=heading, number=f"{number:03d}",
                                 posts=str(POSTS), teasers=str(TEASERS), articles=str(ARTICLES), result=str(result), screen=str(SCREEN))
    cmd = ["/usr/bin/caffeinate", "-i", str(CLAUDE_BIN), "-p", prompt,
           "--model", "claude-opus-5", "--permission-mode", "acceptEdits",
           "--allowedTools"] + ALLOWED_TOOLS
    env = dict(os.environ, PATH=f"{HOME}/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin")
    try:
        res = subprocess.run(cmd, cwd=str(HOME), env=env, timeout=DRAFT_TIMEOUT_S, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        log(f"draft TIMEOUT on Topic {n} of {brief.name}")
        return "failed", f"Claude run hit {DRAFT_TIMEOUT_S // 60} min", "", ""
    log(f"claude exit {res.returncode}; tail: {(res.stdout or '').strip()[-300:]}")
    if res.returncode != 0:
        err = (res.stderr or "").strip()[-300:]
        log(f"stderr: {err}")
        if re.search(r"log ?in|OAuth|authentication|401", err + (res.stdout or ""), re.I):
            notify("Insights pipeline ⚠️", "Claude login has expired; run `claude /login` in a terminal")
        return "failed", f"Claude exited {res.returncode}", "", ""
    try:
        out = json.loads(result.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "failed", "the run left no readable result file", "", ""
    outcome, name = str(out.get("outcome", "")), str(out.get("article", ""))
    if outcome == "drafted":
        try:
            there = bool(re.match(rf"^{number:03d}-.*\.md$", name)) and (POSTS / name).exists()
        except OSError as e:
            raise VaultUnreadable(f"cannot find {name}: {e.strerror}") from e
        if not there:
            return "failed", f"the run reported {name or 'no article'} but no such file is in Posts", "", ""
    elif outcome not in ("cut", "screened", "stopped"):
        return "failed", f"the run reported an unknown outcome {outcome!r}", "", ""
    return outcome, str(out.get("detail", ""))[:300], name if outcome == "drafted" else "", str(out.get("title", ""))


def draft(dry: bool) -> int:
    """Keep the queue fed: while fewer than DRAFT_STOCK articles are in hand, draft the next waiting brief topic."""
    if NO_DRAFT.exists():
        log("NO-DRAFT file present; not drafting")
        return 0
    stock = len(queued()) + len(vault_survey()[0])
    if stock >= DRAFT_STOCK:
        log(f"draft: {stock} article(s) in hand; nothing to draft")
        return 0
    for brief, n, heading, text in waiting_topics():
        flagged = screen_hits(heading + "\n" + text)
        if flagged:
            log(f"draft: Topic {n} of {brief.name} skipped by the screen ({', '.join(flagged)})")
            if not dry:
                note_topic(brief, n, "screened", "publication screen: " + ", ".join(flagged))
                bank_skip(brief, n, heading, "skipped by the publication screen (the brief section mentions " + ", ".join(flagged) + ")")
            continue
        number = next_number()
        log(f"draft: {stock} in hand; Topic {n} of {brief.name} -> article {number:03d}: {heading}")
        if dry:
            print(f"  would draft article {number:03d} from Topic {n} of {brief.name}")
            return 0
        if not CLAUDE_BIN.exists():
            log("claude binary missing; cannot draft")
            return 0
        outcome, detail, name, title = draft_one(brief, n, heading, number)
        note_topic(brief, n, outcome, detail, name)
        log(f"draft outcome: {outcome}" + (f" {name}" if name else "") + (f" ({detail})" if detail else ""))
        if outcome == "drafted":
            notify(f"Insights: {number:03d} drafted", f"{title or name} · the next run prepares it · click to open", open_url=obsidian_url(POSTS / name))
        elif outcome == "failed":
            notify("Insights pipeline ⚠️", f"Drafting Topic {n} of {brief.name[:10]} failed: {detail}"[:230])
        else:
            notify(f"Insights: brief topic {outcome}", f"Topic {n} of {brief.name[:10]}: {detail}"[:230])
        return 1 if outcome == "drafted" else 0
    log("draft: no brief topic is waiting")
    return 0


# ----------------------------------------------------------------------------- main

def guarded(name: str, step) -> str:
    """Run one step. A crash is logged and notified, and does not stop the steps after it."""
    try:
        step()
        return "ok"
    except VaultUnreadable as e:
        vault_alert(e)
        return "no vault"
    except Exception as e:
        traceback.print_exc()
        log(f"{name} CRASHED: {type(e).__name__}: {e}")
        notify("Insights pipeline ⚠️", f"{name} crashed ({type(e).__name__}: {str(e)[:150]}); see /tmp/insights-publish.err")
        return "crashed"


def status() -> None:
    try:
        todo, clashes = vault_survey()
        rows = [(p, parse_fm(split_fm(read_vault(p))[0])) for p in todo]
    except VaultUnreadable as e:
        print(f"VAULT UNREADABLE: {e}")
        rows, clashes = [], []
    print("Vault candidates (next to stage first):")
    for p, d in rows:
        print(f"  {p.name:50s} status={d.get('status'):8s} image={str(d.get('image'))[:30]}")
    for p, live in clashes:
        print(f"Not queued, same title as {live.name}: {p.name}")
    for name, rec in ledger().items():
        if not rec.get("recorded"):
            print(f"Live, vault record still to write: {name} -> {rec['url']}")
    print("Queued (next to release first):")
    for p in queued():
        print(f"  {p.name}")
    try:
        waiting = waiting_topics()
    except VaultUnreadable:
        waiting = []
    print(f"Brief topics waiting (one is drafted per run while fewer than {DRAFT_STOCK} articles are in hand):")
    for brief, n, heading, text in waiting:
        skip = "   [screened: will be skipped]" if screen_hits(heading + "\n" + text) else ""
        print(f"  {brief.name[:10]} Topic {n}: {heading[:70]}{skip}")
    print(f"Last release: {RELEASE_STAMP.read_text().strip() if RELEASE_STAMP.exists() else '-'}   Paused: {PAUSE.exists()}   Drafting off: {NO_DRAFT.exists()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["run", "stage", "release", "draft", "status"])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="release even if one went out today or it is a weekend")
    ap.add_argument("--all", action="store_true", help="stage every candidate, not just the per-run limit")
    a = ap.parse_args()
    if a.command == "status":
        status()
        return 0
    lock = LOCK.open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("another run is in progress; exiting")
        return 0
    outcomes = [guarded("vault", claim_vault)]      # before the first git call: see claim_vault()
    vault_up = outcomes[0] == "ok"
    git("pull", "-q", "--rebase")
    if vault_up:
        outcomes.append(guarded("vault records", lambda: reconcile(a.dry_run)))
    if a.command in ("run", "stage") and vault_up:
        outcomes.append(guarded("stage", lambda: stage(a.dry_run, a.all)))
    if a.command in ("run", "release"):
        outcomes.append(guarded("release", lambda: release(a.dry_run, a.force)))
    if a.command in ("run", "draft") and vault_up:      # last: it is the long step, and nothing waits on it
        outcomes.append(guarded("draft", lambda: draft(a.dry_run)))
    return 1 if "crashed" in outcomes else 0


if __name__ == "__main__":
    sys.exit(main())
