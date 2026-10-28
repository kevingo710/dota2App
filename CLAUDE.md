@AGENTS.md

## Agent team

For feature or UI requests, use `/ship <request>` (`.claude/skills/ship`):
planner → implementer → test-writer → `harness/gate.sh` → reviewer →
visual-qa → Telegram. Subagents live in `.claude/agents/`; how the pieces fit
is in [docs/agentic-harness.md](./docs/agentic-harness.md).

Hooks in `.claude/settings.json` lint every edit, block credential access and
keep you from stopping while the gate is red. If a hook blocks you, fix the
cause; do not work around it.
