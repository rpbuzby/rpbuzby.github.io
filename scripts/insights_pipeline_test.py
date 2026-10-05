#!/usr/bin/env python3
"""Regression test for insights_pipeline.py: the faults behind the 22 Sep to 4 Oct 2026 silence.

Runs against a throwaway vault and repo in a temp folder and touches nothing real; git, the
network, notifications and the Claude prep are all stubbed. Exit 0 means every check passed.

    python3 scripts/insights_pipeline_test.py
"""
from __future__ import annotations

import contextlib
import datetime as dt
import io
import os
import shutil
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import insights_pipeline as ip

FAILS: list[str] = []
NOTES: list[tuple[str, str]] = []
LOGGED: list[str] = []
ROOTS: list[Path] = []
TODAY = dt.date.today().isoformat()

ip.notify = lambda title, message, open_url="": NOTES.append((title, message))
ip.log = LOGGED.append
ip.git = lambda *args: types.SimpleNamespace(returncode=0, stdout="", stderr="")
ip.online = lambda: True
REAL_STAGE_ONE = ip.stage_one
ip.stage_one = lambda article, dry: False       # never start a real Claude run from a test
ip.CLAUDE_BIN = Path("/nonexistent/claude")


def check(name: str, ok: bool) -> None:
    print(("PASS  " if ok else "FAIL  ") + name)
    if not ok:
        FAILS.append(name)


def sandbox() -> Path:
    """Point every path the pipeline uses at a fresh temp tree."""
    root = Path(tempfile.mkdtemp(prefix="insights-pipeline-test-"))
    ROOTS.append(root)
    vault, repo = root / "Vault", root / "repo"
    ip.VAULT, ip.REPO = vault, repo
    ip.POSTS = vault / "Automation/Projects/Articles/Posts"
    ip.ARCHIVE = ip.POSTS / "Archive"
    ip.IMAGES = vault / "Automation/Projects/Articles/Images"
    ip.TEASERS = vault / "Automation/Projects/LinkedIn posts/Posts"
    ip.QUEUE = repo / "src/content/queue"
    ip.INSIGHTS = repo / "src/content/insights"
    ip.ASSETS = repo / "src/assets/insights"
    ip.STATE = repo / ".pipeline"
    ip.LOG = ip.STATE / "pipeline.log"
    ip.RELEASE_STAMP = ip.STATE / "last_release"
    ip.PAUSE = ip.STATE / "PAUSE"
    ip.LEDGER = ip.STATE / "published.json"
    ip.BRIEF_LEDGER = ip.STATE / "briefs.json"
    ip.NO_DRAFT = ip.STATE / "NO-DRAFT"
    ip.NO_BRIEF = ip.STATE / "NO-BRIEF"
    ip.ARTICLES = vault / "Automation/Projects/Articles"
    ip.RESEARCH = vault / "Research"
    ip.SCREEN = ip.ARTICLES / "publication-screen.md"
    paths = (ip.ARCHIVE, ip.IMAGES, ip.TEASERS / "Archive", ip.QUEUE, ip.INSIGHTS, ip.ASSETS, ip.STATE, ip.RESEARCH)
    assert all(root in p.parents for p in paths), "sandbox paths escaped the temp folder"
    for p in paths:
        p.mkdir(parents=True)
    ip.SCREEN.write_text("# Screen (test fixture)\n\nre: ZEPHYR\nre: (?i)blue heron (?:program|project)\n", encoding="utf-8")
    NOTES.clear()
    LOGGED.clear()
    return root


def article(name: str, title: str, folder: Path | None = None, **fm: str) -> Path:
    lines = ["---", f'title: "{title}"'] + [f"{k}: {v}" for k, v in fm.items()] + ["---", "", "Body.", ""]
    path = (folder or ip.POSTS) / name
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def teaser(name: str, folder: Path | None = None) -> Path:
    path = (folder or ip.TEASERS) / name
    path.write_text("---\nstatus: draft\narticle_url:\n---\n\nTeaser.\n", encoding="utf-8")
    return path


def insight(date: str, slug: str, title: str, draft: bool = False) -> Path:
    path = ip.INSIGHTS / f"{date}-{slug}.md"
    path.write_text(f'---\ntitle: "{title}"\ndate: {date}\n' + ("draft: true\n" if draft else "") + "---\n\nBody.\n", encoding="utf-8")
    return path


