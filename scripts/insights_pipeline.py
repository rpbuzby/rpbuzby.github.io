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
  run      stage (bounded) then release.  status  prints the queue.

Releases happen on weekdays only. Controls: `hold: true` in a vault article's frontmatter keeps it out of the pipeline;
a file named PAUSE in .pipeline/ stops releases; --dry-run shows what would happen.
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
CLAUDE_BIN = HOME / ".local/bin/claude"
GRADER = HOME / ".agents/skills/humanise/grade.py"
READALOUD = HOME / ".agents/skills/read-aloud/read_aloud.py"
CHECK_BLURBS = REPO / "scripts/check_blurbs.py"
SITE = "https://russellbuzby.com"
STAGE_TIMEOUT_S = 2700   # 45 min per article
MAX_STAGE_PER_RUN = 2    # scheduled runs; `stage --all` lifts it
MAX_QUEUE = 10           # do not stage more than this many ahead
THEMES = ["Emergency Management & Resilience", "AI in Government", "Defence", "Change & Transformation"]
TAG_TO_THEME = [
    ("emergency", THEMES[0]), ("bushfire", THEMES[0]), ("wildfire", THEMES[0]), ("resilience", THEMES[0]),
    ("disaster", THEMES[0]), ("fire", THEMES[0]), ("ai", THEMES[1]), ("artificial intelligence", THEMES[1]),
    ("automation", THEMES[1]), ("defence", THEMES[2]), ("aukus", THEMES[2]), ("military", THEMES[2]),
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


# ----------------------------------------------------------------------------- queue views

def vault_candidates() -> list[Path]:
    """Numbered vault articles not yet queued or published, not on hold, lowest number first."""
    out = []
    queued = {number_of(p) for p in QUEUE.glob("*.md")} if QUEUE.exists() else set()
    for p in sorted(POSTS.glob("[0-9][0-9][0-9]-*.md"), key=number_of):
        d = parse_fm(split_fm(p.read_text(encoding="utf-8"))[0])
        if str(d.get("hold", "")).lower() == "true":
            continue
        if d.get("status") == "published" or d.get("url"):
            continue
        if number_of(p) in queued:
            continue
        out.append(p)
    return out


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
no em dashes, Australian English).

{stage_note}Do these in order and stop if a step cannot be completed honestly:

1. IMAGE. If the frontmatter `image` is TBD, or names a file that does not exist in the images folder, source \
one under the standing image rule: NSW RFS Flickr (pre-2019 archive) is the required primary source for fire, \
bushfire or emergency topics; Pexels free-use for everything else, and as the documented fallback. Download it \
to the images folder as `{number}-<short-slug>.jpg` at 1600px on the long side (use sips to resize if needed), \
and write `image:` (the filename) and `image_credit:` (photographer or agency, the asset URL, the licence) in \
the frontmatter. Never invent an asset ID or a credit; if no usable image can be verified, write \
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
    d = parse_fm(split_fm(article.read_text(encoding="utf-8"))[0])
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
            article=str(article), images=str(IMAGES), number=f"{n:03d}",
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
            notify("Insights pipeline ⚠️", f"Prep of {article.name} timed out; will retry next run")
            return False
        log(f"claude exit {res.returncode}; tail: {(res.stdout or '').strip()[-300:]}")
        if res.returncode != 0:
            err = (res.stderr or "").strip()[-300:]
            log(f"stderr: {err}")
            if re.search(r"log ?in|OAuth|authentication|401", err + (res.stdout or ""), re.I):
                notify("Insights pipeline ⚠️", "Claude login has expired; run `claude /login` in a terminal")
            return False
        d = parse_fm(split_fm(article.read_text(encoding="utf-8"))[0])

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
    summary = str(d.get("summary", "")).strip()
    if not (18 <= len(summary.split()) <= 50):
        problems.append(f"summary is {len(summary.split())} words")
    if "'" in summary or '"' in summary or "\u2014" in summary or "?" in summary:
        problems.append("summary typography (straight quote, dash or question)")
    if d.get("theme") not in THEMES:
        problems.append(f"theme not set: {d.get('theme')}")
    # grader on the body
    body = split_fm(article.read_text(encoding="utf-8"))[1]
    tmp = STATE / f"grade-{n:03d}.md"
    STATE.mkdir(exist_ok=True)
    tmp.write_text(body, encoding="utf-8")
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
        log("stage gates FAILED: " + " | ".join(problems))
        text = article.read_text(encoding="utf-8")
        text = set_fm_field(text, "stage_note", yq("GATES FAILED " + dt.date.today().isoformat() + ": " + " | ".join(problems)))
        if d.get("status") == "ready":
            text = set_fm_field(text, "status", "draft")
        article.write_text(text, encoding="utf-8")
        notify("Insights pipeline ⚠️", f"{article.name} did not pass the gates; see stage_note in the vault file")
        return False

    # ---- copy into the queue (and clear any old stage_note in the vault file)
    if d.get("stage_note"):
        vt = article.read_text(encoding="utf-8")
        vt = re.sub(r"^stage_note:.*\n?", "", vt, count=1, flags=re.M)
        article.write_text(vt, encoding="utf-8")
    QUEUE.mkdir(parents=True, exist_ok=True)
    title = normalise(curly(str(d["title"])))
    slug = slugify(title)
    ext = img.suffix.lower() or ".jpg"
    qmd = QUEUE / f"{n:03d}-{slug}.md"
    qimg = QUEUE / f"{n:03d}-{slug}{ext}"
    shutil.copy2(img, qimg)
    refs = d.get("references") or []
    body = normalise(body).strip()
    if refs and not re.search(r"^## References\s*$", body, re.M):
        body += "\n\n## References\n" + "\n".join("- " + normalise(r) for r in refs) + "\n"
    front = ["---", f"title: {yq(title)}", f"summary: {yq(normalise(curly(summary)))}", "themes:", f"  - {yq(d['theme'])}",
             f"image: ./{qimg.name}", f"imageCredit: {yq(normalise(curly(credit)))}", f"queue: {n}", f"vault: {yq(article.name)}", "---", ""]
    qmd.write_text("\n".join(front) + body + "\n", encoding="utf-8")
    git("add", str(qmd), str(qimg))
    git("commit", "-q", "-m", f"Queue: {title}")
    log(f"queued {qmd.name}")
    notify("Insights pipeline", f"Queued for release: {title}")
    return True


