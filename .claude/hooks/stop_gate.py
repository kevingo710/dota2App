#!/usr/bin/env python3
"""Stop hook: the agent cannot finish while the quality gate is red.

Runs harness/gate.sh when TS/TSX code differs from HEAD and that exact diff
has not passed yet (fingerprint cache, so a turn that touched nothing costs
nothing). On failure it blocks the stop and hands the gate output back to the
model, up to MAX_BLOCKS times in a row; after that it lets the agent stop and
tells the user, so a hopeless run cannot loop forever.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR", Path(__file__).resolve().parents[2]))
STATE = ROOT / ".harness" / "state"
MAX_BLOCKS = 3


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout


def fingerprint() -> str:
    diff = git("diff", "HEAD", "--", "*.ts", "*.tsx")
    untracked = git("ls-files", "--others", "--exclude-standard", "--", "*.ts", "*.tsx").split()
    digest = hashlib.sha256(diff.encode())
    for name in sorted(untracked):
        digest.update(name.encode())
        digest.update((ROOT / name).read_bytes())
    return "" if not diff and not untracked else digest.hexdigest()


def main() -> None:
    json.load(sys.stdin)
    current = fingerprint()
    if not current:
        return
    STATE.mkdir(parents=True, exist_ok=True)
    passed_file, blocks_file = STATE / "gate.pass", STATE / "gate.blocks"
    if passed_file.exists() and passed_file.read_text() == current:
        return

    gate = subprocess.run(["harness/gate.sh", "--quiet"], cwd=ROOT,
                          capture_output=True, text=True)
    if gate.returncode == 0:
        passed_file.write_text(current)
        blocks_file.unlink(missing_ok=True)
        return

    blocks = int(blocks_file.read_text()) + 1 if blocks_file.exists() else 1
    if blocks > MAX_BLOCKS:
        blocks_file.unlink(missing_ok=True)
        print(json.dumps({"systemMessage":
                          f"quality gate still failing after {MAX_BLOCKS} attempts; "
                          "stopping. Run harness/gate.sh to see why."}))
        return
    blocks_file.write_text(str(blocks))
    print(f"harness/gate.sh failed (attempt {blocks}/{MAX_BLOCKS}). "
          f"Fix these before finishing:\n{gate.stdout[-6000:]}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
