import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

export const THEMES = [
  'Emergency Management & Resilience',
  'AI in Government',
  'Defence',
  'Change & Transformation',
  'Leadership',
] as const;

// Insights: one markdown file per article, named YYYY-MM-DD-slug.md.
// The URL is /YYYY/MM/DD/slug/ so every link ever shared keeps working.
const insights = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/insights' }),
  schema: ({ image }) =>
    z.object({
      title: z.string(),
      date: z.coerce.date(),
      summary: z.string(),
      themes: z.array(z.enum(THEMES)).min(1),
      image: image(),
      imageCredit: z.string().optional(),
      imageAlt: z.string().optional(),
      wordpress: z.string().url().optional(),
      draft: z.boolean().default(false),
      // Old URL slugs for this article (after a file rename). Each one becomes a page that forwards here.
      aliases: z.array(z.string()).default([]),
    }),
});

// Poems: only published or placed work. A poem's text never lives here;
// each entry links to the venue that published it.
const poems = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/poems' }),
  schema: z.object({
    title: z.string(),
    order: z.number(),
    status: z.string(), // e.g. "Winner · 2026 Venie Holmgren Environmental Poetry Prize"
    detail: z.string().optional(), // second status line
    links: z
      .array(z.object({ label: z.string(), url: z.string().url() }))
      .min(1), // first link is the primary button
  }),
});

// Poetry news: reverse-chronological, one file per item.
const news = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/news' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
  }),
});

// Fixed pages: home, about, poetry, contact. Each note's frontmatter holds the
// structured bits (headline, buttons, captions); the body is the prose.
const link = z.object({ label: z.string(), url: z.string() });
const photo = z.object({ image: z.string(), alt: z.string(), caption: z.string().optional() });
const pages = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/pages' }),
  schema: z
    .object({
      title: z.string().optional(),
      headline: z.string(),
      description: z.string().optional(),
      byline: z.string().optional(),
      lede: z.string().optional(),
      buttons: z.array(link).optional(),
      capabilities: z.array(z.string()).optional(),
      evidence: z.array(z.object({ label: z.string(), url: z.string(), title: z.string() })).optional(),
      bio25: z.string().optional(),
      photos: z.array(photo).optional(),
      consulting: z.object({ title: z.string(), lede: z.string(), text: z.string(), buttons: z.array(link) }).optional(),
      poetry: z.object({ title: z.string(), lede: z.string(), text: z.string(), buttons: z.array(link) }).optional(),
      epigraph: z.string().optional(),
      epigraph_cite: z.array(z.string()).optional(),
      headshot: photo.optional(),
      gallery: z.array(photo).optional(),
      origin_photo: photo.optional(),
      instagram_buttons: z.array(link).optional(),
      bio50: z.string().optional(),
      bio100: z.string().optional(),
      photograph_note: z.string().optional(),
      contact_note: z.string().optional(),
      details: z.array(z.object({ label: z.string(), text: z.string() })).optional(),
    })
    .passthrough(),
});

export const collections = { insights, poems, news, pages };
