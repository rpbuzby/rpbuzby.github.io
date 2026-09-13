#!/bin/sh
# Commit every content change and push. GitHub Pages rebuilds the site in about a minute.
#   ~/Projects/russellbuzby.com/scripts/publish.sh ["message"]
set -e
cd "$(dirname "$0")/.."
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
  echo "Nothing to publish."; exit 0
fi
git add -A
git commit -q -m "${1:-Content update $(date '+%Y-%m-%d %H:%M')}"
git push -q
echo "Pushed. https://russellbuzby.com rebuilds in about a minute:"
echo "https://github.com/rpbuzby/rpbuzby.github.io/actions"
