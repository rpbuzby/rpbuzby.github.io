# russellbuzby.com

Static site built with [Astro](https://astro.build), content in markdown, deployed to GitHub Pages by the workflow in `.github/workflows/deploy.yml` on every push to `main`.

## Where things live

| What | Where |
| --- | --- |
| Articles (Insights) | `src/content/insights/YYYY-MM-DD-slug.md` + `src/assets/insights/slug.jpg` |
| Poems (published or placed only) | `src/content/poems/NN-slug.md` |
| Poetry news | `src/content/news/YYYY-MM-title.md` |
| Fixed pages (home, about, poetry, contact) | `src/content/pages/*.md` (the words); `src/pages/*.astro` (the layout) |
| Design tokens and all CSS | `src/styles/global.css` |
| Article URL scheme | `/YYYY/MM/DD/slug/` (same as WordPress; the filename date and slug set it) |

## Publish an article from the vault

```
python3 scripts/publish_article.py "<vault>/Automation/Projects/Articles/Posts/084-slug.md" --push
```

Reads the vault frontmatter (`title`, `date`, `image`, `image_credit`, `references`, `tags`), copies the image from the Articles `Images/` folder, infers the theme from the tags (or pass `--theme`), writes the live URL back into the vault file, commits and pushes. Use `--dry-run` first.

Article frontmatter on the site:

```yaml
title: "…"
date: 2026-09-14
summary: "One or two sentences for the listing and social card."
themes:
  - "Emergency Management & Resilience"   # one or more of the five themes in src/content.config.ts
image: ../../assets/insights/slug.jpg
imageCredit: "Photo: … (optional)"
draft: false                               # true keeps it out of the build
```

## Add a poem or a news item

Copy an existing file in `src/content/poems/` or `src/content/news/`, edit, commit, push. The first link on a poem renders as the primary (ember) button, the rest as outlined buttons.

## Editing in Obsidian

Open the content folder as its own vault: Obsidian → **Open folder as vault** → `~/Projects/russellbuzby.com/src/content`. The explorer then shows only `insights`, `news`, `pages` and `poems`. Frontmatter appears as Properties at the top of each note.

- **Edit a fixed page:** `pages/home.md`, `about.md`, `poetry.md` or `contact.md`. Headline, buttons, captions and bios are Properties; the prose is the body. Photos are named by filename from `src/assets/site/`.
- **Edit an article:** open it under `src/content/insights/`, change the text or the `summary` property.
- **Add a poem or a news item:** duplicate a file in `poems/` or `news/`, edit the properties and the body.
- **Add an article from the vault pipeline:** use `scripts/publish_article.py` (below); it handles the image and the URL write-back.
- **Publish:** run `scripts/publish.sh` from a terminal (or set up the Obsidian Git community plugin with “Commit-and-sync” so it happens from the command palette). The site rebuilds in about a minute.

Rules of the house: Australian spelling, curly quotes, no em dashes, and a poem goes in `poems/` only once it is published or placed, and only as a link to the venue.

## Local preview

```
npm install
npm run dev        # http://localhost:4321
npm run build      # writes dist/
```

## Domain

The domain is registered at WordPress.com. It points at GitHub Pages through the DNS records listed in `docs/cutover.md`.
