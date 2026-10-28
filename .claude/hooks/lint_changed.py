#!/usr/bin/env python3
"""PostToolUse: lint every TS/TSX file right after the agent writes it.

Feedback in the same turn is far cheaper than discovering 20 lint errors at
the gate. Also re-runs the architecture check when a src/ file changed, so a
forbidden import is caught on the edit that introduced it.

Exit 2 sends stderr back to the model (the edit is already applied).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parents[2]))


def main() -> None:
    event = json.load(sys.stdin)
    path = (event.get("tool_input") or {}).get("file_path", "")
    if not path.endswith((".ts", ".tsx")):
        return
    file = Path(path).resolve()
    try:
        rel = file.relative_to(ROOT)
    except ValueError:
        return
    if rel.parts[0] in {"node_modules", "ios", "android"} or not file.exists():
        return

    problems = []
    lint = subprocess.run(
        ["npx", "eslint", "--format", "unix", str(rel)],
        cwd=ROOT, capture_output=True, text=True,
    )
    if lint.returncode != 0:
        problems.append(lint.stdout.strip() or lint.stderr.strip())

    if rel.parts[0] == "src":
        arch = subprocess.run(
            [sys.executable, "harness/check_architecture.py"],
            cwd=ROOT, capture_output=True, text=True,
        )
        if arch.returncode != 0:
            problems.append(arch.stdout.strip())

    if problems:
        print(f"{rel} has problems, fix them now:\n" + "\n".join(problems), file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
