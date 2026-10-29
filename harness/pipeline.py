"""Deterministic orchestration of the agent team (the `/ship` stages in code).

Claude can orchestrate its own subagents through the /ship skill. An 8B local
model cannot do that reliably: it loses track of stages, skips the review, or
calls the wrong tool. So for small models the harness is the orchestrator and
each model only ever plays one role with one clear input and output:

    planner -> build agents -> gate -> check agents (verdict JSON)
                   ^______ exact failure output, max_fix iterations ______|

The stages come from harness/pipeline.json.

Writes the same artifacts as /ship (plan.json, gate.json, review.json,
visual.json, result.json) so harness/run.py and the evals treat both
orchestrators identically.
"""

import json
import subprocess
from pathlib import Path

from backends import AgentResult, Backend, extract_json

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "harness" / "pipeline.json"
PLAN_KEYS = {"summary", "screens", "acceptance"}


def native_build(cwd: Path, env: dict | None, event) -> str:
    """Rebuild the iOS app before captures if the diff touches native code.
    '' when the binary is current, else the build failure for the fixer."""
    from scope import changed_files, classify
    native = classify(changed_files())["native"] if cwd == ROOT else []
    if not native:
        return ""
    proc = subprocess.run(["scripts/ios_build.sh"], cwd=cwd, env=env, capture_output=True, text=True)
    event("build", ok=proc.returncode == 0, files=len(native))
    if proc.returncode == 0:
        return ""
    return "scripts/ios_build.sh (pod install + iOS build) failed:\n" + (proc.stdout + proc.stderr)[-4000:]


def load_spec() -> dict:
    """Stage order, shared by this module, the /ship skill and harness/run.py.
    Adding a check agent is a config change here, not a code change."""
    return json.loads(SPEC.read_text())


class Pipeline:
    def __init__(self, backend: Backend, run_dir: Path, cwd: Path = ROOT,
                 visual: bool = True, env: dict | None = None, on_event=print):
        self.backend, self.dir, self.cwd = backend, run_dir, cwd
        self.visual, self.env, self.event = visual, env, on_event
        self.results: list[AgentResult] = []

    # --- plumbing ------------------------------------------------------------

    def agent(self, name: str, prompt: str, escalated: bool = False) -> AgentResult:
        n = len(self.results) + 1
        route = self.backend.route(name, escalated) if hasattr(self.backend, "route") else None
        self.event(f"agent:{name}", step=n, route=route)
        kwargs = {"escalated": True} if escalated else {}
        result = self.backend.run(prompt, cwd=self.cwd, agent=name, env=self.env,
                                  log=self.dir / f"{n:02d}-{name}.log", **kwargs)
        self.results.append(result)
        self.event(f"agent:{name}:done", turns=result.turns, seconds=round(result.seconds),
                   error=result.error[:120] or None)
        return result

    def agent_json(self, name: str, prompt: str, required: set[str], artifact: str) -> dict:
        """Run an agent whose contract is a JSON block; one repair attempt."""
        result = self.agent(name, prompt)
        data = extract_json(result.text)
        if data is None or not required <= data.keys():
            result = self.agent(name, prompt + "\n\nYour previous answer did not end with a "
                                f"valid ```json block containing {sorted(required)}. "
                                "Answer again, ending with that block.")
            data = extract_json(result.text)
        if data is None or not required <= data.keys():
            raise PipelineError(name, f"no valid JSON with {sorted(required)}")
        (self.dir / f"{artifact}.json").write_text(json.dumps(data, indent=2))
        return data

    def gate(self) -> str:
        out = self.dir / "gate.json"
        proc = subprocess.run(["harness/gate.sh", "--json", str(out), "--quiet"],
                              cwd=self.cwd, capture_output=True, text=True)
        self.event("gate", ok=proc.returncode == 0)
        if proc.returncode == 0:
            return ""
        failing = [c for c in json.loads(out.read_text())["checks"] if c["status"] == "fail"]
        return "harness/gate.sh failed:\n" + "\n".join(f"## {c['name']}\n{c['output']}" for c in failing)

    # --- stages --------------------------------------------------------------

    def applies(self, step: dict, plan: dict) -> bool:
        when = step.get("when")
        return (when is None or (when == "plan.tests" and bool(plan.get("tests")))
                or (when == "visual" and self.visual and bool(plan.get("screens"))))

    def run(self, request: str) -> dict:
        spec = load_spec()
        plan = self.agent_json(spec["planner"], f"Change request: {request}", PLAN_KEYS, "plan")
        plan_text = f"```json\n{json.dumps(plan, indent=2)}\n```"
        for step in spec["build"]:
            if self.applies(step, plan):
                self.agent(step["agent"], f"{step['prompt']}\n{plan_text}")

        for iteration in range(spec["max_fix"] + 1):
            feedback = self.gate()
            for check in spec["checks"]:
                if feedback:
                    break
                if not self.applies(check, plan):
                    continue
                if check.get("when") == "visual":
                    feedback = native_build(self.cwd, self.env, self.event)
                    if feedback:
                        break
                verdict = self.agent_json(
                    check["agent"], f"Run directory: {self.dir}\n{check['prompt']}\n{plan_text}",
                    {"verdict"}, check["artifact"])
                self.event("verdict", agent=check["agent"], verdict=verdict["verdict"])
                if verdict["verdict"] != "pass":
                    findings = verdict.get("blocking") or verdict.get("screens") or verdict
                    feedback = f"{check['agent']} failed:\n{json.dumps(findings, indent=2)}"
            if not feedback:
                return self.finish(plan, "pass", iteration)
            with (self.dir / "iterations.log").open("a") as log:
                log.write(feedback[:400] + "\n---\n")
            if iteration == spec["max_fix"]:
                return self.finish(plan, "fail", iteration, feedback)
            # Hybrid: once the cheap route has had a fix iteration and the check
            # is still red, hand the fix to the escalation route.
            after = getattr(self.backend, "escalate_after", None)
            escalated = after is not None and iteration >= after
            if escalated:
                self.event("escalate", agent=spec["fixer"],
                           route=self.backend.route(spec["fixer"], True))
            self.agent(spec["fixer"], "Your change failed a check. Fix the root cause; do not "
                       f"weaken the check.\n\nPlan:\n{plan_text}\n\n{feedback}",
                       escalated=escalated)
        raise AssertionError("unreachable")

    def finish(self, plan: dict, status: str, iterations: int, reason: str = "") -> dict:
        result = {"status": status, "summary": plan.get("summary", ""),
                  "iterations": iterations, "reason": reason[:2000]}
        (self.dir / "result.json").write_text(json.dumps(result, indent=2))
        return result


class PipelineError(Exception):
    def __init__(self, stage: str, detail: str):
        super().__init__(f"{stage}: {detail}")
        self.stage, self.detail = stage, detail
