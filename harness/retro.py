#!/usr/bin/env python3
"""Which work keeps being done by hand: candidates for a new script or flag.

    harness/retro.py                  every recorded session and run
    harness/retro.py --min-sessions 3
    harness/retro.py --json

Reads the commands recorded by .claude/hooks/record_command.py
(.harness/commands.jsonl, .harness/runs/*/, .harness/evals/runs/*/). A
command counts as **covered** when it already goes through a repo tool
(harness/, scripts/), is a check the gate wraps (npx tsc/eslint/jest) or is
a plain read (ls, cat, grep, git diff...). Everything else is **ad hoc**,
and an ad-hoc command that comes back in several sessions is reported: that
is work the agent re-derives, and pays for, every time.

Coverage (the share of commands that go through repo tools) is the number
to watch: it should go up as the harness absorbs the repeated work.
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [".harness/commands.jsonl", ".harness/runs/*/commands.jsonl",
           ".harness/evals/runs/*/commands.jsonl"]
COVERED = re.compile(
    r"^(\./)?(harness/|scripts/|python3 (harness|scripts)/|npx (tsc|eslint|jest|prettier)\b|"
    r"(ls|cat|head|tail|grep|rg|find|wc|pwd|echo|sed -n)\b|git (status|diff|log|show)\b)")


def normalize(command: str) -> str:
    """Same work, same key: drop `cd X &&`, temp paths and spacing."""
    command = re.sub(r"^\s*cd \S+\s*&&\s*", "", command)
    command = re.sub(r"/(private/)?(var/folders|tmp)/\S+", "<tmp>", command)
    return re.sub(r"\s+", " ", command).strip()


def load(root: Path = ROOT) -> list[dict]:
    rows = []
    for pattern in SOURCES:
        for path in sorted(root.glob(pattern)):
            # A run directory is one session; the interactive log carries ids.
            default_session = path.parent.name if path.parent.name != ".harness" else "interactive"
            for line in path.read_text().splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                row["session"] = row.get("session") or default_session
                rows.append(row)
    return rows


def analyse(rows: list[dict], min_sessions: int = 2, min_count: int = 3) -> dict:
    groups: dict[str, dict] = defaultdict(lambda: {"count": 0, "sessions": set()})
    covered = 0
    for row in rows:
        key = normalize(row["command"])
        if COVERED.match(key):
            covered += 1
            continue
        groups[key]["count"] += 1
        groups[key]["sessions"].add(row["session"])
    candidates = sorted(
        ({"command": k, "count": g["count"], "sessions": len(g["sessions"])}
         for k, g in groups.items()
         if len(g["sessions"]) >= min_sessions or g["count"] >= min_count),
        key=lambda c: (-c["sessions"], -c["count"], c["command"]))
    total = len(rows)
    return {"commands": total, "covered": covered,
            "coverage": round(covered / total, 3) if total else None,
            "candidates": candidates}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--min-sessions", type=int, default=2)
    parser.add_argument("--min-count", type=int, default=3)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = analyse(load(), args.min_sessions, args.min_count)
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    if not report["commands"]:
        print("no commands recorded yet (.claude/hooks/record_command.py)")
        return 0
    print(f"{report['commands']} commands, {report['coverage']:.0%} through repo tools")
    if not report["candidates"]:
        print("no repeated ad-hoc work")
    for c in report["candidates"][:args.limit]:
        print(f"  {c['sessions']} sessions · {c['count']}×  {c['command'][:140]}")
    if report["candidates"]:
        print("\nTurn the top ones into a script under scripts/ or a flag on an existing tool, "
              "and say why in its header.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
