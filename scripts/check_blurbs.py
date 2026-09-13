#!/usr/bin/env python3
"""Check every insight's `summary` for length, typography and the house word bans. Exit 1 on any failure."""
import glob, os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANNED = r"\b(delve|tapestry|leverag(e|es|ed|ing)|utilis(e|es|ed|ing)|utiliz\w*|load-bearing|playbook|navigat(e|es|ed|ing)|unpack\w*|underscor\w*|highlight\w*|crucial|robust|in today’s|this article|this piece|explores|examines|argues that)\b"
US = r"\b(defense|organization\w*|\w+ize[sd]?|\w+izing|\w+ization|behavior\w*|judgment|labor\b|center\w*|percent)\b"
KEEP_IZE = {'size', 'sizes', 'sized', 'prize', 'prizes', 'seize', 'seized', 'citizen', 'citizens'}
NOTBUT = r"\bnot\b[^.]{0,60}\bbut\b|\bisn’t\b[^.]{0,40}\bit’s\b|\bis not\b[^.]{0,40}\bit is\b"
fails = 0
for f in sorted(glob.glob(os.path.join(REPO, 'src/content/insights/*.md'))):
    s = open(f, encoding='utf-8').read()
    m = re.search(r'^summary: "(.*)"$', s, re.M)
    name = os.path.basename(f)
    if not m:
        print(f'FAIL {name}: no summary'); fails += 1; continue
    t = m.group(1)
    n = len(t.split())
    probs = []
    if not 18 <= n <= 50: probs.append(f'{n} words')
    if "'" in t or '\\"' in t: probs.append('straight quote')
    if '—' in t or '–' in t: probs.append('dash')
    if '?' in t: probs.append('question')
    b = re.findall(BANNED, t, re.I)
    if b: probs.append('banned: ' + ', '.join(x[0] if isinstance(x, tuple) else x for x in b))
    us = [w for w in re.findall(US, t, re.I) if (w if isinstance(w, str) else w[0]).lower() not in KEEP_IZE]
    us = [w if isinstance(w, str) else w[0] for w in us]
    if us: probs.append('US spelling: ' + ', '.join(us))
    if re.search(NOTBUT, t, re.I): probs.append('not/but')
    if probs:
        print(f'FAIL {name}: ' + '; '.join(probs)); fails += 1
print(f'{fails} problem(s)')
sys.exit(1 if fails else 0)