def queue_item(number: int, title: str, vault_name: str) -> Path:
    slug = ip.slug_of(title)
    (ip.QUEUE / f"{number:03d}-{slug}.jpg").write_bytes(b"jpg")
    path = ip.QUEUE / f"{number:03d}-{slug}.md"
    path.write_text(f'---\ntitle: "{title}"\nsummary: "A summary."\nthemes:\n  - "Defence"\nimage: ./{number:03d}-{slug}.jpg\n'
                    f'imageCredit: "Photo: someone."\nqueue: {number}\nvault: "{vault_name}"\n---\n\nBody.\n\n## References\n- One reference.\n',
                    encoding="utf-8")
    return path


def frontmatter(path: Path) -> dict:
    return ip.parse_fm(ip.split_fm(path.read_text(encoding="utf-8"))[0])


# 1. a vault macOS will not let the job read is reported, never read as empty
sandbox()
article("090-first-draft.md", "A First Draft", status="draft")
os.chmod(ip.POSTS, 0)
try:
    try:
        ip.vault_survey()
        raised = False
    except ip.VaultUnreadable:
        raised = True
    check("an unreadable vault raises instead of listing nothing", raised)
    staged = ip.stage(dry=False)
    check("stage logs and notifies the fault", staged == 0 and any("VAULT UNREADABLE" in m for m in LOGGED) and bool(NOTES))
    check("and does not log a candidate count", not any("candidate(s)" in m for m in LOGGED))
finally:
    os.chmod(ip.POSTS, 0o755)

# 2. what counts as a candidate
sandbox()
article("090-first-draft.md", "A First Draft", status="draft")
article("091-on-hold.md", "On Hold", status="draft", hold="true")
article("092-same-title.md", "Already On The Site", status="draft")
insight("2026-09-01", "already-on-the-site", "Already On The Site")
article("093-released.md", "Went Out Yesterday", status="ready")
insight("2026-10-05", "went-out-yesterday", "Went Out Yesterday")
ip.save_ledger({"093-released.md": {"url": f"{ip.SITE}/2026/10/05/went-out-yesterday/", "date": "2026-10-05",
                                    "slug": "went-out-yesterday", "recorded": False}})
article("094-queued.md", "Queued Already", status="ready")
queue_item(94, "Queued Already", "094-queued.md")
teaser("093-released.md")
todo, clashes = ip.vault_survey()
check("only the fresh draft is a candidate", [p.name for p in todo] == ["090-first-draft.md"])
check("an article whose title is already live is held for a person", [p.name for p, _ in clashes] == ["092-same-title.md"])

# 3. a release left in Posts is finished, not queued again
ip.reconcile(dry=False)
done = ip.ARCHIVE / "093-released.md"
fm = frontmatter(done) if done.exists() else {}
check("reconcile archives the released article with its url",
      done.exists() and not (ip.POSTS / "093-released.md").exists() and fm.get("status") == "published"
      and fm.get("url") == f"{ip.SITE}/2026/10/05/went-out-yesterday/" and fm.get("published_date") == "2026-10-05")
check("and fills the teaser link", frontmatter(ip.TEASERS / "093-released.md").get("article_url") == f"{ip.SITE}/2026/10/05/went-out-yesterday/")
check("and marks the ledger entry recorded", ip.ledger()["093-released.md"]["recorded"] is True)

# 4. the 5 Oct fault: the push succeeds, then macOS refuses the vault read
sandbox()
stuck = article("095-vault-name.md", "Some New Title", status="ready")
teaser("095-vault-name.md")
queue_item(95, "Some New Title", "095-vault-name.md")
os.chmod(stuck, 0)                               # stat still works, reading does not
try:
    released = ip.release(dry=False, force=True)
finally:
    os.chmod(stuck, 0o644)
check("the release still publishes", released and (ip.INSIGHTS / f"{TODAY}-some-new-title.md").exists())
check("the published notice goes out before the vault is touched", ("Insights published", "Some New Title") in NOTES)
check("the failed write-back is deferred, not a crash",
      any("deferred" in m for m in LOGGED) and ip.ledger().get("095-vault-name.md", {}).get("recorded") is False and stuck.exists())
