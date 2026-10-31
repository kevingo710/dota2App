#!/usr/bin/env bash
# Install the JavaScript dependencies when package.json or yarn.lock changed.
#
# Why: agents in unattended runs may not run package managers (install
# scripts execute arbitrary code, so .claude/settings.json does not allow
# them). A change to package.json still needs node_modules and yarn.lock to
# match before the gate means anything; the first React Native upgrade run
# failed four reviews on exactly that. So the harness installs, the same way
# scripts/ios_build.sh runs pod install, and a failure goes back to the agent.
#
# Skips when package.json and yarn.lock hash to the last successful install.
# Used by harness/pipeline.py and harness/run.py before the gate.
#
# Usage: scripts/deps_install.sh [--force]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
STAMP="$ROOT/.harness/deps.stamp"
# The version that wrote yarn.lock (see commit 36cd151).
YARN="yarn@1.22.22"

inputs_hash() { cat package.json yarn.lock 2>/dev/null | shasum -a 256 | cut -d' ' -f1; }

if [[ "${1:-}" != "--force" && -f "$STAMP" && "$(cat "$STAMP")" == "$(inputs_hash)" ]]; then
  echo "==> dependencies unchanged since the last install: skipping"
  exit 0
fi

# Frozen first: when yarn.lock already satisfies package.json (an agent only
# edited "scripts", say), a plain install still re-resolves the lock. On
# 2026-10-31 that rewrote ~2000 unrelated lines and the reviewer failed the
# run. Only a lock that really is out of date gets the plain install.
echo "==> npx $YARN install --frozen-lockfile"
if ! npx --yes "$YARN" install --frozen-lockfile --non-interactive --network-timeout 300000; then
  echo "==> yarn.lock does not match package.json: npx $YARN install"
  npx --yes "$YARN" install --non-interactive --network-timeout 300000
fi
mkdir -p "$(dirname "$STAMP")"
# The install may have rewritten yarn.lock: stamp what is installed now.
inputs_hash >"$STAMP"
echo "==> dependencies installed"