def stage(dry: bool, all_: bool = False) -> int:
    cands = vault_candidates()
    q = queued()
    log(f"stage: {len(cands)} candidate(s) in vault, {len(q)} queued")
    room = MAX_QUEUE - len(q)
    if room <= 0:
        log("queue full; not staging")
        return 0
    limit = len(cands) if all_ else MAX_STAGE_PER_RUN
    done = 0
    for a in cands[:min(limit, room)]:
        if stage_one(a, dry):
            done += 1
    return done


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
    qmd = q[0]
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
    if out_md.exists():
        log(f"{out_md.name} already exists; aborting")
        notify("Insights pipeline ⚠️", f"{out_md.name} already exists; release skipped")
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

    # write back to the vault: url, status, archive; and the teaser
    vault_file = POSTS / str(d.get("vault", ""))
    if vault_file.exists():
        vt = vault_file.read_text(encoding="utf-8")
        vt = set_fm_field(vt, "url", url)
        vt = set_fm_field(vt, "status", "published")
        vt = set_fm_field(vt, "published_date", iso)
        ARCHIVE.mkdir(exist_ok=True)
        (ARCHIVE / vault_file.name).write_text(vt, encoding="utf-8")
        vault_file.unlink()
        log(f"vault: {vault_file.name} -> Archive/ with url")
    for t in TEASERS.glob(f"{qmd.stem[:3]}-*.md"):
        tt = t.read_text(encoding="utf-8")
        if re.search(r"^article_url:", tt, re.M):
            tt = set_fm_field(tt, "article_url", url)
        else:
            tt = set_fm_field(tt, "article_url", url)
        t.write_text(tt, encoding="utf-8")
        log(f"teaser {t.name}: article_url set")
    notify("Insights published", str(d["title"]), open_url=url)
    return True


# ----------------------------------------------------------------------------- main

def status() -> None:
    print("Vault candidates (next to stage first):")
    for p in vault_candidates():
        d = parse_fm(split_fm(p.read_text(encoding="utf-8"))[0])
        print(f"  {p.name:50s} status={d.get('status'):8s} image={str(d.get('image'))[:30]}")
    print("Queued (next to release first):")
    for p in queued():
        print(f"  {p.name}")
    print(f"Last release: {RELEASE_STAMP.read_text().strip() if RELEASE_STAMP.exists() else '-'}   Paused: {PAUSE.exists()}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["run", "stage", "release", "status"])
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
    git("pull", "-q", "--rebase")
    if a.command in ("run", "stage"):
        stage(a.dry_run, a.all)
    if a.command in ("run", "release"):
        release(a.dry_run, a.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
