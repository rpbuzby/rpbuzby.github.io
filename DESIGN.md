---
name: russellbuzby.com
description: One person, two registers: Commonwealth reform consulting and poetry from Braidwood, on a smoke ground with a single ember accent.
colors:
  ground: "#ECEBE6"
  ash: "#E1DFD8"
  line: "#CFCCC3"
  ink: "#1B1D20"
  stone: "#5F5E57"
  ember: "#A3361C"
  ember-ink: "#FFF6F1"
  dark-ground: "#141517"
  dark-ash: "#1E2024"
  dark-line: "#33363B"
  dark-ink: "#E9E7E1"
  dark-stone: "#A19F96"
  dark-ember: "#E07A58"
  dark-ember-ink: "#1B1D20"
typography:
  page-title:
    fontFamily: "Cormorant Garamond, Cormorant, Garamond, Times New Roman, serif"
    fontSize: "clamp(2.4rem, 4.8vw, 3.6rem)"
    fontWeight: 500
    lineHeight: 1.08
    letterSpacing: "-0.01em"
  door:
    fontFamily: "Cormorant Garamond, serif"
    fontSize: "clamp(1.9rem, 3vw, 2.25rem)"
    fontWeight: 500
    lineHeight: 1.1
  section:
    fontFamily: "Cormorant Garamond, serif"
    fontSize: "clamp(1.5rem, 2.4vw, 1.75rem)"
    fontWeight: 600
    lineHeight: 1.15
  poem-title:
    fontFamily: "Cormorant Garamond, serif"
    fontSize: "clamp(1.4rem, 2vw, 1.6rem)"
    fontWeight: 600
    fontStyle: italic
    lineHeight: 1.2
  item:
    fontFamily: "Cormorant Garamond, serif"
    fontSize: "1.35rem"
    fontWeight: 600
    lineHeight: 1.25
  lede:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(1.05rem, 1.4vw, 1.15rem)"
    fontWeight: 400
    lineHeight: 1.55
  body:
    fontFamily: "IBM Plex Sans, Helvetica Neue, Arial, sans-serif"
    fontSize: "1.0625rem"
    fontWeight: 400
    lineHeight: 1.6
  article-body:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "IBM Plex Sans, sans-serif"
    fontSize: "0.78rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.1em"
    textTransform: uppercase
  log:
    fontFamily: "IBM Plex Mono, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: "0.78rem"
    fontWeight: 400
    lineHeight: 1.6
    letterSpacing: "0.04em"
    textTransform: uppercase
  status:
    fontFamily: "IBM Plex Mono, monospace"
    fontSize: "0.88rem"
    fontWeight: 400
    lineHeight: 1.6
rounded:
  none: "0"
  pill: "999px"
  circle: "50%"
spacing:
  s1: "0.5rem"
  s2: "1rem"
  s3: "1.5rem"
  s4: "2.5rem"
  s5: "4rem"
  s6: "clamp(3.5rem, 8vw, 7rem)"
  col-gap: "clamp(1.5rem, 4vw, 4rem)"
  gutter: "clamp(16px, 4vw, 40px)"
  max-width: "1120px"
  measure: "62ch"
components:
  button-primary:
    backgroundColor: "{colors.ember}"
    textColor: "{colors.ember-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0.6em 1.3em"
    height: "2.75rem"
  button-primary-hover:
    backgroundColor: "color-mix(in srgb, {colors.ember} 85%, {colors.ink})"
    textColor: "{colors.ember-ink}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0.6em 1.3em"
    height: "2.75rem"
  button-secondary-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
  chip:
    backgroundColor: "transparent"
    textColor: "{colors.stone}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0.4em 1em"
    height: "2.5rem"
  chip-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.ground}"
  bio-card:
    backgroundColor: "{colors.ash}"
    textColor: "{colors.ink}"
    padding: "{spacing.s3}"
    rounded: "{rounded.none}"
  nav-link:
    textColor: "{colors.stone}"
    typography: "{typography.label}"
    height: "2.75rem"
  nav-link-current:
    textColor: "{colors.ink}"
---

## Overview

russellbuzby.com is a personal site for one person with two registers: a management consultant advising Commonwealth leaders on reform, and a poet writing from Braidwood in the southern tablelands of New South Wales. The design holds both in one voice. Cormorant Garamond carries every heading and poem title; IBM Plex Sans carries all reading text and interface labels; IBM Plex Mono is reserved for dates and prize status lines, the way a radio log or a coronial record would set them. The ground is smoke, the ink is charcoal, and there is one accent, ember, spent on the primary button, prize status lines, the active nav underline and the quotation rule. Photographs are the owner's own: the bark portrait, the fireground, the festival stage.

Surface modes: Home, About and Contact persuade; Insights and articles are for reading; Poetry is an experience page. Every page renders in light and dark, driven by the same token set.

## Colors

