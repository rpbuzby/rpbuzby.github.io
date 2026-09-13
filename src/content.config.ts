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
      wordpress: z.string().url().optional(),
      draft: z.boolean().default(false),
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

export const collections = { insights, poems, news };