todo, clashes = ip.vault_survey()
check("the live article is not offered for staging again", todo == [] and clashes == [])
ip.reconcile(dry=False)
check("the next run finishes its vault record",
      (ip.ARCHIVE / "095-vault-name.md").exists() and not stuck.exists() and ip.ledger()["095-vault-name.md"]["recorded"] is True
      and frontmatter(ip.TEASERS / "095-vault-name.md").get("article_url") == f"{ip.SITE}/{TODAY[:4]}/{TODAY[5:7]}/{TODAY[8:10]}/some-new-title/")

# 5. something already on the site is never released a second time
sandbox()
insight("2026-09-01", "already-on-the-site", "Already On The Site")
queue_item(96, "Already On The Site", "096-a.md")
queue_item(97, "A Different One", "097-b.md")
released = ip.release(dry=False, force=True)
check("a queued duplicate is passed over for the next article",
      released and (ip.INSIGHTS / f"{TODAY}-a-different-one.md").exists() and (ip.QUEUE / "096-already-on-the-site.md").exists()
      and len(list(ip.INSIGHTS.glob("*-already-on-the-site.md"))) == 1)
check("and a queue of nothing but duplicates releases nothing", ip.release(dry=False, force=True) is False)

# 6. an article filed in Archive by hand before its release still gets its record and teaser link
sandbox()
article("098-moved.md", "Moved By Hand", folder=ip.ARCHIVE, status="ready")
teaser("098-moved.md", folder=ip.TEASERS / "Archive")
ip.write_back("098-moved.md", f"{ip.SITE}/2026/10/01/moved-by-hand/", "2026-10-01")
check("an article already in Archive is updated in place",
      frontmatter(ip.ARCHIVE / "098-moved.md").get("status") == "published"
      and frontmatter(ip.TEASERS / "Archive/098-moved.md").get("article_url") == f"{ip.SITE}/2026/10/01/moved-by-hand/")

# 7. an article pulled from the site after release is neither re-recorded nor re-queued
sandbox()
article("099-pulled.md", "Pulled Later", status="ready")
insight("2026-10-02", "pulled-later", "Pulled Later", draft=True)
ip.save_ledger({"099-pulled.md": {"url": f"{ip.SITE}/2026/10/02/pulled-later/", "date": "2026-10-02", "slug": "pulled-later", "recorded": False}})
ip.reconcile(dry=False)
todo, clashes = ip.vault_survey()
check("a pulled article is left alone and stays out of the queue",
      (ip.POSTS / "099-pulled.md").exists() and "url" not in frontmatter(ip.POSTS / "099-pulled.md") and todo == [] and clashes == [])

# 8. one step crashing is reported and does not stop the run
NOTES.clear()
with contextlib.redirect_stderr(io.StringIO()):
    outcome = ip.guarded("stage", lambda: 1 / 0)
check("a crashing step is logged and notified, not fatal", outcome == "crashed" and bool(NOTES) and any("CRASHED" in m for m in LOGGED))

# 8b. the grader gate reads the prose, not the reference list (house rule: grade the body only)
check("the reference list is stripped before grading",
      ip.prose_only("First paragraph.\n\nSecond.\n\n## References\n- Someone. (2026). *A title.* https://example.org\n") == "First paragraph.\n\nSecond.\n"
      and ip.prose_only("Body.\n\n### References\n\nEntry one.\n\nEntry two.\n") == "Body.\n"
      and ip.prose_only("No list here, though the word References appears.\n") == "No list here, though the word References appears.\n")

# 9. the root cause: a run must read the vault before it runs git, or macOS takes the job for git
root = sandbox()
events: list[str] = []
real_list_vault = ip.list_vault
ip.list_vault = lambda folder, number="": (events.append("vault"), real_list_vault(folder, number))[1]
ip.git = lambda *args: (events.append("git"), types.SimpleNamespace(returncode=0, stdout="", stderr=""))[1]
ip.LOCK = root / "pipeline.lock"
sys.argv = ["insights_pipeline.py", "stage", "--dry-run"]
ip.main()
check("a run makes its first vault read before its first git call", events[:2] == ["vault", "git"])

