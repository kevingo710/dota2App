# Hybrid backend: a model per agent, chosen by the evals

Not every agent needs the same model. A planner's mistake becomes the
contract that every later stage follows. An implementer's mistake gets caught
by the gate a few seconds later. The hybrid backend gives each agent its own
**route**, and the routes come from measurements, not intuition.

```sh
harness/run.py --backend hybrid "make the hero name on Superstar gold"
harness/eval.py matrix                     # agent x model table + suggested routes
harness/eval.py matrix --prefer speed      # same, fastest instead of cheapest
harness/eval.py matrix --write             # store the picks in harness/backends.json
```

From the phone: `/hybrid <request>`.

## Routes

| route | runs on |
| --- | --- |
| `claude` | Claude Code, model from the agent's frontmatter |
| `claude:<model>` | Claude Code with `--model` (`opus`, `sonnet`, `haiku`) |
| `opencode` | opencode + Ollama, model from the generated `.opencode/agents/<name>.md` |
| `<provider>/<model>` | opencode with `-m`, e.g. `ollama/qwen3-14b-agent:latest` |

`harness/backends.json` → `hybrid.routes` is the table; an unlisted agent takes
`hybrid.default`. Any backend accepts `--route agent=<route>` to override one
entry, which is how a candidate model is measured for one role:

```sh
harness/eval.py agents --backend opencode --agent reviewer \
  --route reviewer=ollama/gpt-oss-agent:latest
```

The prompt, tools, permissions and hooks are the same on every route.
Only the model and the runtime change. The route is part of the roster
fingerprint, so `compare` reports `reviewer: model opus→ollama/qwen3-14b-agent`
next to the change in the numbers.

## Escalation: cheap first, strong when it's stuck

A route is a first attempt, not a sentence. `hybrid.escalation` gives an
agent a stronger route for when the cheap one gets stuck:

```json
"escalation": {"implementer": "claude:haiku"},
"escalate_after": 1
```

The local implementer writes the change and gets one fix iteration with the
exact gate output. If the gate is still red, the next fix goes to Haiku with
the same prompt, the same plan and the same failure. `run.py`'s own retries,
which come after the pipeline's loop, go straight to escalation. The event
log records the route of every invocation, and the roster fingerprint
includes the escalation, so changing it shows up in `compare`.

This came out of the system evals, not the agent evals: qwen3 14B passes the
three single-file implementer cases, but on multi-file plans (a helper plus
its use in a screen) it imports modules it never created and loops on the
same `TS2307` until the retries run out, 30–60 minutes per task.

Mixed routes use the harness orchestrator (`harness/pipeline.py`). The
`/ship` skill runs every subagent inside one Claude session, so it can only
honour routes that are all Claude.

## How the pick is made

`harness/eval.py matrix` pools every agent-level eval run produced by the
agent's **current** prompt (older prompts are ignored, infra failures don't
count), per agent × model. For each agent:

1. take the best pass rate,
2. keep the routes within that agent's **tolerance** of it,
3. pick the cheapest (`--prefer cost`) or the fastest (`--prefer speed`).

The tolerance is the design decision, and it lives in `backends.json` with
its reason:

| agent | tolerance | why |
| --- | --- | --- |
| implementer | 0.34 | backed by `gate.sh`, the reviewer, the fix loop and `run.py`'s re-check: a weaker model costs a fix iteration, not a wrong result |
| visual-qa | 0.34 | backed by deterministic OCR (`--expect`) that `run.py` re-runs; vision is the second layer |
| planner, reviewer, test-writer | 0 | nothing deterministic checks them: the plan is the contract, the reviewer is the last judge, and a test that can't catch its bug still passes the gate (only the evals' mutation testing notices) |

That is the general rule: **spend model quality where no deterministic check
backs the agent up, save it where one does.**

## Local candidates (Apple M4 Pro, 24 GB)

macOS gives the GPU about two thirds of unified memory, so the ceiling is
around 16 GB of weights plus KV cache:

| model | size | fits | notes |
| --- | --- | --- | --- |
| `qwen3:8b` (`qwen3-agent`, 64k ctx) | 5 GB | yes | the original local default |
| `qwen3:14b` (`qwen3-14b-agent`, 32k ctx) | 9 GB | yes | largest dense Qwen3 that fits with context |
| `gpt-oss:20b` (`gpt-oss-agent`, 32k ctx) | 13 GB | yes, 100% GPU | MoE, ~3.6B active: fast |
| `gemma4:12b` (`gemma4-agent`, 32k ctx) | 8 GB | yes | the only local model here with vision |
| `qwen3-coder:30b`, Qwen3.6 35B-A3B | 18–20 GB | no | need 32 GB or more |
| Devstral Small 2 (24B dense) | ~15 GB | tight | no room for 32k context next to it |

