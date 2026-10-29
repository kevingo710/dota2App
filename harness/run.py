#!/usr/bin/env python3
"""Headless agent run: a change request in, verified screenshots on Telegram out.

    harness/run.py "make the Superstar title gold"
    harness/run.py --no-telegram --no-visual "add a test for HeroMapper nulls"
    harness/run.py --backend opencode "..."     # fully local: opencode + Ollama

What it does, and why it is not just `claude -p`:

1. preflight      simulator, app, Metro, credentials (harness/preflight.sh)
2. isolate        clean tree required; work happens on branch agent/<run-id>
3. agents         --backend claude: claude -p "/ship <request>" (Claude orchestrates)
                  --backend opencode: harness/pipeline.py runs each agent on a
                  local Ollama model (code orchestrates). Both with
                  HARNESS_MANAGED=1, so the hooks forbid git and edits to the
                  harness itself
4. verify         the harness re-runs harness/gate.sh and re-captures every
                  planned screen with OCR (--expect the planner's strings).
                  The agent's own "it passed" is never trusted.
5. fix loop       on failure, resume the same agent session with the exact
                  failing output, up to --retries times
6. deliver        commit on the branch, send the screenshots + a report to
                  Telegram, write .harness/runs/<run-id>/report.md

Everything a run produced lives in .harness/runs/<run-id>/ (gitignored).
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from agents import snapshot
from backends import BACKENDS, AgentResult, get_backend, parse_routes
from pipeline import Pipeline, PipelineError, load_spec, native_build
from retro import analyse, load
from scope import classify

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / ".harness" / "runs"


class RunFailed(Exception):
    def __init__(self, stage: str, detail: str):
        super().__init__(f"{stage}: {detail}")
        self.stage, self.detail = stage, detail


def sh(*cmd: str, check: bool = True, env=None, timeout=None) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env, timeout=timeout)
    if check and proc.returncode != 0:
        raise RunFailed(cmd[0], (proc.stdout + proc.stderr)[-2000:])
    return proc


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40] or "run"


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


class Run:
    def __init__(self, args):
        self.args = args
        self.id = f"{dt.datetime.now():%Y%m%d-%H%M%S}-{slugify(args.request)}"
        self.dir = RUNS / self.id
        self.dir.mkdir(parents=True)
        self.branch = f"agent/{self.id}"
        self.session = None
        self.backend = get_backend(args.backend, parse_routes(args.route))
        self.env = {**os.environ, "HARNESS_MANAGED": "1", "HARNESS_RUN_DIR": str(self.dir)}
        self.usage = {"turns": 0, "tokens": 0, "cost_usd": 0.0, "agent_seconds": 0.0,
                      "invocations": 0}
        self.fix_iterations = 0
        self.started = time.time()
        self.gate = {}
        self.shots = []

    # --- plumbing ------------------------------------------------------------

    def event(self, stage: str, **data) -> None:
        line = {"t": round(time.time() - self.started, 1), "stage": stage, **data}
        with (self.dir / "events.jsonl").open("a") as f:
            f.write(json.dumps(line) + "\n")
        print(f"[{line['t']:>6}s] {stage} {json.dumps(data) if data else ''}", flush=True)

    def telegram(self, *flags: str) -> None:
        if self.args.no_telegram:
            return
        proc = sh("scripts/telegram.sh", *flags, check=False)
        if proc.returncode != 0:
            self.event("telegram-error", output=proc.stderr[-500:])

    # --- stages --------------------------------------------------------------

    def isolate(self) -> str:
        dirty = sh("git", "status", "--porcelain").stdout.strip()
        if dirty:
            raise RunFailed("isolate", "working tree is not clean; commit or stash first:\n" + dirty[:800])
        current = sh("git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        base = self.args.base or current
        if base != current:
            sh("git", "switch", base)
        sh("git", "switch", "-c", self.branch)
        self.event("isolate", base=base, branch=self.branch)
        return base

    def account(self, result: AgentResult) -> None:
        u = self.usage
        u["invocations"] += 1
        u["turns"] += result.turns
        u["tokens"] += result.tokens
        u["cost_usd"] += result.cost_usd
        u["agent_seconds"] += result.seconds

    def agent(self, prompt: str, agent: str | None = None, escalated: bool = False) -> None:
        resume = self.session if self.args.orchestrator == "skill" else None
        self.event("agent-start", backend=self.backend.name, agent=agent, resume=bool(resume),
                   route=self.backend.route(agent, escalated))
        result = self.backend.run(prompt, agent=agent, session=resume, env=self.env,
                                  escalated=escalated,
                                  log=self.dir / f"agent-{self.usage['invocations'] + 1}.log",
                                  max_turns=self.args.max_turns)
        self.account(result)
        self.session = result.session or self.session
        self.event("agent-end", turns=result.turns, seconds=round(result.seconds),
                   cost=round(result.cost_usd, 4), error=result.error[:200] or None)
        if result.error:
            raise RunFailed("agent", result.error)

    def orchestrate(self) -> None:
        if self.args.orchestrator == "skill":
            visual = "no (skip visual QA)" if self.args.no_visual else "yes"
            self.agent(f"/ship {self.args.request}\n\n"
                       f"Managed run. Run directory: {self.dir}\nSimulator available: {visual}")
            return
        pipeline = Pipeline(self.backend, self.dir, visual=not self.args.no_visual,
                            env=self.env, on_event=self.event)
        try:
            pipeline.run(self.args.request)
        except PipelineError as exc:
            raise RunFailed(exc.stage, exc.detail)
        finally:
            for result in pipeline.results:
                self.account(result)

    def fix(self, plan: dict, feedback: str) -> None:
        message = ("The harness re-ran its independent checks after your run and they "
                   f"failed. Fix the root cause, then stop.\n\n{feedback}")
        if self.args.orchestrator == "skill":
            self.agent(message)
        else:
            # The pipeline's own fix loop already ran: a harness-level fix goes
            # straight to the escalation route when there is one.
            self.agent(f"{message}\n\nPlan:\n```json\n{json.dumps(plan, indent=2)}\n```",
                       agent="implementer", escalated=True)

    def verify(self, plan: dict) -> str:
        """Independent checks. Returns '' when green, else feedback for the agent."""
        gate_json = self.dir / "gate.final.json"
        proc = sh("harness/gate.sh", "--json", str(gate_json), "--quiet", check=False)
        self.gate = read_json(gate_json)
        self.event("gate", ok=proc.returncode == 0)
        if proc.returncode != 0:
            failing = [c for c in self.gate.get("checks", []) if c["status"] == "fail"]
            return "harness/gate.sh failed:\n" + "\n".join(
                f"## {c['name']}\n{c['output']}" for c in failing)

        if not sh("git", "status", "--porcelain").stdout.strip():
            return "the run made no changes to the repository"

        # Every check agent in harness/pipeline.json must have passed too: a
        # green gate on a run that skipped review is not a pass.
        for check in load_spec()["checks"]:
            if check.get("when") == "visual" and (self.args.no_visual or not plan.get("screens")):
                continue
            verdict = read_json(self.dir / f"{check['artifact']}.json")
            if verdict.get("verdict") != "pass":
                return (f"{check['artifact']}.json is missing or not 'pass'. Run the "
                        f"{check['agent']} stage, save its JSON to "
                        f"{self.dir}/{check['artifact']}.json and fix what it reports.\n"
                        + json.dumps(verdict.get("blocking") or verdict.get("screens") or [])[:2000])

        self.shots = []
        if self.args.no_visual:
            return ""
        if failure := native_build(ROOT, self.env, self.event):
            return failure
        for screen in plan.get("screens", []):
            png = self.dir / f"final-{screen}.png"
            flags = ["--screen", screen, "--dry-run", "--out", str(png), "--wait", str(self.args.wait)]
            for text in plan.get("expect_text", {}).get(screen, []):
                flags += ["--expect", text]
            proc = sh("scripts/telegram.sh", *flags, check=False)
            self.event("ocr", screen=screen, ok=proc.returncode == 0)
            if proc.returncode != 0:
                return (f"screen '{screen}' failed OCR verification. What the OCR "
                        f"actually read:\n{proc.stderr[-2500:]}")
            self.shots.append({"screen": screen, "png": str(png)})
        return ""

    def commit(self, summary: str, status: str) -> None:
        sh("git", "add", "-A")
        if not sh("git", "diff", "--cached", "--quiet", check=False).returncode:
            return
        title = summary if status == "pass" else f"wip(agent): {summary} [failed run]"
        body = (f"{title}\n\nAgent run {self.id} ({status}).\n"
                f"Request: {self.args.request}\n"
                f"Artifacts: .harness/runs/{self.id}/ (local)\n\n"
                "Co-Authored-By: Claude Code <noreply@anthropic.com>\n")
        subprocess.run(["git", "commit", "-q", "-F", "-"], cwd=ROOT, input=body, text=True, check=True)
        self.event("commit", status=status)

    # --- report --------------------------------------------------------------

    def scope(self, files: list[str]) -> dict:
        """The verification level the diff called for vs the one the planner
        chose: a measurable check on a decision we leave to the agent."""
        scope = classify(files)
        scope["planned"] = (read_json(self.dir / "plan.json").get("verify") or {}).get("level")
        return scope

    def report(self, status: str, summary: str, failure: RunFailed | None) -> str:
        mark = {"pass": "✓", "fail": "✗"}
        checks = [f"{c['name']} {mark.get(c['status'], '?')}" for c in self.gate.get("checks", [])]
        if self.shots:
            checks.append("OCR ✓")
        for check in load_spec()["checks"]:
            if check.get("when") == "visual" and self.args.no_visual:
                continue
            verdict = read_json(self.dir / f"{check['artifact']}.json").get("verdict")
            checks.append(f"{check['agent']} {mark.get(verdict, '–')}")
        files = sh("git", "diff", "--name-only", "HEAD~1", check=False).stdout.split() if status == "pass" else []
        u = self.usage
        lines = [
            f"{'✅' if status == 'pass' else '❌'} {summary}",
            f"run: {self.id}",
            f"branch: {self.branch}",
            "checks: " + " · ".join(checks),
            f"agents: {self.backend.name}/{self.args.orchestrator} · {u['turns']} turns · "
            f"{u['agent_seconds'] / 60:.1f} min · ${u['cost_usd']:.2f}"
            f" · {self.fix_iterations} fix iteration(s)",
            f"total: {(time.time() - self.started) / 60:.1f} min",
        ]
        if files:
            lines.append("files: " + ", ".join(files[:8]) + (" …" if len(files) > 8 else ""))
            scope = self.scope(files)
            planned = scope["planned"] or "?"
            mark = " ⚠ planner underestimated shared code" if (planned, scope["level"]) == ("quick", "full") else ""
            lines.append(f"scope: {scope['level']} (planned {planned}){mark}")
        retro = analyse(load())
        if retro["candidates"]:
            # Counts only: report.md becomes a public PR body, and a raw local
            # command can carry paths or data that should stay on the machine.
            lines.append(f"retro: {retro['coverage']:.0%} of commands via repo tools, "
                         f"{len(retro['candidates'])} repeated by hand (harness/retro.py)")
        if failure:
            lines.append(f"failed at {failure.stage}: {failure.detail[:700]}")
        if status == "pass":
            lines.append("Reply /pr to open a pull request, /continue <request> to iterate.")
        text = "\n".join(lines)
        (self.dir / "report.md").write_text(text + "\n")
        (self.dir / "summary.json").write_text(json.dumps({
            "id": self.id, "status": status, "summary": summary, "branch": self.branch,
            "request": self.args.request, "base": self.base, "usage": u,
            "backend": self.backend.name, "orchestrator": self.args.orchestrator,
            "roster": snapshot(self.backend.name, self.backend.route),
            "routes": self.backend.routes,
            "fix_iterations": self.fix_iterations, "shots": self.shots,
            "scope": self.scope(files) if files else None,
            "failure": failure and {"stage": failure.stage, "detail": failure.detail},
        }, indent=2))
        return text

    # --- main ----------------------------------------------------------------

    def execute(self) -> int:
        self.base = None
        summary, status, failure = self.args.request, "fail", None
        self.event("start", request=self.args.request, backend=self.backend.name)
        try:
            flags = ["--backend", self.backend.name]
            flags += [f"--route={a}={r}" for a, r in self.backend.routes.items()]
            flags += ["--no-telegram"] if self.args.no_telegram else []
            flags += ["--no-visual"] if self.args.no_visual else []
            proc = sh("harness/preflight.sh", *flags, check=False)
            if proc.returncode != 0:
                raise RunFailed("preflight", proc.stdout + proc.stderr)
            self.base = self.isolate()
            self.telegram("--text", f"🛠 {self.id}\n{self.args.request}")

            self.orchestrate()
            plan = read_json(self.dir / "plan.json")
            if not plan:
                raise RunFailed("plan", "the agent did not write plan.json")
            summary = plan.get("summary", summary)

            while feedback := self.verify(plan):
                with (self.dir / "harness-iterations.log").open("a") as log:
                    log.write(feedback[:300] + "\n---\n")
                if self.fix_iterations >= self.args.retries:
                    raise RunFailed("verify", feedback)
                self.fix_iterations += 1
                self.event("fix", iteration=self.fix_iterations)
                self.fix(plan, feedback)
                plan = read_json(self.dir / "plan.json") or plan
            status = "pass"
        except RunFailed as exc:
            failure = exc
            self.event("failed", at=exc.stage)
        finally:
            if self.base:
                self.commit(summary, status)

        text = self.report(status, summary, failure)
        self.event("end", status=status, cost=round(self.usage["cost_usd"], 4))
        visual = {s.get("screen"): s for s in read_json(self.dir / "visual.json").get("screens", [])}
        for shot in self.shots:
            caption = visual.get(shot["screen"], {}).get("caption") or summary
            self.telegram("--file", shot["png"], "--caption", f"{shot['screen']}: {caption}")
        self.telegram("--text", text)
        if self.base and not self.args.stay:
            sh("git", "switch", self.base, check=False)
        print(text)
        return 0 if status == "pass" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("request")
    parser.add_argument("--base", help="branch to start from (default: current)")
    parser.add_argument("--retries", type=int, default=2, help="harness-level fix iterations")
    parser.add_argument("--max-turns", type=int, default=120)
    parser.add_argument("--backend", default="claude", choices=BACKENDS,
                        help="claude (cloud), opencode + Ollama (local) or hybrid "
                             "(a route per agent, harness/backends.json)")
    parser.add_argument("--route", action="append", metavar="AGENT=ROUTE",
                        help="run one agent elsewhere, e.g. reviewer=claude or "
                             "implementer=ollama/qwen3-14b-agent:latest")
    parser.add_argument("--orchestrator", choices=["skill", "harness"],
                        help="who sequences the agents: the /ship skill (an LLM) or "
                             "harness/pipeline.py (code). Default: skill on claude, "
                             "harness on opencode")
    parser.add_argument("--wait", type=int, default=25, help="seconds to wait per capture")
    parser.add_argument("--no-telegram", action="store_true")
    parser.add_argument("--no-visual", action="store_true", help="skip simulator captures")
    parser.add_argument("--stay", action="store_true", help="stay on the agent branch afterwards")
    args = parser.parse_args()
    # The /ship skill runs every subagent inside one Claude session, so it can
    # only honour routes that are all Claude: anything mixed needs the harness.
    args.orchestrator = args.orchestrator or (
        "skill" if args.backend == "claude" and not args.route else "harness")
    return Run(args).execute()


if __name__ == "__main__":
    sys.exit(main())
