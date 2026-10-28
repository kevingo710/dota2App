#!/usr/bin/env bash
# Capture a screen of the app and send it to Telegram.
#
# Used by the "visual change" workflow: after a UI change, capture the running
# app and push the screenshot to the bot so the change can be reviewed on the
# phone. See docs/telegram.md for the full flow.
#
# Usage:
#   scripts/telegram.sh                        # capture the booted simulator
#   scripts/telegram.sh --screen superstar     # seed a screen, then capture
#   scripts/telegram.sh --file /tmp/shot.png   # send an existing image
#   scripts/telegram.sh --screen superstar --dry-run
#   scripts/telegram.sh --text "gate: FAIL"    # plain text message
#
# Options:
#   --file PATH      Send an existing image instead of capturing.
#   --screen NAME    Screen to seed before capturing
#                    (home|explore|superstar|settings|detail).
#   --caption TEXT   Caption of the message.
#   --text TEXT      Send a text message (no capture). Used by harness/run.sh.
#   --chat ID        Override the destination chat id.
#   --wait SECONDS   Wait after seeding the screen (default 20).
#   --out PATH       Also copy the captured image to PATH.
#   --expect TEXT    Extra text the OCR must find (repeatable). Used by the
#                    harness to check what the planner promised.
#   --no-verify      Skip the OCR verification of the captured image.
#   --dry-run        Capture and verify, but do not send anything.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BUNDLE_ID="${BUNDLE_ID:-org.reactjs.native.example.dota2App}"
WAIT_SECONDS="${WAIT_SECONDS:-20}"
MAX_HEIGHT="${MAX_HEIGHT:-1200}"
FILE=""
SCREEN=""
CAPTION=""
TEXT=""
CHAT=""
OUT=""
VERIFY=1
EXPECTS=()
DRY_RUN=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file) FILE="$2"; shift 2 ;;
    --screen) SCREEN="$2"; shift 2 ;;
    --caption) CAPTION="$2"; shift 2 ;;
    --text) TEXT="$2"; shift 2 ;;
    --chat) CHAT="$2"; shift 2 ;;
    --wait) WAIT_SECONDS="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --expect) EXPECTS+=("$2"); shift 2 ;;
    --no-verify) VERIFY=0; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help)
      sed -n '2,24p' "$0"
      exit 0
      ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