`harness/local/setup.sh --candidates` pulls and configures the ones that fit.

## Results (2026-10-28, agent level, 1 run per case unless noted)

| agent | best local | pass | Claude tier needed | pass | $/case |
| --- | --- | --- | --- | --- | --- |
| planner | qwen3 8B | 75% | **sonnet** (opus not needed) | 100% | 0.059 |
| implementer | **qwen3 14B** | 100% (378 s/case) | haiku | 100% | 0.003 |
| test-writer | gpt-oss 20B | 50% | **haiku** | 100% | 0.004 |
| reviewer | qwen3 14B | 83% (12 runs) | **sonnet** | 100% | 0.043 |
| visual-qa | gemma4 12B | 67% | haiku | 100% | 0.002 |

What the numbers say:

- **Opus isn't needed anywhere in this pipeline.** Sonnet for planner and
  reviewer, Haiku for the rest: 16/16 at $0.43 instead of $1.72 (−75%).
- **Repeat before trusting a pick.** qwen3 14B scored 4/4 as reviewer on the
  first run and `matrix` picked it. With `--repeat 2` it let `axios` in a
  screen through twice: 10/12. The reviewer has zero tolerance, so the pick
  moved to Sonnet. A one-run 100% on four cases is not evidence.
- **Bigger isn't uniformly better locally.** qwen3 14B fixes the scope
  creep and `console.log` that the 8B reviewer approved, and is a 3/3
  implementer, but still writes Vitest for the test-writer. gpt-oss 20B is
  3× faster but is the worst implementer (wrong copy, type error) and
  misses `axios` in a screen as a reviewer.
- **The test-writer is the role no local model can do yet**: every one
  imports `vitest` or writes no test at all. It's the cheapest role to send
  to the cloud (Haiku, $0.004/case).
- **The planner also stays in the cloud:** every local model invents paths
  (`src/__tests__/...`, `src/data/useCases/...`) that the plan then binds
  everyone to.

Suggested routes (`matrix --write`, cost preference), now in `backends.json`:

```json
{
  "planner": "claude:sonnet",
  "test-writer": "claude:haiku",
  "reviewer": "claude:sonnet",
  "implementer": "ollama/qwen3-14b-agent:latest",
  "visual-qa": "opencode"
}
```

The judges (plan, tests, review) run on Claude. The work with the most
tokens (implementing, with its fix loop) and the screenshots run on the
Mac, backed by the gate and OCR. With `--prefer speed` the same
data picks Haiku/Sonnet for everything, which is the right choice when wall
time matters more than keeping code local.

## Results end to end (`harness/eval.py system`, 4 tasks, `--no-visual`)

| | Claude (`/ship`, Opus/Sonnet) | hybrid with escalation |
| --- | --- | --- |
| tasks passed | 4/4 | 4/4 |
| cost | $3.71 | **$0.49 (−87%)** |
| time per task | 2.4 min | 23 min |
| escalations to Haiku | – | 1 (home-count, after one failed local fix) |

Per task on hybrid: `settings-row` 12 min, `home-count` 51 min (the local
implementer looped until escalation, then Haiku fixed it in 49 s),
`mapper-test` 24 min, `guardrail-layers` 4 min (refused safely: the plan
kept `axios` out of the screen and nothing forbidden landed).

Reading it: **hybrid gets the same result at an eighth of the cost and
keeps the code on the Mac, but it's ten times slower.** Use hybrid for
unattended jobs (the Telegram bot, overnight runs); use `--backend claude`
when you're waiting for the answer. Single run per task: treat the times as
an order of magnitude, not a benchmark.

## What the system evals caught that the agent evals didn't

Running the whole system turned up four problems that no agent-level case
exposed:

1. **A harness bug: every failed run crashed.** `run.py` logged the failure
   with `event("failed", stage=...)`, which collides with `event()`'s own
   `stage` argument. A failed run therefore never wrote `summary.json` or
   sent its report to Telegram. It had never been seen because every earlier
   run had passed. Fixed, with a regression test in `harness/evals/selftest.py`.
2. **Two grader false negatives.** `home-count` required the literal
   "heroes" in `HomeScreen.tsx`, while Claude had put the plural in a pure
   `formatHeroCount()` with its own test, which is better design.
   `guardrail-layers` (an adversarial request for `axios` in a screen) required
   the run to *pass*, while a safe refusal is just as correct. The graders now
   check behaviour (`safe_failure`, no `axios`/`api.opendota.com` in the
   screen).
3. **The local implementer doesn't scale to multi-file plans.** That is the
   reason for escalation (above).
4. **System runs threw away their evidence.** The sandbox was deleted with the
   plan and agent logs in it. They're now kept in `.harness/evals/runs/`, and each
   row stores its diff stat.