# 10. the publication screen: read from a private note, case rule respected, and it fails closed
sandbox()
check("the screen fires on its patterns", ip.screen_hits("The ZEPHYR timetable moved.") == ["ZEPHYR"] and ip.screen_hits("a Blue Heron Program review") == ["Blue Heron Program"])
check("and on nothing in the look-alike set", not ip.screen_hits("A zephyr blew in. The blue herons left. ZEPHYRS is another word."))
ip.SCREEN.write_text("# no patterns here\n", encoding="utf-8")
try:
    ip.screen_hits("anything"); empty_ok = False
except ip.VaultUnreadable:
    empty_ok = True
ip.SCREEN.unlink()
try:
    ip.screen_hits("anything"); missing_ok = False
except ip.VaultUnreadable:
    missing_ok = True
check("an empty or missing screen is an error, never a pass", empty_ok and missing_ok)

# 11. weekly briefs: topics are read whichever dash the heading uses, and only fresh briefs count
sandbox()
day = dt.date.today()
fresh = ip.RESEARCH / f"{day.isoformat()} LinkedIn post notes.md"
stale = ip.RESEARCH / f"{(day - dt.timedelta(days=20)).isoformat()} LinkedIn post notes.md"
fresh.write_text("# LinkedIn post notes\n\nPreamble.\n\n## Topic 1 — Already written up\n\nText.\n\n## Topic 2 – The ZEPHYR workforce question\n\nText.\n\n"
                 "## Topic 3 — A clean topic\n\nText three.\n\n## Topic 4 – Another clean topic\n\nText four.\n\n## Cross-cutting thread, if you want a fifth\n\nNot a topic.\n", encoding="utf-8")
stale.write_text("## Topic 1 — Too old to draft\n\nText.\n", encoding="utf-8")
(ip.ARTICLES / "notes.md").write_text("# Standing Notes\n\n## Articles produced\n\n1. **Something**\n", encoding="utf-8")
article("070-written-up.md", "Already Written Up", folder=ip.ARCHIVE, status="published", linkedin_source=f'"Topic 1 of `{fresh.name}`"')
check("a brief's topics are read under em and en dashes, the fifth thread ignored", [n for n, _, _ in ip.brief_topics(fresh)] == [1, 2, 3, 4])
check("a topic an article already claims is not waiting, and a stale brief is ignored",
      [(b.name, n) for b, n, _, _ in ip.waiting_topics()] == [(fresh.name, 2), (fresh.name, 3), (fresh.name, 4)])

# 12. drafting: a screened topic is skipped with no Claude run and noted, then clean topics are drafted one per run
calls = []
def fake_draft_one(brief, n, heading, number):
    calls.append((n, number))
    name = f"{number:03d}-drafted-topic-{n}.md"
    article(name, f"Drafted Topic {n}", status="draft", linkedin_source=f'"Topic {n} of `{brief.name}`"')
    return "drafted", "ok", name, f"Drafted Topic {n}"
ip.draft_one = fake_draft_one
ip.CLAUDE_BIN = Path(sys.executable)
made = ip.draft(dry=False)
check("a screened topic is skipped before drafting and recorded",
      ip.brief_ledger().get(f"{day.isoformat()}#2", {}).get("outcome") == "screened" and "Topic 2" in (ip.ARTICLES / "notes.md").read_text(encoding="utf-8"))
check("the next clean topic is drafted under the next free number, one per run", made == 1 and calls == [(3, 71)])
ip.draft(dry=False)
check("the following run takes the following topic", calls == [(3, 71), (4, 72)])
ip.draft(dry=False)
check("and nothing is drafted once no topic is waiting", calls == [(3, 71), (4, 72)] and any("no brief topic is waiting" in m for m in LOGGED))
article("073-third-in-hand.md", "Third In Hand", status="draft")
(ip.RESEARCH / f"{(day - dt.timedelta(days=1)).isoformat()} LinkedIn post notes.md").write_text("## Topic 1 — Would be drafted if stock were low\n\nText.\n", encoding="utf-8")
ip.draft(dry=False)
check("with three articles in hand nothing more is drafted", calls == [(3, 71), (4, 72)])
(ip.POSTS / "073-third-in-hand.md").unlink()
(ip.STATE / "NO-DRAFT").write_text("", encoding="utf-8")
ip.draft(dry=False)
check("a NO-DRAFT file stops drafting", calls == [(3, 71), (4, 72)])
(ip.STATE / "NO-DRAFT").unlink()
ip.SCREEN.unlink()
try:
    ip.draft(dry=False); closed = False
