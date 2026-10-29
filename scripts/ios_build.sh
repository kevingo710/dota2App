#!/usr/bin/env bash
# Rebuild and reinstall the iOS app on the booted simulator when native code
# changed, so the screenshots show the binary the change produces.
#
# Why: visual QA captures the app installed on the simulator. Metro serves the
# new JavaScript, but a change to ios/, android/ or the dependencies (a React
# Native upgrade, a native module) also needs a new binary: JS from one React
# Native version on a binary from another fails at start-up.
#
# Skips the build when the native inputs (ios/, package.json, yarn.lock) hash
# to the same value as the last successful build. Used by harness/pipeline.py
# and harness/run.py before any capture.
#
# Usage:
#   scripts/ios_build.sh            build if the native inputs changed
#   scripts/ios_build.sh --force    build anyway
#   scripts/ios_build.sh --check    exit 1 if a build is needed, build nothing
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
STAMP="$ROOT/.harness/ios-build.stamp"
MODE="${1:-}"

log() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# Hash of every tracked or new file that ends up in the binary (Pods and build
# output excluded: they are derived from these).
inputs_hash() {
  { git ls-files --cached --others --exclude-standard -- ios package.json yarn.lock |
      grep -vE '^ios/(Pods|build)/' | sort | while read -r f; do
        [[ -f "$f" ]] && printf '%s %s\n' "$f" "$(shasum -a 256 "$f" | cut -d' ' -f1)"
      done; } | shasum -a 256 | cut -d' ' -f1
}

HASH="$(inputs_hash)"
if [[ "$MODE" != "--force" && -f "$STAMP" && "$(cat "$STAMP")" == "$HASH" ]]; then
  log "native inputs unchanged since the last build: skipping"
  exit 0
fi
[[ "$MODE" == "--check" ]] && { log "native inputs changed: a build is needed"; exit 1; }

UDID="${UDID:-$(xcrun simctl list devices booted | grep '(Booted)' | head -1 | sed -E 's/.*\(([0-9A-Fa-f-]{36})\).*/\1/')}"
[[ -n "$UDID" ]] || die "no booted simulator; run: xcrun simctl boot <device>"

log "pod install"
(cd ios && bundle exec pod install) || die "pod install failed"

log "building and installing on $UDID (Metro keeps serving this checkout)"
npx react-native run-ios --udid "$UDID" --no-packager || die "iOS build failed"

mkdir -p "$(dirname "$STAMP")"
# pod install may have rewritten Podfile.lock: stamp what was actually built.
inputs_hash >"$STAMP"
log "iOS app rebuilt"
