#!/usr/bin/env python3
"""PreToolUse guard: the rules a prompt cannot enforce.

Always:
  - no reading or writing Telegram credentials (the scripts load them).
  - no calling api.telegram.org by hand (everything goes through
    scripts/telegram.sh, which verifies before sending).
  - no destructive git (reset --hard, clean -f, push --force) or --no-verify.

Only in unattended runs (HARNESS_MANAGED=1, set by harness/run.sh):
  - no git push / commit (the harness commits after its own gate).
  - no edits to .claude/, harness/ or scripts/: an agent must not be able to
    weaken the checks that judge it.

Exit 2 blocks the tool call; stderr is shown to the model as the reason.
"""

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parents[2]))
MANAGED = os.environ.get("HARNESS_MANAGED") == "1"

SECRET_PATTERNS = [
    r"telegram\.env",
    r"\.env\.local\b",
    r"\.config/dota2app",
    r"(?<![\w/.-])telegram\.md\b",  # repo-root legacy file, not docs/telegram.md
    r"\bTG_TOKEN\b",
]
ALWAYS_BLOCKED_BASH = [
    (r"api\.telegram\.org", "send through scripts/telegram.sh, not curl"),
    (r"\bgit\s+reset\s+--hard\b", "destructive: git reset --hard"),
    (r"\bgit\s+clean\s+-\w*f", "destructive: git clean -f"),
    (r"\bgit\s+push\b.*(--force|-f\b)", "destructive: force push"),
    (r"--no-verify\b", "hooks must not be skipped"),
    (r"\brm\s+-\w*r\w*\s+(/|~|\$HOME)(\s|$)", "destructive: rm -r on / or ~"),
]
MANAGED_BLOCKED_BASH = [
    (r"\bgit\s+(push|commit|checkout|switch|merge|rebase)\b",
     "the harness owns git in unattended runs"),
]
PROTECTED_DIRS = (".claude", "harness", "scripts")


def block(reason: str) -> None:
    print(f"blocked by .claude/hooks/guard.py: {reason}", file=sys.stderr)
    sys.exit(2)


def is_secret_path(path: str) -> bool:
    p = Path(path).expanduser()
    resolved = p if p.is_absolute() else (ROOT / p)
    resolved = resolved.resolve()
    if resolved == ROOT / "telegram.md":
        return True
    return p.name in {"telegram.env", ".env.local"} or ".config/dota2app" in str(resolved)


def main() -> None:
    event = json.load(sys.stdin)
    tool = event.get("tool_name", "")
    args = event.get("tool_input", {}) or {}

    if tool == "Bash":
        command = args.get("command", "")
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, command):
                block("credentials are off-limits; scripts/telegram.sh loads them itself")
        rules = ALWAYS_BLOCKED_BASH + (MANAGED_BLOCKED_BASH if MANAGED else [])
        for pattern, reason in rules:
            if re.search(pattern, command):
                block(reason)
        return

    path = args.get("file_path") or args.get("notebook_path") or ""
    if not path:
        return
    if is_secret_path(path):
        block("credentials are off-limits; scripts/telegram.sh loads them itself")
    if MANAGED and tool in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
        try:
            rel = Path(path).resolve().relative_to(ROOT)
        except ValueError:
            block(f"edits outside the repo are not allowed: {path}")
        if rel.parts and rel.parts[0] in PROTECTED_DIRS:
            block(f"{rel.parts[0]}/ is the harness itself; agents cannot change their own checks")


if __name__ == "__main__":
    main()
