#!/usr/bin/env bash
# Make sure the environment can actually show a change before an agent run:
# booted iOS simulator, app installed, Metro serving this checkout, Telegram
# credentials present. Fixes what it can (starts Metro), fails loudly on the rest.
#
# Usage: harness/preflight.sh [--backend claude|opencode|hybrid] [--route=AGENT=ROUTE]... [--no-visual] [--no-telegram]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BUNDLE_ID="${BUNDLE_ID:-org.reactjs.native.example.dota2App}"
METRO_PORT="${METRO_PORT:-8081}"
STATE_DIR="$ROOT/.harness"
VISUAL=1
TELEGRAM=1
BACKEND=claude
ROUTES=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --backend) BACKEND="$2"; shift 2 ;;
    --route=*) ROUTES+=(--route "${1#--route=}"); shift ;;
    --no-visual) VISUAL=0; shift ;;
    --no-telegram) TELEGRAM=0; shift ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

ok() { printf '  ok    %s\n' "$*"; }
die() { printf '  FAIL  %s\n' "$*" >&2; exit 1; }

# Which runtimes this run needs: every agent's route (harness/backends.py).
ROSTER="$(python3 harness/agents.py roster --backend "$BACKEND" ${ROUTES[@]+"${ROUTES[@]}"} --models)" \
  || die "bad backend or route"
LOCAL_MODELS="$(awk '$2 !~ /^claude/ && $3 ~ /^ollama\// {sub("ollama/", "", $3); print $3}' <<<"$ROSTER" | sort -u)"

if grep -qv ' claude' <<<"$ROSTER"; then
  command -v opencode >/dev/null || die "opencode not found (brew install sst/tap/opencode)"
  ok "opencode $(opencode --version 2>/dev/null)"
  curl -sf http://localhost:11434/api/version >/dev/null || die "Ollama not running (ollama serve)"
  # Every model a local route uses must exist locally.
  for model in $LOCAL_MODELS; do
    ollama list | awk '{print $1}' | grep -qx "$model" || die "model $model missing; run harness/local/setup.sh"
    ok "ollama $model"
  done
  python3 harness/agents.py check >/dev/null || die "opencode agents out of sync; run harness/agents.py sync"
  # Ollama serves one model at a time on most Macs: another workload holding
  # the GPU queues every agent call behind it (minutes per step).
  others="$(ollama ps | awk 'NR>1 {print $1}' | grep -vxF -f <(echo "$LOCAL_MODELS") || true)"
  [[ -z "$others" ]] || printf '  warn  other models loaded in Ollama (%s): local runs will be slow\n' "$(echo $others)"
fi
if grep -q ' claude' <<<"$ROSTER"; then
  command -v claude >/dev/null || die "claude CLI not found (npm i -g @anthropic-ai/claude-code)"
  ok "claude $(claude --version 2>/dev/null | head -1)"
fi
[[ -d node_modules ]] || die "node_modules missing; run: yarn install"
ok "node_modules"

if [[ "$VISUAL" == 1 ]]; then
  command -v xcrun >/dev/null || die "xcrun not found (Xcode required)"
  UDID="$(xcrun simctl list devices booted | grep '(Booted)' | head -1 | sed -E 's/.*\(([0-9A-Fa-f-]{36})\).*/\1/')"
  [[ -n "$UDID" ]] || die "no booted simulator; run: xcrun simctl boot \"iPhone 18 Pro\""
  ok "simulator $UDID"
  xcrun simctl listapps "$UDID" | grep -q "$BUNDLE_ID" || die "app not installed; run: yarn ios"
  ok "app $BUNDLE_ID installed"

  if ! (echo >"/dev/tcp/127.0.0.1/$METRO_PORT") 2>/dev/null; then
    mkdir -p "$STATE_DIR"
    # Detached on purpose: Metro outlives this run so the bot can reuse it.
    nohup npx react-native start --port "$METRO_PORT" >"$STATE_DIR/metro.log" 2>&1 &
    echo $! >"$STATE_DIR/metro.pid"
    for _ in $(seq 1 60); do
      (echo >"/dev/tcp/127.0.0.1/$METRO_PORT") 2>/dev/null && break
      sleep 1
    done
    (echo >"/dev/tcp/127.0.0.1/$METRO_PORT") 2>/dev/null ||
      die "Metro did not start; see .harness/metro.log"
    ok "Metro started on :$METRO_PORT (pid $(cat "$STATE_DIR/metro.pid"))"
  else
    ok "Metro on :$METRO_PORT"
  fi
fi

if [[ "$TELEGRAM" == 1 ]]; then
  # Never print the token; only check that the dry run can resolve a chat.
  scripts/telegram.sh --text preflight --dry-run >/dev/null 2>&1 ||
    die "Telegram credentials not found (see docs/telegram.md)"
  [[ -n "${TG_TOKEN:-}" || -f "$ROOT/.env.local" || -f "$HOME/.config/dota2app/telegram.env" || -f "$ROOT/telegram.md" ]] ||
    die "Telegram credentials not found (see docs/telegram.md)"
  ok "Telegram credentials"
fi
