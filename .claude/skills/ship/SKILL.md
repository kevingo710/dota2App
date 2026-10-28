---
name: ship
description: End-to-end pipeline for a change to the Dota 2 app - plan, implement, test, gate, review, visual QA on the iOS simulator, then send the verified screenshots to Telegram. Use when the user asks for a feature or UI change and wants it validated and delivered ("/ship make the Superstar title gold").
argument-hint: <change request>
---

# /ship

You are the orchestrator. You do not write app code yourself; you delegate to
the subagents in `.claude/agents/` and decide, from their structured outputs
and from `harness/gate.sh`, whether the change advances. Nothing reaches
Telegram until every stage is green.

Request: $ARGUMENTS

## 0. Run directory

If the request ends with "Managed run. Run directory: <path>", this is an
unattended run from `harness/run.py`: use that directory, treat it as
`HARNESS_MANAGED=1`, and skip stage 5 when it says "Simulator available: no".
Do not probe environment variables. Otherwise create
`.harness/runs/<YYYYMMDD-HHMMSS>-<slug>/`. Every stage writes its
output there; the run directory is the audit trail of the run.

## 1. Plan → `plan.json`

Delegate to **planner** with the request. Extract its JSON block and save it as
`plan.json`. If `screens` is empty the change is not visual: skip stage 5 and
send a text summary instead of photos. Also skip stage 5 when
the run says no simulator is available.

## 2. Implement

Delegate to **implementer** with the full `plan.json`. Then, if `plan.tests`
is non-empty, delegate to **test-writer** with the plan and the list of
changed files (`git status --short`).

## 3. Gate → `gate.json`

Run `harness/gate.sh --json "$RUN_DIR/gate.json"`. On failure, go to the fix
loop with the failing checks' `output`.

## 4–5. Checks

The check agents and their order come from `harness/pipeline.json` (`checks`):
run each one that applies, save its JSON as `<artifact>.json` and treat any
`verdict` other than `pass` as a failure for the fix loop. Today that is:

### 4. Review → `review.json`

Delegate to **reviewer** with `plan.json`. Save its JSON. On `fail`, fix loop
with `blocking`.

### 5. Visual QA → `visual.json`

Delegate to **visual-qa** with `plan.json` and the run directory. Save its JSON.
On `fail`, fix loop with the failing screens' findings.

## Fix loop

At most **3** fix iterations across the whole run. Each iteration: delegate to
**implementer** with the plan plus the exact findings (not a paraphrase), then
restart from stage 3. Record each iteration in `iterations.log` (stage, reason,
one line). After the third failed iteration, stop and report failure; never
lower a check to get green.

## 6. Deliver

Write `result.json`:

```json
{"status": "pass", "summary": "<plan.summary>", "iterations": 0,
 "screens": [{"screen": "superstar", "png": "...", "caption": "..."}],
 "files": ["..."]}
```

Then:

- In a managed run, stop here. The headless harness re-runs the
  gate itself, commits and sends to Telegram; doing it twice would duplicate
  messages.
- Otherwise, for each screen send the image produced by visual QA:
  `scripts/telegram.sh --file "<png>" --caption "<caption> | gate ✅ review ✅ OCR ✅"`
  and finish with a one-paragraph summary for the user (what changed, what was
  checked, iterations used).

On failure (`status: "fail"`), outside a managed run, send a text message:
`scripts/telegram.sh --text "❌ /ship failed at <stage>: <reason>"`.

## Never

- `git push`, `git commit --no-verify`, or editing `.claude/`, `harness/` or
  `scripts/` to make a run pass.
- Sending to Telegram without `--dry-run` before stage 6.
- Reading credential files (`~/.config/dota2app/telegram.env`, `.env.local`,
  `telegram.md`): the hooks block it, and the scripts already know where they are.
