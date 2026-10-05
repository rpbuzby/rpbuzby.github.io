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
    paths = (ip.ARCHIVE, ip.IMAGES, ip.TEASERS / "Archive", ip.QUEUE, ip.INSIGHTS, ip.ASSETS, ip.STATE)
    assert all(root in p.parents for p in paths), "sandbox paths escaped the temp folder"
    for p in paths:
        p.mkdir(parents=True)
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

for root in ROOTS:
    shutil.rmtree(root, ignore_errors=True)
print(f"\n{'FAIL' if FAILS else 'PASS'}: {len(FAILS)} failed" + (": " + "; ".join(FAILS) if FAILS else ""))
sys.exit(1 if FAILS else 0)