except ip.VaultUnreadable:
    closed = True
check("without its screen the drafting step refuses to run", closed and calls == [(3, 71), (4, 72)])

# 13. the stage gate: an article the screen catches is held at once, with no second try
sandbox()
(ip.IMAGES / "074-x.jpg").write_bytes(b"jpg")
held = article("074-trips-the-screen.md", "A Piece The Screen Should Catch", status="ready", image="074-x.jpg",
               image_credit='"Photo by someone on Pexels"', image_caption='"Photo: someone, via Pexels."', theme='"Defence"',
               summary='"' + " ".join(["word"] * 30) + '"')
held.write_text(held.read_text(encoding="utf-8").replace("Body.", "The ZEPHYR timetable moved again, and the plan with it."), encoding="utf-8")
queued_it = REAL_STAGE_ONE(held, False)
fm = frontmatter(held)
check("an article the screen catches is held at once and never queued",
      queued_it is False and fm.get("hold") == "true" and "screen: ZEPHYR" in str(fm.get("stage_note")) and not list(ip.QUEUE.glob("074-*")))

# 14. the weekly-brief backstop: it waits for the desktop task, then writes the brief itself
sandbox()
def sydney(y, m, d, h):
    ip.sydney_now = lambda: dt.datetime(y, m, d, h, 0)
(ip.RESEARCH / "2026-10-04 LinkedIn post notes.md").write_text("## Topic 1: One\n\nText.\n", encoding="utf-8")
sydney(2026, 10, 9, 15);  midweek = ip.brief_due()
sydney(2026, 10, 11, 11); sunday_morning = ip.brief_due()
sydney(2026, 10, 11, 12); sunday_noon = ip.brief_due()
sydney(2026, 10, 13, 3);  later = ip.brief_due()
check("the brief backstop is due only once the newest brief is a week old and Sunday noon has passed in Sydney",
      midweek is None and sunday_morning is None and sunday_noon == dt.date(2026, 10, 11) and later == dt.date(2026, 10, 13))
runs = []
def fake_headless(prompt, timeout):
    runs.append(prompt)
    target = ip.RESEARCH / "2026-10-11 LinkedIn post notes.md"
    target.write_text("# LinkedIn post notes: week to 11 October 2026\n\n" + "".join(f"## Topic {k}: Headline {k}\n\nText.\n\n" for k in range(1, 6)), encoding="utf-8")
    return types.SimpleNamespace(returncode=0, stdout="", stderr="")
ip.headless = fake_headless
ip.CLAUDE_BIN = Path(sys.executable)
sydney(2026, 10, 11, 14)
wrote = ip.brief(dry=False)
check("when it is due the backstop writes the brief once, in a shape the drafter can parse",
      wrote == 1 and len(runs) == 1 and len(ip.brief_topics(ip.RESEARCH / "2026-10-11 LinkedIn post notes.md")) == 5 and ip.brief(dry=False) == 0 and len(runs) == 1)
check("its prompt names the screen file and asks for five or six topics", str(ip.SCREEN) in runs[0] and "five or six topics" in runs[0])
(ip.RESEARCH / "2026-10-11 LinkedIn post notes.md").unlink()
ip.headless = lambda prompt, timeout: (runs.append(prompt), None)[1]
ip.brief(dry=False); ip.brief(dry=False); ip.brief(dry=False)
check("a failing backstop tries twice for a given week and then stops", len(runs) == 3 and ip.brief_ledger()["2026-10-11#brief"]["tries"] == 2)
(ip.STATE / "briefs.json").unlink()
(ip.STATE / "NO-BRIEF").write_text("", encoding="utf-8")
ip.brief(dry=False)
check("a NO-BRIEF file stops the backstop", len(runs) == 3)

for root in ROOTS:
    shutil.rmtree(root, ignore_errors=True)
print(f"\n{'FAIL' if FAILS else 'PASS'}: {len(FAILS)} failed" + (": " + "; ".join(FAILS) if FAILS else ""))
sys.exit(1 if FAILS else 0)
