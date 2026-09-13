import { defineConfig } from 'astro/config';
import sitemap from '@astrojs/sitemap';

export default defineConfig({
  site: 'https://russellbuzby.com',
  trailingSlash: 'always',
  build: { format: 'directory' },
  integrations: [sitemap()],
  markdown: { smartypants: true },
});