log() { printf '==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

# --- credentials -------------------------------------------------------------

# Order: environment > .env.local (gitignored) > ~/.config/dota2app/telegram.env
#       > legacy telegram.md in the repo root.
load_env_file() {
  local file="$1"
  [[ -f "$file" ]] || return 1
  local line key value
  while IFS= read -r line; do
    line="${line#"${line%%[![:space:]]*}"}"
    [[ "$line" == export\ * ]] && line="${line#export }"
    [[ "$line" == *=* ]] || continue
    key="${line%%=*}"
    value="${line#*=}"
    value="${value%\"}"; value="${value#\"}"
    value="${value%\'}"; value="${value#\'}"
    key="${key//[[:space:]]/}"
    [[ "$key" == TG_TOKEN && -z "${TG_TOKEN:-}" ]] && TG_TOKEN="$value"
    [[ "$key" == TG_CHAT && -z "${TG_CHAT:-}" ]] && TG_CHAT="$value"
  done < "$file"
  return 0
}

TG_TOKEN="${TG_TOKEN:-}"
TG_CHAT="${TG_CHAT:-}"
load_env_file "$ROOT/.env.local" || true
load_env_file "$HOME/.config/dota2app/telegram.env" || true

if [[ -z "$TG_TOKEN" && -f "$ROOT/telegram.md" ]]; then
  TG_TOKEN="$(grep -oE '[0-9]{6,}:[A-Za-z0-9_-]{30,}' "$ROOT/telegram.md" | head -1)"
  [[ -z "$TG_CHAT" ]] && TG_CHAT="$(grep -oE 'TG_CHAT="[0-9]+"' "$ROOT/telegram.md" | grep -oE '[0-9]+' | head -1)"
fi

[[ -n "$CHAT" ]] && TG_CHAT="$CHAT"

if [[ "$DRY_RUN" == 0 ]]; then
  [[ -n "$TG_TOKEN" ]] || die "TG_TOKEN not found (set it in the environment, in .env.local or in ~/.config/dota2app/telegram.env)"
  [[ -n "$TG_CHAT" ]] || die "TG_CHAT not found (set it in the environment, in .env.local or in ~/.config/dota2app/telegram.env)"
fi

# Prints a one-line summary of a Bot API response, fails on ok=false.
check_response() {
  python3 - "$1" <<'PY'
import json, sys

try:
    data = json.loads(sys.argv[1])
except json.JSONDecodeError:
    sys.exit("error: unexpected response from the Telegram API")

if not data.get("ok"):
    sys.exit(f"error: {data.get('description', 'unknown error')}")

result = data["result"]
chat = result.get("chat", {})
print(f"sent: message_id={result.get('message_id')} chat={chat.get('title') or chat.get('username') or chat.get('id')}")
PY
}

# --- text --------------------------------------------------------------------

if [[ -n "$TEXT" ]]; then
  if [[ "$DRY_RUN" == 1 ]]; then
    log "dry run: would send text to chat $TG_CHAT"
    printf '%s\n' "$TEXT"
    exit 0
  fi
  # Telegram caps messages at 4096 characters.
  check_response "$(curl -s --data-urlencode "chat_id=$TG_CHAT" \
    --data-urlencode "text=${TEXT:0:4000}" \
    "https://api.telegram.org/bot$TG_TOKEN/sendMessage")"
  exit 0
fi

# --- capture -----------------------------------------------------------------

TMP="$(mktemp -d)"
APP_BACKUP="$TMP/App.tsx.bak"
# Compiled once and cached; recompiled when the Swift source changes.
OCR_BIN="${XDG_CACHE_HOME:-$HOME/.cache}/dota2app/verify_screen"
SHOT="$TMP/shot.png"

cleanup() {
  if [[ -f "$APP_BACKUP" ]]; then
    cp "$APP_BACKUP" "$ROOT/App.tsx"
  fi
  rm -rf "$TMP"
}
trap cleanup EXIT

if [[ -n "$SCREEN" ]]; then
  command -v xcrun >/dev/null || die "xcrun not found (Xcode required)"
  UDID="${UDID:-$(xcrun simctl list devices booted | grep '(Booted)' | head -1 | sed -E 's/.*\(([0-9A-Fa-f-]{36})\).*/\1/')}"
  [[ -n "$UDID" ]] || die "no booted simulator; run: xcrun simctl boot <device>"
  xcrun simctl listapps "$UDID" | grep -q "$BUNDLE_ID" ||
    die "app $BUNDLE_ID not installed; run: yarn ios"

  cp "$ROOT/App.tsx" "$APP_BACKUP"
  log "seeding screen '$SCREEN'"
  python3 "$ROOT/scripts/patch_app_for_screenshots.py" "$SCREEN"
  # Cold restart: Fast Refresh cannot recover an app stuck on a red box (e.g.
  # Metro was down), and a fresh launch loads the seeded bundle directly.
  xcrun simctl terminate "$UDID" "$BUNDLE_ID" >/dev/null 2>&1 || true
  xcrun simctl launch "$UDID" "$BUNDLE_ID" >/dev/null 2>&1 || true
  log "waiting ${WAIT_SECONDS}s for the reload"
  sleep "$WAIT_SECONDS"

  xcrun simctl io "$UDID" screenshot "$SHOT" >/dev/null 2>&1 ||
    die "screenshot failed"
else
  [[ -n "$FILE" ]] || die "nothing to send: pass --file PATH or --screen NAME"
  [[ -f "$FILE" ]] || die "file not found: $FILE"
  cp "$FILE" "$SHOT"
fi

sips -Z "$MAX_HEIGHT" "$SHOT" --out "$SHOT" >/dev/null

if [[ "$VERIFY" == 1 && -n "$SCREEN" ]]; then
  if [[ ! -x "$OCR_BIN" || "$ROOT/scripts/verify_screen.swift" -nt "$OCR_BIN" ]]; then
    log "compiling OCR verifier"
    mkdir -p "$(dirname "$OCR_BIN")"
    swiftc -O -o "$OCR_BIN" "$ROOT/scripts/verify_screen.swift"
  fi
  case "$SCREEN" in
    home) EXPECTS=("Dota 2 Heroes" ${EXPECTS[@]+"${EXPECTS[@]}"}) ;;
    explore) EXPECTS=("Filter the roster" ${EXPECTS[@]+"${EXPECTS[@]}"}) ;;
    superstar) EXPECTS=("Superstar" ${EXPECTS[@]+"${EXPECTS[@]}"}) ;;
    detail) EXPECTS=("Juggernaut" ${EXPECTS[@]+"${EXPECTS[@]}"}) ;;
    settings) EXPECTS=("Clear cached data" ${EXPECTS[@]+"${EXPECTS[@]}"}) ;;
  esac
  for EXPECTED in ${EXPECTS[@]+"${EXPECTS[@]}"}; do
    if ! "$OCR_BIN" "$SHOT" "$EXPECTED" >"$TMP/ocr.txt"; then
      [[ -n "$OUT" ]] && cp "$SHOT" "$OUT"
      sed 's/^/    ocr: /' "$TMP/ocr.txt" >&2
      die "verification failed (expected: $EXPECTED)"
    fi
    log "OCR ok: found '$EXPECTED'"
  done
fi

[[ -n "$OUT" ]] && cp "$SHOT" "$OUT" && log "image saved to $OUT"

if [[ "$DRY_RUN" == 1 ]]; then
  log "dry run: would send $SHOT to chat $TG_CHAT (caption: ${CAPTION:-none})"
  exit 0
fi

# --- send --------------------------------------------------------------------

[[ -n "$CAPTION" ]] || CAPTION="Dota 2 App${SCREEN:+ - $SCREEN}"
# Telegram caps photo captions at 1024 characters.
CAPTION="${CAPTION:0:1000}"

log "sending to Telegram chat $TG_CHAT"
# --form-string, not -F: captions are written by agents, and -F reads a local
# file when the value starts with @ or < (an injected "@~/.ssh/id_rsa" caption
# would upload that file).
RESPONSE="$(curl -s --form-string "chat_id=$TG_CHAT" -F "photo=@$SHOT" \
  --form-string "caption=$CAPTION" \
  "https://api.telegram.org/bot$TG_TOKEN/sendPhoto")"

check_response "$RESPONSE"
printf 'caption: %s\n' "$CAPTION"
