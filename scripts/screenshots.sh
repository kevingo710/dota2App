#!/usr/bin/env bash
# Capture screenshots of every screen on the booted iOS simulator.
# See docs/screenshots.md for the full write-up of the process.
#
# Usage: scripts/screenshots.sh [--wait SECONDS] [--no-verify] [--no-frame] [--out DIR]
#        scripts/screenshots.sh --frame-only   # re-frame existing captures, no simulator
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BUNDLE_ID="${BUNDLE_ID:-org.reactjs.native.example.dota2App}"
HERO_ID="${HERO_ID:-8}"
WAIT_SECONDS="${WAIT_SECONDS:-20}"
OUT_DIR="${OUT_DIR:-screenshots}"
MAX_HEIGHT="${MAX_HEIGHT:-1200}"
METRO_PORT="${METRO_PORT:-8081}"
VERIFY=1
FRAME=1
FRAME_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --wait) WAIT_SECONDS="$2"; shift 2 ;;
    --no-verify) VERIFY=0; shift ;;
    --no-frame) FRAME=0; shift ;;
    --frame-only) FRAME_ONLY=1; shift ;;
    --out) OUT_DIR="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,7p' "$0"
      exit 0
      ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

log() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

expected_text() {
  case "$1" in
    home) echo "Dota 2 Heroes" ;;
    explore) echo "Filter the roster" ;;
    superstar) echo "Superstar" ;;
    detail) echo "Juggernaut" ;;
    settings) echo "Clear cached data" ;;
    *) die "no expected text for screen '$1'" ;;
  esac
}

# Headline drawn above each device in screenshots/framed/ (README gallery)
store_title() {
  case "$1" in
    home) echo "Every hero, one search away" ;;
    explore) echo "Filter by attribute and role" ;;
    superstar) echo "A new hero every day" ;;
    detail) echo "Stats, attributes and abilities" ;;
    settings) echo "Sources and cache in one place" ;;
    *) die "no store title for screen '$1'" ;;
  esac
}

SCREENS=(home explore superstar detail settings)

# Put every capture in $OUT_DIR inside an iPhone frame with its headline.
frame_all() {
  local bin
  bin="$(mktemp -d)/frame_screenshot"
  log "compiling device framer"
  swiftc -O -o "$bin" "$ROOT/scripts/frame_screenshot.swift"
  mkdir -p "$OUT_DIR/framed"
  for screen in "${SCREENS[@]}"; do
    [[ -f "$OUT_DIR/$screen.png" ]] || die "missing $OUT_DIR/$screen.png"
    "$bin" "$OUT_DIR/$screen.png" "$OUT_DIR/framed/$screen.png" "$(store_title "$screen")"
    log "wrote $OUT_DIR/framed/$screen.png"
  done
  rm -rf "$(dirname "$bin")"
}

if [[ "$FRAME_ONLY" == 1 ]]; then
  frame_all
  exit 0
fi

# --- preflight ---------------------------------------------------------------

command -v xcrun >/dev/null || die "xcrun not found (Xcode required)"
UDID="${UDID:-$(xcrun simctl list devices booted | grep '(Booted)' | head -1 | sed -E 's/.*\(([0-9A-Fa-f-]{36})\).*/\1/')}"
[[ -n "$UDID" ]] || die "no booted simulator; run: xcrun simctl boot <device> (see xcrun simctl list devices)"
xcrun simctl listapps "$UDID" | grep -q "$BUNDLE_ID" ||
  die "app $BUNDLE_ID not installed on $UDID; run: yarn ios"

STARTED_METRO=0
if ! (echo >"/dev/tcp/127.0.0.1/$METRO_PORT") 2>/dev/null; then
  log "Metro not listening on :$METRO_PORT, starting it"
  npx react-native start --port "$METRO_PORT" >/tmp/dota2-metro.log 2>&1 &
  for _ in $(seq 1 60); do
    (echo >"/dev/tcp/127.0.0.1/$METRO_PORT") 2>/dev/null && break
    sleep 1
  done
  (echo >"/dev/tcp/127.0.0.1/$METRO_PORT") 2>/dev/null || die "Metro did not start; see /tmp/dota2-metro.log"
  STARTED_METRO=1
fi

TMP="$(mktemp -d)"
APP_BACKUP="$TMP/App.tsx.bak"
OCR_BIN="$TMP/verify_screen"

restore() {
  cp "$APP_BACKUP" "$ROOT/App.tsx"
  [[ "$STARTED_METRO" == 1 ]] && kill %1 2>/dev/null || true
  rm -rf "$TMP"
}
cp "$ROOT/App.tsx" "$APP_BACKUP"
trap restore EXIT

if [[ "$VERIFY" == 1 ]]; then
  if [[ ! -x "$OCR_BIN" || "$ROOT/scripts/verify_screen.swift" -nt "$OCR_BIN" ]]; then
    log "compiling OCR verifier"
    swiftc -O -o "$OCR_BIN" "$ROOT/scripts/verify_screen.swift"
  fi
fi

mkdir -p "$OUT_DIR"

# --- capture -----------------------------------------------------------------

log "launching $BUNDLE_ID on $UDID"
xcrun simctl launch "$UDID" "$BUNDLE_ID" >/dev/null

for screen in "${SCREENS[@]}"; do
  log "capturing $screen (waiting ${WAIT_SECONDS}s for reload + data)"
  python3 "$ROOT/scripts/patch_app_for_screenshots.py" "$screen"
  sleep "$WAIT_SECONDS"

  full="$TMP/$screen-full.png"
  xcrun simctl io "$UDID" screenshot "$full" >/dev/null 2>&1

  if [[ "$VERIFY" == 1 ]]; then
    "$OCR_BIN" "$full" "$(expected_text "$screen")" >"$TMP/$screen.txt" ||
      die "verification failed for '$screen' (expected: $(expected_text "$screen")); see $TMP/$screen.txt"
  fi

  sips -Z "$MAX_HEIGHT" "$full" --out "$OUT_DIR/$screen.png" >/dev/null
  log "wrote $OUT_DIR/$screen.png"
done

[[ "$FRAME" == 1 ]] && frame_all

log "done: ${SCREENS[*]} in $OUT_DIR/ (App.tsx restored)"
