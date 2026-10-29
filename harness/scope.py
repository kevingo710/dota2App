#!/usr/bin/env python3
"""How much to verify while iterating: the lightest check that covers a change.

    harness/scope.py                 the working tree vs HEAD (also: harness/gate.sh --scope)
    harness/scope.py --base main     vs another ref
    harness/scope.py --files a b     planned files (before any edit)
    harness/scope.py --json

Prints the changed files, the screens they show on, the shared code they
touch (from harness/scope.json, each with its reason) and a level:

    quick   harness/gate.sh --changed   lint and Jest only on what changed
                                        (+ related tests), types and
                                        architecture in full
    full    harness/gate.sh             shared code changed: anything can break

Native files (ios/, android/, dependencies) are listed apart: screenshots of
such a change need a rebuilt binary, which harness/pipeline.py and
harness/run.py get from scripts/ios_build.sh before capturing.

This is advice for the agent while it iterates. The judgement at the end is
always the full gate (Stop hook, harness/run.py), whatever the level says.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES = json.loads((ROOT / "harness" / "scope.json").read_text())


def changed_files(base: str = "HEAD") -> list[str]:
    def git(*args: str) -> list[str]:
        out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout
        return [line for line in out.splitlines() if line]
    return sorted(set(git("diff", "--name-only", base)
                      + git("ls-files", "--others", "--exclude-standard")))


def classify(files: list[str]) -> dict:
    shared = [{"file": f, "why": rule["why"]} for f in files
              for rule in RULES["shared"] if f.startswith(rule["prefix"])]
    screens = sorted({RULES["screens"][f] for f in files if f in RULES["screens"]})
    level = "none" if not files else "full" if shared else "quick"
    # Native changes need a new binary before any screenshot (scripts/ios_build.sh).
    native = [{"file": f, "why": rule["why"]} for f in files
              for rule in RULES.get("native", []) if f.startswith(rule["prefix"])]
    return {"changed": files, "screens": screens, "shared": shared, "native": native, "level": level,
            "command": {"none": "", "quick": "harness/gate.sh --changed",
                        "full": "harness/gate.sh"}[level]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base", default="HEAD")
    parser.add_argument("--files", nargs="+", help="classify these instead of the diff")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    scope = classify(args.files or changed_files(args.base))
    if args.json:
        print(json.dumps(scope, indent=2))
        return 0
    print(f"level: {scope['level']}" + (f"  →  {scope['command']}" if scope["command"] else ""))
    print(f"changed: {len(scope['changed'])} file(s)" + "".join(f"\n  {f}" for f in scope["changed"]))
    if scope["screens"]:
        print("screens: " + ", ".join(scope["screens"]))
    for item in scope["shared"]:
        print(f"shared: {item['file']}: {item['why']}")
    for item in scope["native"]:
        print(f"native: {item['file']}: {item['why']} (rebuild: scripts/ios_build.sh)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
