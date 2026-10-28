#!/usr/bin/env python3
"""PostToolUse (Bash): remember every command an agent ran, so that
harness/retro.py can find the work that is being done by hand again and
again and should become a script (DRY for agents).

Writes one JSON line per command to $HARNESS_RUN_DIR/commands.jsonl in
unattended runs, else to .harness/commands.jsonl (gitignored). Anything that
looks like a token or key is redacted before it touches disk. Never blocks.
"""

import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parents[2]))
SECRETS = re.compile(r"[0-9]{8,10}:[A-Za-z0-9_-]{35}|sk-[A-Za-z0-9_-]{20,}|"
                     r"(token|key|secret|password)=\S+", re.I)


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    command = (event.get("tool_input") or {}).get("command")
    if event.get("tool_name", "Bash") != "Bash" or not command:
        return
    out = Path(os.environ.get("HARNESS_RUN_DIR") or ROOT / ".harness") / "commands.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a") as f:
        f.write(json.dumps({"t": round(time.time()), "session": event.get("session_id"),
                            "command": SECRETS.sub("<redacted>", command)}) + "\n")


if __name__ == "__main__":
    try:
        main()
    except OSError:
        pass  # recording is best effort; it must never fail a tool call
    sys.exit(0)
