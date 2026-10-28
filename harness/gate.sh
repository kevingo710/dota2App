#!/usr/bin/env bash
# Deterministic quality gate. Every agent run must pass it before anything is
# reported as done or sent to Telegram. The model never decides that its own
# change is "good enough"; this script does.
#
# Usage: harness/gate.sh [--changed] [--scope] [--json PATH] [--quiet]
#
# --scope: print harness/scope.py's verdict (changed files, screens, shared
# code, quick or full) and exit without running anything.
#
# --changed: the quick level for iterating (harness/scope.py). Lint and Jest
# run only on the changed files and their related tests; types, architecture,
# agents and secrets stay whole (they are project-wide and fast). Never the
# final word: the Stop hook and harness/run.py always run the full gate.
#
# Checks, in order (all run, so one report shows every failure):
#   types         npx tsc --noEmit
#   lint          npx eslint . --ext .ts,.tsx
#   tests         npx jest --ci
#   architecture  harness/check_architecture.py (Clean Architecture layers)
#   agents        harness/agents.py check (opencode copies in sync, every agent has evals)
#   secrets       no Telegram token / private key in tracked or staged files
#
# Exit code 0 only if every check passes. --json writes a machine-readable
# report that harness/run.sh feeds back to the agent on a retry.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

JSON_OUT=""
QUIET=0
CHANGED=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json) JSON_OUT="$2"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    --changed) CHANGED=1; shift ;;
    --scope) exec python3 harness/scope.py ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

LOG_DIR="$(mktemp -d)"
trap 'rm -rf "$LOG_DIR"' EXIT
RESULTS=()
FAILED=0

check() {
  local name="$1"; shift
  local start=$SECONDS status
  if "$@" >"$LOG_DIR/$name.log" 2>&1; then status=pass; else status=fail; FAILED=1; fi
  RESULTS+=("$name|$status|$((SECONDS - start))")
  if [[ "$QUIET" == 0 || "$status" == fail ]]; then
    printf '%-13s %s (%ss)\n' "$name" "$status" "$((SECONDS - start))"
  fi
  if [[ "$status" == fail ]]; then
    tail -40 "$LOG_DIR/$name.log" | sed 's/^/    /'
  fi
}

scan_secrets() {
  # Telegram bot tokens and private keys. Tracked + staged files only, so
  # gitignored local secrets (telegram.md, .env.local) do not trip it.
  ! git ls-files -z --cached | xargs -0 grep -nIE \
    '[0-9]{8,10}:[A-Za-z0-9_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----' 2>/dev/null
}

check types npx tsc --noEmit
if [[ "$CHANGED" == 1 ]]; then
  SCOPE="$(python3 harness/scope.py --json)"
  # Changed TS files that still exist (a deleted file has nothing to lint).
  TS_FILES=()
  while IFS= read -r f; do [[ -f "$f" ]] && TS_FILES+=("$f"); done < <(
    python3 -c 'import json,sys; [print(f) for f in json.load(sys.stdin)["changed"] if f.endswith((".ts", ".tsx"))]' <<<"$SCOPE")
  if [[ ${#TS_FILES[@]} -gt 0 ]]; then
    check lint npx eslint "${TS_FILES[@]}"
    check tests npx jest --ci --silent --passWithNoTests --findRelatedTests "${TS_FILES[@]}"
  else
    [[ "$QUIET" == 1 ]] || echo "lint/tests    skipped (no TS file changed)"
  fi
else
  check lint npx eslint . --ext .ts,.tsx
  check tests npx jest --ci --silent
fi
check architecture python3 harness/check_architecture.py
check agents python3 harness/agents.py check
check secrets scan_secrets

if [[ -n "$JSON_OUT" ]]; then
  mkdir -p "$(dirname "$JSON_OUT")"
  GATE_CHANGED="$CHANGED" python3 - "$LOG_DIR" "$JSON_OUT" "${RESULTS[@]}" <<'PY'
import json, os, sys
from pathlib import Path

log_dir, out, rows = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
checks = []
for row in rows:
    name, status, seconds = row.split("|")
    log = (log_dir / f"{name}.log").read_text(errors="replace")
    checks.append({
        "name": name,
        "status": status,
        "seconds": int(seconds),
        # Only failing output is useful to an agent; keep it short.
        "output": log[-4000:] if status == "fail" else "",
    })
Path(out).write_text(json.dumps(
    {"ok": all(c["status"] == "pass" for c in checks), "checks": checks,
     "scope": "changed" if os.environ.get("GATE_CHANGED") == "1" else "full"}, indent=2))
PY
fi

if [[ "$CHANGED" == 1 ]]; then
  # The agent chose the quick level; tell it when the diff says otherwise.
  python3 -c 'import json, sys
shared = json.load(sys.stdin)["shared"]
for item in shared[:5]:
    print("note: shared code changed (%s: %s)" % (item["file"], item["why"]))
if shared:
    print("note: %d shared file(s): run harness/gate.sh before finishing" % len(shared))' <<<"$SCOPE"
  SUFFIX=" (changed files only; the full gate decides at the end)"
fi
if [[ "$FAILED" == 0 ]]; then
  echo "gate: PASS${SUFFIX:-}"
else
  echo "gate: FAIL${SUFFIX:-}"
fi
exit "$FAILED"
