# Agent design principles

The software-engineering principles we already apply to code, applied to
agents, each with the rule that comes out of it and where this repo follows
it or enforces it. An agent is a component: it has inputs, an output contract,
dependencies and permissions. What changes is that it's probabilistic and
nothing type-checks it, so here **the evals play the compiler's role**.

## The short version (also in AGENTS.md)

1. **DRY** · what you do by hand twice becomes a script; one definition per thing.
2. **KISS** · the simplest tool that decides: a script before a model, the lightest check before the full one.
3. **SoC / SRP** · one agent, one job; whoever does the work does not judge it.
4. **YAGNI** · no agent, rule or check without a measured failure behind it.
5. **Freedom while iterating, code decides at the end** · the agent picks how to verify, the full gate decides "done".

## DRY: never pay for the same work twice

An agent re-derives its process every session, and you pay for it in tokens
and in supervision. The end goal of a task isn't the result: it's the result
**plus** the process captured as a tool, so the next time costs less.

| rule | in this repo |
| --- | --- |
| Repeated manual work becomes a script or a flag on an existing one | `scripts/telegram.sh` (capture + OCR + send), `harness/preflight.sh` (starts Metro), `harness/local/setup.sh` |
| Find the repetition with data, not memory | `.claude/hooks/record_command.py` records every command; `harness/retro.py` lists the ad-hoc ones that come back across sessions and the **coverage** (share of commands that go through repo tools). `run.py` puts the top candidate in the Telegram report |
| One definition per thing | `.claude/agents/` → generated `.opencode/`; `pipeline.json` read by `/ship`, `pipeline.py` and `run.py`; `scope.json` read by the planner and `scope.py`; the same `guard.py` on both backends |

Where it doesn't apply: **prompts**. An agent doesn't see the other agents'
files, so a prompt must stand on its own. Repeating a codebase rule in two
prompts is fine; removing context in the name of DRY isn't.

## KISS: the simplest thing that decides

| rule | in this repo |
| --- | --- |
| A script decides before a model does | "done" is `harness/gate.sh` + OCR, not an LLM judge; the eval graders are deterministic |
| Code orchestrates when the model can't | an 8B model doesn't coordinate stages, so `harness/pipeline.py` sequences them; with Claude the `/ship` skill does |
| The lightest check that covers the change | `harness/gate.sh --changed` while iterating, `harness/gate.sh` at the end |

## SoC / SRP: one job per agent, and the doer is not the judge

This is the principle with the most weight. It's what made the hybrid
backend possible: because each agent does one thing, each one has its own
evals and its own model ([hybrid.md](./hybrid.md)). An agent that plans,
implements and reviews can't be half sent to Haiku.

| rule | in this repo | enforced by |
| --- | --- | --- |
| Judges (planner, reviewer, visual-qa) are read-only | the planner has no Edit, visual-qa only Bash + Read | `harness/agents.py check` fails if a judge has a write tool |
| Builders can do their job | implementer and test-writer have Edit/Write | same check |
| Nobody can edit their own judges | `harness/`, `.claude/`, `scripts/` blocked in unattended runs | `.claude/hooks/guard.py` |
| If the description says "and also…", it's two agents | five agents, five contracts (plan, change, tests, review, visual) | code review |

## YAGNI: no rule without a failure behind it

When an agent designs a test suite it tends to propose the large-company
rules: MUST test every device, MUST run everything on any shared change.
Each of those rules is a past incident turned into a mandate for everyone.
Here a rule enters only with evidence:

| rule | in this repo | enforced by |
| --- | --- | --- |
| No agent without evals | an agent with no cases doesn't pass the gate | `agents.py check` |
| No agent outside the pipeline | if no stage uses it, it gets deleted | `agents.py check` |
| Every hard rule comes from a real incident | the `git push` that opencode ran → per-agent permissions; Metro down → preflight starts it | `guardrails_test.py` |
| Every config decision carries its why | `tolerance_why`, `escalation_why` in `backends.json`; every `shared` entry in `scope.json` has a `why` | review |
| A model only gets added if it earns its place | Opus was replaced: Sonnet/Haiku score 16/16 just the same | `harness/eval.py matrix` |

A rule with its reason lets the agent judge whether it applies. A bare
MUST makes it obey even when it's overkill.

## Freedom while iterating, code decides at the end

Agents are good at picking a tool. So give them **options, not mandates**,
for *how* to verify:

```sh
harness/gate.sh --scope     # what this diff touches: screens, shared code, quick|full
harness/gate.sh --changed   # quick: lint + related Jest tests, types and architecture in full
harness/gate.sh             # full
scripts/telegram.sh --screen settings --dry-run   # the one journey that changed
```

The planner chooses `verify.level` from `harness/scope.json` (shared code →
`full`, with the file and the reason), the implementer iterates at that level,
and `gate.sh --changed` warns if the diff touched shared code.

What the agent **doesn't** choose is whether it's done. The evals show
why: an 8B reviewer approved a `console.log` and an out-of-scope change, and
a 14B one let `axios` into a screen through twice in a row. So:

- **"Done" is the full gate**, enforced by the Stop hook and re-run by
  `harness/run.py`, whatever level the agent used along the way.
- **Freedom scales with the model.** Opus/Sonnet get many options; a local
  model gets few, fixed stages (the harness orchestrator).
- **The agent's decision is measured too.** Planner evals include picking
  `quick` for a single-screen change and `full` for a theme token. Each run
  report includes `scope: full (planned quick ⚠)` when the planner
  underestimated the diff.

> In this repo the full gate takes about 3 s, so `--changed` saves
> little today. The rule matters as the suite grows. The mechanism is
> already in place, and the report shows when the planner gets it wrong.

## The rest of SOLID

| principle | in agents | in this repo |
| --- | --- | --- |
| **OCP** | add an agent without touching code | a `.md` + an entry in `pipeline.json` + its evals |
| **LSP** | any model that honours the contract is interchangeable | each agent's output JSON; the graders check the contract, not the model |
| **ISP** | each agent with only the tools its role needs | tools and permissions per agent, rendered for opencode |
| **DIP** | depend on a contract, not on a model | `Backend` / `Router`: the pipeline doesn't know whether Claude or qwen is running |

## Two that are specific to agents

- **Fail fast with the exact error.** The agent gets the raw compiler,
  test or OCR output, not a summary: `gate.json` → the fix loop.
- **Least privilege, and never over your own judges.** Minimal permissions
  per agent; no access to `harness/`, `.claude/` or `scripts/` in
  unattended runs.

## Where the analogy breaks

- **There's no compiler for prompts.** Without evals these principles
  are just good intentions; with evals (`harness/eval.py`) they're
  measurable, and with `agents.py check` some are mandatory.
- **Agents are probabilistic.** The same agent can fail a case it passed
  before (the 14B reviewer: 4/4, then 10/12). That's why SRP plus a
  deterministic judge matters more here than in ordinary code.
