#!/usr/bin/env python3
"""Publish a vault article to russellbuzby.com.

Copies one markdown article from the Obsidian Articles pipeline into the Astro
content collection, carries its image across, maps its tags to a site theme,
writes the live URL back into the vault file, and (optionally) commits and
pushes so GitHub Pages rebuilds.

    python3 scripts/publish_article.py "<path to vault article>.md" [--theme "AI in Government"] [--date 2026-09-14] [--push] [--dry-run]

Stdlib only. Vault frontmatter it reads: title, date, image, image_credit,
references (list), tags (list), summary (optional). The site frontmatter it
writes: title, date, summary, themes, image, imageCredit, draft.

The article body is taken as-is (after the frontmatter). A trailing
"## References" section is added from the `references` list when the body does
not already carry one.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import subprocess
import sys
import unicodedata

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(REPO, 'src', 'content', 'insights')
ASSETS = os.path.join(REPO, 'src', 'assets', 'insights')
VAULT = os.path.expanduser('~/Library/Mobile Documents/iCloud~md~obsidian/Documents/Vault')
IMAGES_DIRS = [
    os.path.join(VAULT, 'Automation', 'Projects', 'Articles', 'Images'),
    os.path.join(VAULT, 'Automation', 'Projects', 'Articles', 'Images', 'Archive'),
]
THEMES = ['Emergency Management & Resilience', 'AI in Government', 'Defence', 'Change & Transformation', 'Leadership']
# First matching tag (case-insensitive substring) decides the theme unless --theme is given.
TAG_TO_THEME = [
    ('emergency', 'Emergency Management & Resilience'),
    ('bushfire', 'Emergency Management & Resilience'),
    ('wildfire', 'Emergency Management & Resilience'),
    ('resilience', 'Emergency Management & Resilience'),
    ('disaster', 'Emergency Management & Resilience'),
    ('fire', 'Emergency Management & Resilience'),
    ('ai', 'AI in Government'),
    ('artificial intelligence', 'AI in Government'),
    ('defence', 'Defence'),
    ('aukus', 'Defence'),
    ('change', 'Change & Transformation'),
    ('transformation', 'Change & Transformation'),
    ('reform', 'Change & Transformation'),
    ('leadership', 'Leadership'),
]


def die(msg: str) -> None:
    print(f'error: {msg}', file=sys.stderr)
    sys.exit(1)


def split_frontmatter(text: str) -> tuple[str, str]:
    m = re.match(r'^---\r?\n(.*?)\r?\n---\r?\n?(.*)$', text, re.S)
    if not m:
        die('no YAML frontmatter found')
    return m.group(1), m.group(2)


def parse_frontmatter(fm: str) -> dict:
    """Minimal YAML reader for the flat keys and simple lists this pipeline writes."""
    data: dict = {}
    key = None
    for line in fm.splitlines():
        if not line.strip():
            continue
        m = re.match(r'^([A-Za-z_][\w-]*):\s*(.*)$', line)
        if m and not line.startswith((' ', '\t')):
            key, val = m.group(1), m.group(2).strip()
            if val == '':
                data[key] = []
            else:
                data[key] = unquote(val)
        elif key is not None and re.match(r'^\s*-\s+', line):
            data.setdefault(key, [])
            if not isinstance(data[key], list):
                data[key] = [data[key]]
            data[key].append(unquote(re.sub(r'^\s*-\s+', '', line).strip()))
    return data


def unquote(v: str) -> str:
    if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'':
        inner = v[1:-1]
        return inner.replace('\\"', '"') if v[0] == '"' else inner
    return v


def yq(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def curly(s: str) -> str:
    s = re.sub(r'(^|[\s(\[])"', '\\1\u201c', s)
    s = s.replace('"', '\u201d')
    s = re.sub(r"(^|[\s(\[])'", '\\1\u2018', s)
    s = s.replace("'", '\u2019')
    return s


def normalise(s: str) -> str:
    for bad, good in (('\u2011', '-'), ('\u00a0', ' '), ('\u200b', ''), ('\u00ad', ''), ('\u2014', ':')):
        s = s.replace(bad, good)
    return s


def slugify(title: str) -> str:
    s = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return s[:80].rstrip('-')


def find_image(name: str) -> str | None:
    if not name or name.upper() == 'TBD':
        return None
    if os.path.isabs(name) and os.path.exists(name):
        return name
    for d in IMAGES_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


def first_paragraph(body: str) -> str:
    for para in re.split(r'\n\s*\n', body.strip()):
        t = re.sub(r'[*_`>#\[\]]', '', para).strip()
        if len(t) > 80 and not t.startswith('!'):
            return t
    return ''


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('article', help='vault markdown file')
    ap.add_argument('--theme', action='append', choices=THEMES, help='site theme (repeatable); default from tags')
    ap.add_argument('--date', help='publish date YYYY-MM-DD (default: today)')
    ap.add_argument('--slug', help='override URL slug (default from title)')
    ap.add_argument('--summary', help='override the listing summary (default: vault summary or first paragraph)')
    ap.add_argument('--push', action='store_true', help='git commit and push after writing')
    ap.add_argument('--dry-run', action='store_true', help='show what would be written, write nothing')
    a = ap.parse_args()

    src = os.path.abspath(a.article)
    if not os.path.exists(src):
        die(f'not found: {src}')
    raw = open(src, encoding='utf-8').read()
    fm_text, body = split_frontmatter(raw)
    fm = parse_frontmatter(fm_text)

    title = normalise(curly(fm.get('title', '')))
    if not title:
        die('vault article has no title')
    date = a.date or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        die('date must be YYYY-MM-DD')
    slug = a.slug or slugify(title)

    themes = a.theme or []
    if not themes:
        tags = [t.lower() for t in (fm.get('tags') or [])]
        for needle, theme in TAG_TO_THEME:
            if any(re.search(rf'\b{re.escape(needle)}\b', t) for t in tags) and theme not in themes:
                themes.append(theme)
                break
    if not themes:
        die('could not infer a theme from tags; pass --theme')

    summary = a.summary or fm.get('summary') or first_paragraph(body)
    summary = normalise(curly(summary))
    if len(summary) > 400:
        summary = summary[:400].rsplit(' ', 1)[0] + '…'

    img_src = find_image(str(fm.get('image', '')))
    if not img_src:
        die(f"image not found for '{fm.get('image')}'; source it first (image rule) or pass a path in the vault frontmatter")
    ext = os.path.splitext(img_src)[1].lower() or '.jpg'
    img_name = f'{slug}{ext}'
    credit = normalise(curly(str(fm.get('image_credit', '')))) if fm.get('image_credit') else ''
    if credit.upper().startswith('NOT YET') or credit.upper().startswith('TBD'):
        die('image_credit says the image is not sourced yet')

    body = normalise(body).strip()
    refs = fm.get('references') or []
    if refs and not re.search(r'^## References\s*$', body, re.M):
        body += '\n\n## References\n' + '\n'.join('- ' + normalise(r) for r in refs) + '\n'

    out_md = os.path.join(CONTENT, f'{date}-{slug}.md')
    out_img = os.path.join(ASSETS, img_name)
    url = f'https://russellbuzby.com/{date[:4]}/{date[5:7]}/{date[8:10]}/{slug}/'

    front = ['---', f'title: {yq(title)}', f'date: {date}', f'summary: {yq(summary)}', 'themes:'] + [f'  - {yq(t)}' for t in themes]
    front += [f'image: ../../assets/insights/{img_name}']
    if credit:
        front += [f'imageCredit: {yq(credit)}']
    front += ['---', '']
    content = '\n'.join(front) + body + '\n'

    print(f'title:   {title}\ndate:    {date}\nthemes:  {", ".join(themes)}\nurl:     {url}\nimage:   {img_src}\nwrites:  {os.path.relpath(out_md, REPO)}\n         {os.path.relpath(out_img, REPO)}')
    if a.dry_run:
        print('\n--- frontmatter ---\n' + '\n'.join(front))
        return
    if os.path.exists(out_md):
        die(f'{out_md} already exists; remove it or pass --slug')

    os.makedirs(CONTENT, exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)
    shutil.copy2(img_src, out_img)
    open(out_md, 'w', encoding='utf-8').write(content)

    # Write the live URL and published status back into the vault file so cross-links can use it.
    new_fm = fm_text
    if re.search(r'^url:', new_fm, re.M):
        new_fm = re.sub(r'^url:.*$', f'url: {url}', new_fm, flags=re.M)
    else:
        new_fm += f'\nurl: {url}'
    new_fm = re.sub(r'^status:.*$', 'status: published', new_fm, flags=re.M)
    open(src, 'w', encoding='utf-8').write(f'---\n{new_fm}\n---\n{raw.split("---", 2)[2].lstrip(chr(10))}')
    print('vault:   url and status written back')

    if a.push:
        subprocess.run(['git', '-C', REPO, 'add', out_md, out_img], check=True)
        subprocess.run(['git', '-C', REPO, 'commit', '-m', f'Publish: {title}'], check=True)
        subprocess.run(['git', '-C', REPO, 'push'], check=True)
        print('pushed; GitHub Pages will rebuild in about a minute')
    else:
        print('not pushed; run with --push, or commit and push yourself')


if __name__ == '__main__':
    main()
