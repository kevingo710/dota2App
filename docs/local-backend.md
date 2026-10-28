# Local backend: opencode + Ollama + Qwen

The whole agent system also runs with no cloud and no API key: the same
agents, guardrails, gate, evals and Telegram delivery, on models running on
the Mac.

```sh
harness/local/setup.sh                                 # pull models, create agent-sized variants
harness/run.py --backend opencode "make the hero name on Superstar gold"
harness/eval.py agents --backend opencode
harness/local/guardrails_test.py                       # prove the guardrails hold locally
```

## What is shared, what differs

| | Claude backend | Local backend |
| --- | --- | --- |
| Agent definitions | `.claude/agents/*.md` | generated `.opencode/agents/*.md` (`harness/agents.py sync`) |
| Models | per agent frontmatter (Opus / Sonnet) | `harness/backends.json`: `qwen3-agent` for text agents, `gemma4-agent` (vision) for visual-qa |
| Orchestration | the `/ship` skill: Claude delegates to its subagents | `harness/pipeline.py`: **code** runs each stage |
| Guardrails | `.claude/hooks/*.py` via Claude Code hooks | **the same scripts** via `.opencode/plugins/harness-guard.js` |
| Permissions | allowlist in `.claude/settings.json` | the same allowlist, rendered into each agent's `permission:` |
| Gate, OCR, Telegram, evals | `harness/gate.sh`, `scripts/telegram.sh`, `harness/eval.py` | identical |

### Why code orchestrates on the small model

An 8B model can play one role well when the input is narrow and the output is
a fixed JSON block. What it does badly is coordinating a multi-stage process:
it skips the review, invents a stage, or loses the plan halfway. So for local
models `harness/pipeline.py` is the orchestrator: planner, build agents, gate,
then the check agents, with the exact failure output fed back to the
implementer. The stage list is data (`harness/pipeline.json`), shared with
the `/ship` skill.

### Why per-agent permissions

Found while building this: opencode applies agent-level permissions over the
global ones in `opencode.json`, so a global `bash: {"*": "deny"}` didn't stop
an agent from running `git push` (it was a no-op, nothing was pushed).
The fix renders the allowlist into every generated agent, and
`harness/local/guardrails_test.py` stops a regression from going unnoticed:

```
PASS  'echo not-in-allowlist'            blocked by permission deny (*)
PASS  'git status --short --no-verify'   blocked by guard.py plugin
PASS  'git status --short'               ran (control)
```

## Models

`harness/local/*.Modelfile` make the setup reproducible:

- **qwen3-agent** = `qwen3:8b` with `num_ctx 65536`. opencode's system prompt
  alone is around 11k tokens, and with Ollama's default context the model
  silently loses the tool definitions.
- **gemma4-agent** = `gemma4:12b` (vision + tools) with `num_ctx 32768`, for
  visual-qa, which has to look at screenshots.

To try another model for one role without touching the config, pass a route:
`harness/eval.py agents --backend opencode --agent reviewer --route
reviewer=ollama/gpt-oss-agent:latest`, then `harness/eval.py matrix`. Mixing
local and Claude per agent is the `hybrid` backend: [hybrid.md](./hybrid.md).

## Gotchas

- Ollama serves one model at a time on most Macs. Another workload holding the
  GPU (for example another app using `gpt-oss`) queues every agent call behind
  it; `harness/preflight.sh --backend opencode` warns about it.
- Local runs are slower than the cloud (minutes per stage on an 8B model) and
  cost $0. The evals record both, so the trade-off is a number rather than an
  opinion.
