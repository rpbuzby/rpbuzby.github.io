import { getEntry, render } from 'astro:content';
import type { ImageMetadata } from 'astro';

/** Site photos live in src/assets/site/ and are referenced by filename from the page notes. */
const photos = import.meta.glob<{ default: ImageMetadata }>('../assets/site/*.{jpg,jpeg,png,webp}', { eager: true });
export function sitePhoto(name: string): ImageMetadata {
  const hit = Object.entries(photos).find(([k]) => k.endsWith('/' + name));
  if (!hit) throw new Error(`No site photo named ${name} in src/assets/site/`);
  return hit[1].default;
}

/** Load a fixed page note (home, about, poetry, contact) and its rendered body. */
export async function pageNote(id: string) {
  const entry = await getEntry('pages', id);
  if (!entry) throw new Error(`Missing src/content/pages/${id}.md`);
  const { Content } = await render(entry);
  return { data: entry.data, Content };
}

/** Render a one-line markdown string (links and emphasis only) to HTML. */
export function inline(md: string): string {
  return md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_m, t, u) => `<a href="${u}"${/^https?:/.test(u) ? ' target="_blank" rel="noopener"' : ''}>${t}</a>`)
    .replace(/\*([^*]+)\*/g, '<em>$1</em>');
}
