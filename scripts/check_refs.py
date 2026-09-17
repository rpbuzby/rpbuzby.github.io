#!/usr/bin/env python3
"""Check every insight and queued article renders its references in the house style.

The site shows the small numbered reference block (src/lib/refs.ts, .refs in
global.css) only when the '## References' entries are markdown list items. A
draft that writes them as blank-line-separated paragraphs still renders, but as
full-size body text with no numbers. Exit 1 on any failure.

  python3 scripts/check_refs.py           # report
  python3 scripts/check_refs.py --fix     # rewrite paragraph entries as list items
"""
import glob, os, re, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIX = '--fix' in sys.argv


def section(body):
    """Return (entries, is_list) for the References section, or (None, None)."""
    m = re.search(r'^## References\s*$', body, re.M)
    if not m:
        return None, None
    tail = body[m.end():]
    nxt = re.search(r'^## ', tail, re.M)
    if nxt:
        tail = tail[:nxt.start()]
    lines = [l for l in tail.split('\n')]
    items = [l.strip()[2:] for l in lines if l.lstrip().startswith('- ')]
    if items:
        return items, True
    entries, buf = [], []
    for l in lines:
        if l.strip():
            buf.append(l.strip())
        elif buf:
            entries.append(' '.join(buf)); buf = []
    if buf:
        entries.append(' '.join(buf))
    return entries, False


def fix(body):
    m = re.search(r'^## References\s*$', body, re.M)
    entries, is_list = section(body)
    if not entries or is_list:
        return body
    head, tail = body[:m.end()], body[m.end():]
    after = ''
    nxt = re.search(r'^## ', tail, re.M)
    if nxt:
        after = tail[nxt.start():]
    return head + '\n' + '\n'.join('- ' + e for e in entries) + '\n' + ('\n' + after if after else '')


fails = 0
targets = sorted(glob.glob(os.path.join(REPO, 'src/content/insights/*.md'))) + \
          sorted(glob.glob(os.path.join(REPO, 'src/content/queue/*.md')))
for f in targets:
    name = os.path.basename(f)
    if name == 'README.md':
        continue
    body = open(f, encoding='utf-8').read()
    entries, is_list = section(body)
    if entries is None:
        continue          # an article may legitimately carry no references
    if not entries:
        print(f'FAIL {name}: References heading with no entries'); fails += 1
        continue
    if not is_list:
        if FIX:
            open(f, 'w', encoding='utf-8').write(fix(body))
            print(f'FIXED {name}: {len(entries)} reference(s) rewritten as list items')
        else:
            print(f'FAIL {name}: {len(entries)} reference(s) as paragraphs, not list items'); fails += 1

print(f'{fails} problem(s) across {len(targets)} file(s)')
sys.exit(1 if fails and not FIX else 0)
