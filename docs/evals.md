# Evals

How the agent team is measured, and how you see what a change to the roster
actually did.

```sh
harness/evals/selftest.py                      # test the eval harness itself (no model, seconds)
harness/eval.py agents                         # every agent alone, Claude backend
harness/eval.py agents --backend opencode      # same cases, local qwen/gemma
harness/eval.py agents --agent reviewer --repeat 3
harness/eval.py system                         # full harness/run.py runs
harness/eval.py compare                        # committed baseline vs latest run
harness/eval.py baseline                       # promote the latest run to baseline
harness/eval.py history                        # every run, roster fingerprint, pass rate, cost
harness/eval.py matrix                         # agent x model across all runs -> hybrid routes
```

## Two levels

| level | what runs | what it tells you |
| --- | --- | --- |
| **agents** | each agent alone, with a fixed input, in a throw-away copy of the repo | whether this agent does its one job: unit tests for prompts and models |
| **system** | `harness/run.py` end to end on `harness/evals/system.json` | whether the team delivers: pass rate, fix iterations, turns, cost |

Agent-level cases live in `harness/evals/agents/<agent>.json`. Each case has a
prompt, optional `setup` edits (for example a seeded bug for the reviewer) and a
list of graders. Every case runs in a sandbox: a snapshot of your current
working tree, uncommitted work included and gitignored secrets excluded,
committed so that the agent's diff starts from zero.

## Graders are deterministic

No model grades another model. `harness/evals/graders.py`:

| grader | checks |
| --- | --- |
| `json_keys`, `json_equals`, `json_contains`, `json_subset`, `json_regex`, `json_len_gte/lte` | the agent's output contract (its final JSON block) |
| `unchanged` | read-only agents (planner, reviewer, visual-qa) left the tree as they found it |
| `changed_include`, `changed_within`, `diff_regex` | the diff touches the right files, only those, with the right content (e.g. `colors.gold`, and no hex literal) |
| `gate`, `tests_pass` | the change passes `harness/gate.sh` / Jest |
| `mutation_killed` | **mutation testing**: the production code is broken on purpose and the agent's new tests must fail. A test that cannot catch the bug it is about scores zero. |

A case **passes** only if every grader passes. The **score** is the fraction of
graders passed, which helps with small local models that get the format right
but not the content.

## What each agent is tested on

| agent | cases | what they cover |
| --- | --- | --- |
| planner | 4 | correct screens/layers/files, reusing the existing entity instead of touching domain, a non-visual task, an ambiguous request (it must commit and record the alternative) |
| implementer | 3 | scope (`changed_within`), a theme token rather than a hex literal, no fetching from presentation |
| test-writer | 2 | both with mutation testing |
| reviewer | 4 | seeded defects (axios in a screen, hex + `console.log`, scope creep) and a **clean diff it must approve**: a reviewer that blocks everything is as useless as one that blocks nothing |
| visual-qa | 3 | fixture screenshots: a match, a missing row, the wrong screen |

## Tracking roster changes

Every result stores the **roster fingerprint** (`harness/agents.py roster`):
a hash of each agent (prompt, tools, model), plus the `/ship` skill, the hooks
and `harness/pipeline.json`. `compare` puts that next to the numbers:

```
## Roster
+ security-auditor added (opus, 3 cases)
~ reviewer: prompt/config changed
~ pipeline changed

## Per agent
| agent | pass | Δ pass | score Δ | sec Δ | tokens Δ | $ Δ |
| reviewer | 75% | -25% | -0.08 | +4 | +1200 | +0.03 |
| security-auditor | 100% | new | new | new | new | new |

## Cases that changed
▼ reviewer/clean-change-passes: 100% → 0%
+ security-auditor/hardcoded-token: new case, 100%
```

`--fail-on-regression` exits 1 when any case's pass rate went down, so
`compare` can act as a gate before a prompt change is merged.

### Adding an agent

1. Write `.claude/agents/<name>.md`. It's the only definition.
2. `harness/agents.py sync` generates the opencode copy. `harness/gate.sh` fails
   until the copies are in sync **and** `harness/evals/agents/<name>.json` has
   at least one case: an agent nobody measures doesn't get merged.
3. If it's a check (it returns a `verdict`), add it to `checks` in
   `harness/pipeline.json`. Both orchestrators and `run.py`'s verification read
   that file, with no code change.
4. `harness/eval.py agents --agent <name>`, then `harness/eval.py system`,
   then `harness/eval.py compare` to see what it bought (pass rate, caught
   defects) and what it cost (seconds, tokens, $).
5. Happy with it? `harness/eval.py baseline` and commit the baseline.

Baselines live in `harness/evals/baselines/<kind>-<backend>.json` and are
committed. Run history lives in `.harness/evals/` and stays local.

## Comparing backends

`compare` doesn't require both results to come from the same backend:

```sh
harness/eval.py compare harness/evals/baselines/agents-claude.json \
                        harness/evals/baselines/agents-opencode.json
```

shows, case by case, where an 8B local model stays at the level of the cloud
and where it doesn't.

## Current results (baselines, 2026-10-28, 1 run per case)

| agent | Claude (Opus/Sonnet) | local (qwen3 8B / gemma4 12B) |
| --- | --- | --- |
| planner | 4/4 | 3/4: invents test paths (`use_cases/get_heroes_use_case.test.ts`) |
| implementer | 3/3 | 2/3: type error in the hero counter |
| test-writer | 2/2 (both mutants killed) | 0/2: writes Vitest (`vi`) instead of Jest, tests don't run |
| reviewer | 4/4 | 2/4: **approves scope creep and a `console.log`** |
| visual-qa | 3/3 | 2/3: no JSON in one answer |
| **total** | **16/16 · 42 s/case · $1.72** | **9/16 · 164 s/case · $0** |

Reading it: locally, the **reviewer is the weak link**. It lets through
defects the Claude reviewer blocks, which makes the deterministic gate and the
harness's re-verification even more important on that backend. The next
experiments are clear: a bigger local model just for the reviewer
(`harness/backends.json`), or a more explicit checklist in its prompt, measured
with `compare`.

Debugging these evals turned up two bugs in the harness itself, not in the
agents. On macOS `/var` vs `/private/var` made opencode ask for
`external_directory` permission (an unattended run would hang until the
timeout), and an empty final answer was counted as an error. That's why each
failure is labelled **`infra`** (environment or harness) or **`model`**
(agent): infra failures are fixed and rerun, and they never count as an
agent regression.

Model choice per agent (which local models are worth it, which Claude tier
each role needs, and the hybrid that comes out of it) is in
[hybrid.md](./hybrid.md).

## Limits

- System runs are `--no-visual`: Metro serves the real checkout, not the
  sandbox. visual-qa is measured at the agent level with fixture screenshots.
- One run per case by default. LLMs are not deterministic, so use
  `--repeat 3` before trusting a 1-case flip.
- Hooks may not fire in sandboxes on the Claude backend (untrusted directory).
  Agent evals measure the prompt and the model; the guardrails have their own
  tests (`harness/local/guardrails_test.py`, `harness/evals/selftest.py`).
