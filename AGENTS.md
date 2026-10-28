# AGENTS.md

## Visual changes: send the screenshot to Telegram

When the user asks for a **visual/UI change** (new screen, layout, colours,
copy, icons, anything that shows on screen), finish the change and then push a
capture of the running app to Telegram so it can be reviewed on the phone.

```sh
scripts/telegram.sh --screen <screen> --caption "<what changed>"
```

- `--screen` accepts `home | explore | superstar | settings | detail`
  (the routes in `src/presentation/navigation/types.ts`).
- Omit `--screen` when the change is visible on the currently open screen, or
  use `--file <png>` to send an image that already exists.
- The script seeds the screen, captures the booted iOS simulator, OCR-verifies
  the expected text and uploads it to the bot. It restores `App.tsx` afterwards.
- Use `--dry-run` to capture and verify without sending; use `--out <png>` to
  also keep the image locally.
- Credentials live in `~/.config/dota2app/telegram.env` (never commit the
  token). See [docs/telegram.md](./docs/telegram.md).

If the simulator is not booted or the app is not installed, say so instead of
guessing; `yarn ios` installs it.

## How agents work here (docs/agent-design.md)

1. **DRY**: what you do by hand twice becomes a script or a flag on an
   existing one, with its why in the header. `harness/retro.py` lists the
   repeated ad-hoc commands.
2. **KISS**: a script decides before a model; the lightest check that covers
   the change before the full one.
3. **SoC / SRP**: one agent, one job. Whoever does the work doesn't judge it
   (judges are read-only: `harness/agents.py check` enforces it).
4. **YAGNI**: no agent, rule or check without a measured failure behind it.
   Every rule carries its why and when it doesn't apply.
5. **You pick how to verify; the full gate decides when you're done.**

## Checks before finishing a change

While iterating, pick the lightest level that covers your change:

```sh
harness/gate.sh --scope     # what the diff touches and which level it calls for
harness/gate.sh --changed   # quick: lint + related tests, types and architecture in full
```

Before finishing, always the full gate:

```sh
harness/gate.sh           # types, lint, tests, architecture, agents, secret scan
```

It runs `npx tsc --noEmit`, `npx eslint . --ext .ts,.tsx`, `npx jest`,
`harness/check_architecture.py` (Clean Architecture dependency rule) and a
secret scan. The Stop hook runs it for you; CI runs it on every PR.

## Agent pipeline

Feature and UI requests go through `/ship <request>` (planner → implementer →
test-writer → gate → reviewer → visual-qa → Telegram). Unattended:
`harness/run.py "<request>"` (add `--backend opencode` for local models,
`--backend hybrid` for a route per agent, see docs/hybrid.md);
from the phone: `harness/bot.py`. See
[docs/agentic-harness.md](./docs/agentic-harness.md).

## Changing an agent

`.claude/agents/*.md` is the only definition. After editing or adding one:
`harness/agents.py sync` (regenerates `.opencode/`), add or update its cases in
`harness/evals/agents/<name>.json`, run `harness/eval.py agents --agent <name>`
and `harness/eval.py compare`. The gate fails if an agent has no eval cases or
the opencode copies are stale. See [docs/evals.md](./docs/evals.md).

`yarn` is not on the PATH in this environment; use `npx` for the binaries in
`node_modules/.bin`.

## Screenshots for the README

`scripts/screenshots.sh` regenerates every image in `screenshots/`. Run it when
the UI changes so the README stays accurate (see `docs/screenshots.md`).
