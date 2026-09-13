# Cutover: WordPress.com to GitHub Pages

The domain stays registered at WordPress.com (Automattic, paid to 20 Feb 2028). Only its DNS records change. There is no email on the domain, so nothing else moves.

## Before cutover (done)

- Site built and deployed to GitHub Pages from `rpbuzby/rpbuzby.github.io`, preview at https://rpbuzby.github.io/
- All 71 articles exported, same `/YYYY/MM/DD/slug/` URLs, RSS at `/rss.xml`, `/feed/` forwards to it
- `docs/CNAME` holds the domain file, parked so the preview URL keeps working

## Cutover steps (Russell)

1. **Check the preview** at https://rpbuzby.github.io/ and spot-check three old article links by swapping the host, e.g. https://rpbuzby.github.io/2026/08/20/au-audit-for-a-workforce-that-isnt-there/
2. **Move the CNAME file into place** and push (or ask Claude to):
   ```
   cd ~/Projects/russellbuzby.com && git mv docs/CNAME public/CNAME && git commit -m "Custom domain" && git push
   ```
   Then in GitHub: repo → Settings → Pages → Custom domain shows `russellbuzby.com`. Tick “Enforce HTTPS” once the DNS check passes (it can take up to an hour after step 3).
3. **Point the DNS at GitHub.** In WordPress.com: My Sites → Upgrades → Domains → russellbuzby.com → DNS records → Manage. Add these records (WordPress.com will warn that the domain will stop pointing at the WordPress site; that is the intent):

   | Type | Name | Value |
   | --- | --- | --- |
   | A | @ | 185.199.108.153 |
   | A | @ | 185.199.109.153 |
   | A | @ | 185.199.110.153 |
   | A | @ | 185.199.111.153 |
   | AAAA | @ | 2606:50c0:8000::153 |
   | AAAA | @ | 2606:50c0:8001::153 |
   | AAAA | @ | 2606:50c0:8002::153 |
   | AAAA | @ | 2606:50c0:8003::153 |
   | CNAME | www | rpbuzby.github.io |

   If WordPress.com’s editor will not let the root A records override its own, the fallback is to change the domain’s nameservers to Cloudflare (free account, add site, copy the two nameservers into WordPress.com → Domains → Name servers) and add the same records there with the proxy switched off.
4. **Wait and verify.** `dig +short russellbuzby.com` should return the four GitHub addresses. Open https://russellbuzby.com/ and one old article URL. HTTPS shows a GitHub certificate.
5. **Let the WordPress.com site plan lapse** at its next renewal, keeping only the domain registration. Do not delete the WordPress site until the new one has been live for a month; it is the rollback (remove the A records and the domain points back within the hour).

## After cutover

- New articles: `python3 scripts/publish_article.py "<vault article>.md" --push`
- New poem or news item: add a file in `src/content/poems/` or `src/content/news/`, push
- Article images from the vault `Images/` folder are copied by the publish script; the site serves optimised WebP from them
