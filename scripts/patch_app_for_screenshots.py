#!/usr/bin/env python3
"""Temporarily patch App.tsx so scripts/screenshots.sh can start on any screen.

Injected code is marked with a comment so the patch is idempotent; the shell
script restores the original file from a backup when it exits.

Usage: patch_app_for_screenshots.py <home|explore|spotlight|settings|detail>
"""

import re
import sys
from pathlib import Path

MARKER = "// screenshots-driver (injected by scripts/screenshots.sh, never commit)"
VALID_ROUTES = {"home", "explore", "spotlight", "settings", "detail"}

DRIVER_TEMPLATE = """
{marker}
const SHOT_ROUTE = '{route}';
const SHOT_TABS = ['Home', 'Explore', 'Spotlight', 'Settings'];

const shotState = () => {{
  if (SHOT_ROUTE === 'detail') {{
    return {{
      index: 1,
      routes: [{{name: 'Tabs'}}, {{name: 'HeroDetail', params: {{heroId: {hero_id}}}}}],
    }};
  }}
  const tabName = SHOT_ROUTE.charAt(0).toUpperCase() + SHOT_ROUTE.slice(1);
  const index = SHOT_TABS.indexOf(tabName);
  if (index < 0) {{
    return undefined;
  }}
  return {{
    routes: [
      {{name: 'Tabs', state: {{index, routes: SHOT_TABS.map(name => ({{name}}))}}}},
    ],
  }};
}};
"""


def fail(message: str) -> None:
    sys.exit(f"patch_app_for_screenshots: {message}")


def replace_once(source: str, old: str, new: str, what: str) -> str:
    count = source.count(old)
    if count != 1:
        fail(
            f"expected exactly 1 occurrence of {what!r} in App.tsx, found {count}. "
            "Update the anchors in scripts/patch_app_for_screenshots.py "
            "(see docs/screenshots.md)."
        )
    return source.replace(old, new)


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in VALID_ROUTES:
        fail(f"usage: patch_app_for_screenshots.py <{'|'.join(sorted(VALID_ROUTES))}>")
    route = sys.argv[1]

    app_path = Path(__file__).resolve().parent.parent / "App.tsx"
    source = app_path.read_text()

    if MARKER not in source:
        driver = DRIVER_TEMPLATE.format(marker=MARKER, route=route, hero_id=8)
        source = replace_once(
            source,
            "import React from 'react';\n",
            "import React from 'react';\nimport {LogBox} from 'react-native';\n",
            "first import line",
        )
        last_import = source.rfind("\nimport ")
        line_end = source.index("\n", last_import + 1)
        source = source[: line_end + 1] + driver + "\n" + source[line_end + 1 :]
        source = replace_once(
            source,
            "<NavigationContainer theme={MyTheme}>",
            "<NavigationContainer\n"
            "          key={SHOT_ROUTE}\n"
            "          theme={MyTheme}\n"
            "          initialState={shotState()}>",
            "<NavigationContainer> opening tag",
        )
        source = replace_once(
            source,
            "const App = () => {\n  return (",
            "const App = () => {\n  LogBox.ignoreAllLogs();\n  return (",
            "App component body",
        )
    else:
        source, count = re.subn(
            r"const SHOT_ROUTE = '[a-z]+';",
            f"const SHOT_ROUTE = '{route}';",
            source,
        )
        if count != 1:
            fail(f"found {count} SHOT_ROUTE declarations, expected 1")

    app_path.write_text(source)


if __name__ == "__main__":
    main()
