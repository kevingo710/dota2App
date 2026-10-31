#!/usr/bin/env bash
# Assemble the GitHub Pages site (https://kevingo710.github.io/dota2App/):
#
#   /          web/landing/index.html: the agent graph and the app side by side
#   /app/      the React Native app built for the web (webpack + react-native-web)
#              plus the Valve hero snapshot it reads (scripts/snapshot-herodata.mjs)
#   /viewer/   harness/viewer in static mode, drawing harness/viewer/snapshot.json
#
# Why: the Pages workflow and a local preview must build the same tree, so the
# layout lives here once instead of in the workflow's YAML.
#
# Usage: scripts/build-pages.sh [outDir]        (default: _site)
#        PAGES_BASE=/ scripts/build-pages.sh    for a site served from the root
# Preview: serve the parent of a folder named like the base, e.g.
#        scripts/build-pages.sh /tmp/site/dota2App && python3 -m http.server -d /tmp/site
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
OUT="${1:-_site}"
BASE="${PAGES_BASE:-/dota2App/}"

case "$OUT" in
  "" | / | . | ..) echo "refusing to use '$OUT' as the output directory" >&2; exit 2 ;;
esac
rm -rf "$OUT"
mkdir -p "$OUT/viewer"
OUT="$(cd "$OUT" && pwd)"

echo "==> app: webpack, public path ${BASE}app/"
PUBLIC_PATH="${BASE}app/" npx webpack --mode production --output-path "$OUT/app"

echo "==> app: Valve hero snapshot"
node scripts/snapshot-herodata.mjs "$OUT/app"

echo "==> landing and viewer"
cp web/landing/index.html "$OUT/index.html"
cp harness/viewer/index.html harness/viewer/snapshot.json "$OUT/viewer/"
# Plain files: no Jekyll processing on Pages.
touch "$OUT/.nojekyll"

echo "==> site ready: $OUT"
