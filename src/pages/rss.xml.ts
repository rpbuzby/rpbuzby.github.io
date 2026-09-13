import rss from '@astrojs/rss';
import type { APIContext } from 'astro';
import { publishedInsights, insightPath } from '../lib/insights';

export async function GET(context: APIContext) {
  const posts = await publishedInsights();
  return rss({
    title: 'Russell Buzby · Insights',
    description: 'Writing on emergency management, AI in government, Defence, and change.',
    site: context.site!,
    items: posts.map((p) => ({
      title: p.data.title,
      pubDate: p.data.date,
      description: p.data.summary,
      link: insightPath(p),
      categories: p.data.themes,
    })),
    customData: '<language>en-au</language>',
  });
}