- **ground** `#ECEBE6` is the page. **ash** `#E1DFD8` is the only raised surface (bio cards, image placeholders). **line** `#CFCCC3` draws every hairline rule.
- **ink** `#1B1D20` is all reading text, headings and the secondary button border. Body text is never grey.
- **stone** `#5F5E57` is secondary text only: bylines, dates, captions, article summaries in lists, poem blurbs, chrome links (nav, footer, jump links, references). Contrast on ground 5.4:1, on ash 4.9:1.
- **ember** `#A3361C` is the single accent. It fills the primary button, colours prize status lines, underlines the current nav item and rules the epigraph. It is never used for body links or decorative fills.
- **ember-ink** `#FFF6F1` is text on ember.
- Dark theme swaps the set (`dark-*` tokens) under `prefers-color-scheme: dark` guarded by `:root:not([data-theme="light"])`, and again under `:root[data-theme="dark"]`. Ember lifts to `#E07A58` on the dark ground. Every text token clears 4.5:1 in both themes.

## Typography

Roles, desktop maximum:

| Role | Face | Size | Weight |
| --- | --- | --- | --- |
| Page title (h1) | Cormorant | 3.6rem | 500 |
| Home doors (h2 in `.register`) | Cormorant | 2.25rem | 500 |
| Section heading (h2) | Cormorant | 1.75rem | 600 |
| Poem title (h3 in `.poem`) | Cormorant italic | 1.6rem | 600 |
| Item title (article, news) | Cormorant | 1.35rem | 600 |
| Lede | Plex Sans | 1.15rem | 400 |
| Body | Plex Sans | 1.0625rem | 400 |
| Label (nav, buttons, chips, small heads) | Plex Sans caps, 0.1em tracking | 0.78rem | 500 |
| Log (dates, themes) | Plex Mono caps | 0.78rem | 400 |
| Status (prize lines) | Plex Mono, ember | 0.88rem | 400 |

Rules: weight carries the step between title and section as well as size. The lede is in the reading face and in ink, never grey; the home page has no lede, its byline is the standfirst. Body measure is 62ch. Headings use `text-wrap: balance`. Dates and figures use tabular numerals. Curly quotes only, no em dashes anywhere.

## Layout

- One wrapper at 1120px with a side gutter of `clamp(16px, 4vw, 40px)`; nothing scrolls sideways at any width.
- Spacing scale `s1` to `s6`: 0.5, 1, 1.5, 2.5, 4rem and a fluid section gap. Use the tokens, not literal rem values. Tight inside a group (s1, s2), generous between groups (s3, s4), one big interval between sections (s6; the Poetry page uses s5 to match About's rhythm).
- Two-column compositions split 7:5 (hero, About, epigraph) or 5:7 (origin, poem rows) with `col-gap`, and collapse to one column at 860px. Article and list rows keep two columns down to 560px, then the list keeps a 72px square thumbnail beside the text.
- Section heads on the home page carry a hairline and a right-aligned "more" link; on every other page an h2 stands alone with s3 above it.
- Masthead: brand left, five caps links right; at phone width the Home link hides and the brand is the home link.
- Article page: date and theme log, title, byline, 2:1 hero, 62ch body, share row, author card, references, earlier/later links.

## Elevation & Depth

None. No shadows, no blur. The only surface above the ground is ash, used for bio cards and as the placeholder tone behind loading photographs. Separation is done with hairlines and space.

## Shapes

Square corners everywhere except filter chips (pill) and the author photo (circle). Photographs are hard-edged with no border. Buttons are 1px-bordered rectangles.

## Components

- **Button pair**: first link ember-filled, the rest outlined in ink; 44px tall, caps label, `scale(.97)` on press, hover only on fine pointers. External links append a small arrow and a screen-reader phrase.
- **Chips**: pill, 40px tall, stone outline; the active chip inverts to ink on ground. Used only for the Insights theme filter.
- **Post card**: thumbnail left (24 per cent, 3:2), log line, title, summary. On the home page, three cards in a row with the log line on one line.
- **Poem row**: italic title and ember mono status left, stone blurb and button pair right, hairline beneath.
- **News list**: month log left, title and one-line body right, hairline beneath.
- **Bio card**: ash panel with a caps heading and a Copy button; three widths (25, 50, 100 words).
- **Epigraph**: italic Cormorant quotation with a hanging ember quotation mark and a 1px ember rule, cite in stone sans.
- **Author card**: 96px circular portrait, name in Cormorant, two lines, three buttons.
- **Share row**: label plus chips for Copy link, LinkedIn, Email and native Share where available.

## Do's and Don'ts

- Do keep body text in ink. Grey is for text that supports the reading text, never the reading text itself.
- Do add a new poem only once it is published or placed, and only as a link to the venue. The site never reproduces a poem.
- Do keep article addresses stable; a renamed file needs the old slug under `aliases`.
- Do spend ember on one thing per view. If a page has two ember elements competing, one of them is wrong.
- Don't add a kicker or eyebrow above a heading. The heading carries its own weight.
- Don't set labels in mono. Mono is for dates, themes and prize lines; labels are Plex Sans caps.
- Don't introduce a card, shadow or rounded panel. The system separates with hairlines and space.
- Don't use em dashes or straight quotes anywhere, including frontmatter.
- Don't write American spellings; the site is Australian English throughout.
