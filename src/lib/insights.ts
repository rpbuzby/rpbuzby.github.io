import { getCollection, type CollectionEntry } from 'astro:content';

export type Insight = CollectionEntry<'insights'>;

const pad = (n: number) => String(n).padStart(2, '0');

/** /YYYY/MM/DD/slug/ — the same URL shape WordPress used, so old links keep working. */
export function insightPath(entry: Insight): string {
  const d = entry.data.date;
  const slug = entry.id.replace(/^\d{4}-\d{2}-\d{2}-/, '');
  return `/${d.getUTCFullYear()}/${pad(d.getUTCMonth() + 1)}/${pad(d.getUTCDate())}/${slug}/`;
}

export function insightParams(entry: Insight) {
  const d = entry.data.date;
  return {
    year: String(d.getUTCFullYear()),
    month: pad(d.getUTCMonth() + 1),
    day: pad(d.getUTCDate()),
    slug: entry.id.replace(/^\d{4}-\d{2}-\d{2}-/, ''),
  };
}

export function themeSlug(theme: string): string {
  return theme.toLowerCase().replace(/[^a-z]+/g, '-').replace(/(^-|-$)/g, '');
}

export function fmtDate(d: Date): string {
  return new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(d);
}

/** Published insights, newest first. Drafts are excluded from every build. */
export async function publishedInsights(): Promise<Insight[]> {
  const all = await getCollection('insights', ({ data }) => !data.draft);
  return all.sort((a, b) => b.data.date.getTime() - a.data.date.getTime() || b.id.localeCompare(a.id));
}
