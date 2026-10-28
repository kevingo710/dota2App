#!/usr/bin/env python3
"""Enforce the Clean Architecture dependency rule on src/.

Agents are good at making a screen look right and bad at noticing that they
just imported axios into a use case. This check makes the layer boundaries a
hard gate instead of a convention.

Usage: check_architecture.py [--json]
Exit code 1 when a forbidden import is found.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

# layer -> (forbidden src/ layers, forbidden packages). `core` is the
# composition root (DI container), so it is allowed to see everything.
RULES = {
    "domain": (
        {"data", "infrastructure", "presentation"},
        {"react", "react-native", "axios", "@tanstack/react-query"},
    ),
    "data": ({"presentation"}, {"react", "react-native"}),
    "infrastructure": ({"data", "presentation"}, {"react", "react-native"}),
    "presentation": ({"data", "infrastructure"}, {"axios"}),
}

IMPORT_RE = re.compile(r"""^\s*(?:import|export)\b[^'"]*?from\s+['"]([^'"]+)['"]""", re.M)


def layer_of(path: Path) -> str | None:
    try:
        return path.relative_to(SRC).parts[0]
    except ValueError:
        return None


def package_name(spec: str) -> str:
    parts = spec.split("/")
    return "/".join(parts[:2]) if spec.startswith("@") else parts[0]


def violations():
    for file in sorted(SRC.rglob("*.ts*")):
        layer = layer_of(file)
        if layer not in RULES:
            continue
        banned_layers, banned_packages = RULES[layer]
        text = file.read_text(encoding="utf-8")
        for match in IMPORT_RE.finditer(text):
            spec = match.group(1)
            line = text.count("\n", 0, match.start()) + 1
            rel = file.relative_to(ROOT)
            if spec.startswith("."):
                target = layer_of((file.parent / spec).resolve())
                if target in banned_layers:
                    yield {"file": str(rel), "line": line, "import": spec,
                           "rule": f"{layer} must not depend on {target}"}
            elif package_name(spec) in banned_packages:
                yield {"file": str(rel), "line": line, "import": spec,
                       "rule": f"{layer} must not import {package_name(spec)}"}


def main() -> int:
    found = list(violations())
    if "--json" in sys.argv:
        print(json.dumps({"ok": not found, "violations": found}, indent=2))
    elif found:
        for v in found:
            print(f"{v['file']}:{v['line']}: {v['rule']} (import '{v['import']}')")
    else:
        print("architecture ok")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
