#!/usr/bin/env bash
# Prove in a real browser that the web build keeps the browser's Back and
# Forward working (scenarios A to F in scripts/verify-web-history.cjs).
#
# Why a script: Jest cannot exercise session history or iframes, and the design
# relies on useLinking internals, so a React Navigation bump can break it
# silently. The harness gate does not run this; run it by hand after changing
# linking.web.ts, the navigators or @react-navigation/*.
#
# Builds the app for both bases the code must support (/mobadex/app/ as on
# GitHub Pages, next to the landing page, and /). It skips the networked Valve
# snapshot: the browser script mocks the hero data. Playwright is pinned and
# lives in a cache outside the repo so package.json and yarn.lock stay as they
# are; its browser is only downloaded if Playwright's own cache lacks it.
#
# Usage: scripts/verify-web-history.sh
# Exit code 0 only if every scenario passes.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PLAYWRIGHT_VERSION="1.64.1"
PLAYWRIGHT_DIR="${XDG_CACHE_HOME:-$HOME/.cache}/dota2app/playwright-$PLAYWRIGHT_VERSION"

log() { printf '==> %s\n' "$*"; }

WORK="$(mktemp -d)"
SERVER_PIDS=()
cleanup() {
  for pid in ${SERVER_PIDS[@]+"${SERVER_PIDS[@]}"}; do
    kill "$pid" 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  done
  rm -rf "$WORK"
}
trap cleanup EXIT

if [[ ! -d "$PLAYWRIGHT_DIR/node_modules/playwright" ]]; then
  log "installing playwright@$PLAYWRIGHT_VERSION in $PLAYWRIGHT_DIR"
  mkdir -p "$PLAYWRIGHT_DIR"
  npm install --prefix "$PLAYWRIGHT_DIR" --no-audit --no-fund --silent \
    "playwright@$PLAYWRIGHT_VERSION"
fi
log "checking the Playwright browser"
node "$PLAYWRIGHT_DIR/node_modules/playwright/cli.js" install --no-shell chromium

log "building for /mobadex/app/"
PUBLIC_PATH=/mobadex/app/ npx webpack --mode production \
  --output-path "$WORK/pages/mobadex/app" >"$WORK/build-pages.log" 2>&1 ||
  { cat "$WORK/build-pages.log" >&2; exit 1; }
# The same landing tree as scripts/build-pages.sh, minus the Valve snapshot.
cp web/landing/index.html "$WORK/pages/mobadex/index.html"
mkdir -p "$WORK/pages/mobadex/viewer"
cp harness/viewer/index.html harness/viewer/snapshot.json "$WORK/pages/mobadex/viewer/"

log "building for /"
PUBLIC_PATH=/ npx webpack --mode production \
  --output-path "$WORK/root" >"$WORK/build-root.log" 2>&1 ||
  { cat "$WORK/build-root.log" >&2; exit 1; }

free_port() {
  python3 -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
}

# Sets SERVED_URL; not run in a subshell so the cleanup trap knows the PID.
serve() {
  local dir="$1" port
  port="$(free_port)"
  python3 -m http.server "$port" --bind 127.0.0.1 --directory "$dir" >/dev/null 2>&1 &
  SERVER_PIDS+=("$!")
  SERVED_URL="http://127.0.0.1:$port"
  for _ in {1..50}; do
    curl -s -o /dev/null "$SERVED_URL/" && return 0
    python3 -c 'import time; time.sleep(0.1)'
  done
  printf 'error: the server for %s did not start\n' "$dir" >&2
  return 1
}

serve "$WORK/pages"
PAGES_URL="$SERVED_URL"
serve "$WORK/root"
ROOT_URL="$SERVED_URL"

log "running the scenarios"
NODE_PATH="$PLAYWRIGHT_DIR/node_modules" node scripts/verify-web-history.cjs "$PAGES_URL" "$ROOT_URL"
