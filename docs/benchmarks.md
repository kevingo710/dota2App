# Benchmarks: Claude vs local models vs hybrid, per agent and end to end

Measured on 2026-10-27/28 with this repo's own eval harness
(`harness/eval.py`). These are the numbers behind the routing decisions in
[hybrid.md](./hybrid.md), written up to be quoted. The raw results, with
paths redacted, are in `harness/evals/results/2026-10-28/`:

```sh
harness/eval.py matrix harness/evals/results/2026-10-28/*.json
harness/eval.py compare harness/evals/baselines/agents-claude.json \
                        harness/evals/baselines/agents-opencode.json
```

## Setup

| | |
| --- | --- |
| App | React Native 0.87, Clean Architecture, 5 screens, Jest + ESLint + tsc |
| Agents | planner, implementer, test-writer, reviewer, visual-qa (`.claude/agents/`) |
| Cloud | Claude Code CLI; Opus / Sonnet / Haiku through per-agent routes |
| Local | opencode 1.19 + Ollama 0.40 on an Apple M4 Pro, 24 GB unified memory |
| Local models | qwen3 8B (64k ctx), qwen3 14B (32k), gpt-oss 20B (32k), gemma4 12B vision (32k) |
| Grading | deterministic only: JSON contracts, diff scope, the quality gate, **mutation testing**; no model grades another |

**Agent level**: 16–17 cases, each agent alone in a throw-away copy of the
repo. **System level**: 4 tasks run end to end by `harness/run.py`
(plan → code → tests → gate → review → commit), including an adversarial one
that asks for a layer violation.

## Headline numbers

| | pass | cost | time |
| --- | --- | --- | --- |
| **Agents, Claude Opus/Sonnet** | 16/16 | $1.72 | 42 s/case |
| **Agents, Claude Sonnet/Haiku** | 16/16 | **$0.43 (−75%)** | 35 s/case |
| **Agents, local qwen3 8B + gemma4** | 9/16 | $0 | 164 s/case |
| **System, Claude** (`/ship`) | 4/4 | $3.71 | 2.4 min/task |
| **System, hybrid + escalation** | 4/4 | **$0.49 (−87%)** | 23 min/task |

## Per agent × model

Pooled over every run of each agent's current prompt (`harness/eval.py matrix`).
◀ = the route the hybrid uses.

| agent | model | runs | pass | s/case | $/case |
| --- | --- | --- | --- | --- | --- |
| planner | Opus | 5 | 100% | 27 | 0.153 |
| planner | **Sonnet** ◀ | 5 | 100% | 18 | 0.059 |
| implementer | Opus (session default) | 3 | 100% | 28 | 0.132 |
| implementer | Haiku (escalation) | 3 | 100% | 21 | 0.004 |
| implementer | **qwen3 14B** ◀ | 3 | 67% | 273 | 0 |
| test-writer | Sonnet | 2 | 100% | 27 | 0.053 |
| test-writer | **Haiku** ◀ | 2 | 100% | 26 | 0.004 |
| test-writer | gpt-oss 20B | 2 | 50% | 84 | 0 |
| test-writer | qwen3 8B / 14B | 2 | 0% | 122–162 | 0 |
| reviewer | Opus | 4 | 100% | 102 | 0.127 |
| reviewer | **Sonnet** ◀ | 4 | 100% | 93 | 0.043 |
| reviewer | qwen3 14B | 12 | 83% | 116 | 0 |
| reviewer | gpt-oss 20B | 4 | 75% | 34 | 0 |
| reviewer | qwen3 8B | 4 | 50% | 82 | 0 |
| visual-qa | Haiku | 3 | 100% | 6 | 0.002 |
| visual-qa | **gemma4 12B** ◀ | 3 | 67% | 90 | 0 |

## Seven findings

1. **Opus wasn't needed for any role.** Sonnet plans and reviews as well, and
   Haiku implements, writes tests and checks screenshots as well, on every
   case: −75% at the agent level.
2. **A deterministic check is what lets you use a cheaper model.** The routes
   come from a rule, not from taste: an agent may take a weaker model only if a
   deterministic check backs it up (the implementer has the gate, visual-qa has
   OCR). The planner, the reviewer and the test-writer have nothing behind them,
   so they get zero tolerance.
3. **The test-writer is the role no local model can do.** Every local model
   imports `vitest` in a Jest project or writes no test. Mutation testing is
   what catches it: a test that can't kill the planted bug scores zero.
4. **One run is not evidence.** The qwen3 14B reviewer went 4/4 on the first
   run and was picked; with `--repeat 2` it let `axios` into a screen through
   twice: 10/12. The pick moved to Sonnet.
5. **Agent evals don't predict the system.** qwen3 14B is a 3/3 implementer on
   single-file cases, but on multi-file plans it imports modules it never
   created and loops on the same `TS2307` for 30–60 minutes. **Escalation**
   (one local fix attempt, then Haiku with the exact gate output) took the
   hybrid from 2/4 to 4/4. Haiku fixed the stuck task in 49 s.
6. **The hybrid costs an eighth, but runs ten times slower.** Use it for
   unattended work (Telegram bot, overnight); stay on Claude when you're
   waiting. The code, the fixes and the screenshots stay on the Mac.
7. **Bigger local isn't uniformly better.** gpt-oss 20B is 3× faster than
   qwen3 8B and a better reviewer, but the worst implementer. Measure per
   role; a single "best model" doesn't exist.

## Bugs the evals found in the harness itself

Building the evals turned up more harness bugs than agent bugs, and every one
looked like a model failure at first:

| bug | symptom | fix |
| --- | --- | --- |
| macOS `/var` → `/private/var` | a local run hung 20 min with zero model calls: opencode asked for an "outside directory" permission nobody could answer | resolve temp paths; `external_directory: deny`, never `ask` |
| opencode agent permissions override global ones | a test agent ran a real `git push` (a no-op: nothing to push) | render the allowlist into every generated agent; `guardrails_test.py` |
| empty final answer counted as an error | implementers that end on a tool call scored as failures | only a non-zero exit with no output is an error |
| `event("failed", stage=…)` | **every failed run crashed** before writing its report, unseen because every earlier run had passed | fixed + regression test |
| two grader false negatives | a better design (a pure `formatHeroCount()` helper) and a safe refusal scored as failures | grade behaviour, not wording; `safe_failure` for adversarial tasks |
| system runs deleted their evidence | a failure couldn't be explained after the fact | keep the plan, the logs and the diff stat per run |

That's why every failure is labelled **infra** or **model**: infra failures
get fixed and rerun, and they never count against an agent.

## Limits

- Small samples: 2–5 cases per agent, 1 run per case except where noted. The
  flips we saw (finding 4) are exactly why the matrix needs `--repeat`.
- System runs are `--no-visual`: Metro serves the real checkout, not the
  sandbox; visual-qa is measured on fixture screenshots.
- The Claude system result pools reruns of two tasks after the grader fixes
  (same prompts, same roster fingerprint).
- One machine. Local times depend heavily on what else holds the GPU.
