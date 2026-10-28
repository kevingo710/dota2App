#!/usr/bin/env python3
"""Test the eval harness itself, without calling any model (seconds, free).

An eval suite with a broken grader silently mis-scores every agent, so this
checks, against a real sandbox:

  - every case's setup edits and mutation anchors still apply to the code
  - graders accept a known-good answer and reject a known-bad one
  - mutation testing kills a mutant with a real test, and a useless test survives

    harness/evals/selftest.py
"""

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path[:0] = [str(HERE), str(HERE.parent)]

from agents import eval_cases, load_roster  # noqa: E402
from eval import apply_edits, build_base  # noqa: E402
from graders import Context, grade, tree_fingerprint  # noqa: E402

GOOD_TEST = """
describe('selftest', () => {
  it('unprefixed npc names have no picture', () => {
    const {toHero} = require('../../src/data/mappers/HeroMapper');
    expect(toHero({id: 1, localized_name: 'A', name: 'antimage', primary_attr: 'agi',
      attack_type: 'Melee', roles: []}).picture).toBe('');
  });
});
"""
USELESS_TEST = "describe('selftest', () => { it('is true', () => { expect(true).toBe(true); }); });\n"

failures = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global failures
    failures += not condition
    print(f"{'ok  ' if condition else 'FAIL'} {label}{f'  ({detail})' if detail and not condition else ''}")


def sandbox_from(base: Path, tmp: Path, name: str) -> Path:
    path = tmp / name
    shutil.copytree(base, path, symlinks=True)
    return path


def result(agents: dict, rows: list[tuple], pipeline: str = "p1") -> dict:
    from eval import summarize
    cases = [{"agent": a, "case": c, "attempt": 1, "pass": p, "score": float(p), "seconds": 10.0,
              "tokens": 100, "cost_usd": 0.1} for a, c, p in rows]
    return {"kind": "agents", "backend": "claude", "timestamp": "t",
            "roster": {"fingerprint": "f", "agents": agents, "skill": "s", "hooks": "h",
                       "pipeline": pipeline},
            "summary": summarize(cases), "cases": cases}


def check_compare() -> None:
    """Adding an agent and editing another must show up in `compare`."""
    from eval import compare
    reviewer = {"hash": "aaa", "model": "opus", "tools": ["Read"], "eval_cases": 2}
    before = result({"reviewer": reviewer},
                    [("reviewer", "axios", True), ("reviewer", "clean", True)])
    after = result({"reviewer": {**reviewer, "hash": "bbb"},
                    "security-auditor": {"hash": "ccc", "model": "opus", "tools": ["Read"],
                                         "eval_cases": 0}},
                   [("reviewer", "axios", True), ("reviewer", "clean", False)], pipeline="p2")
    report, regressed = compare(before, after)
    check("compare: new agent is reported", "+ security-auditor added" in report, report)
    check("compare: new agent without evals is flagged", "no eval cases" in report)
    check("compare: edited agent is reported", "~ reviewer: prompt/config changed" in report)
    check("compare: pipeline change is reported", "~ pipeline changed" in report)
    check("compare: flipped case is listed", "▼ reviewer/clean: 100% → 0%" in report)
    check("compare: regression is detected", regressed)


def check_routing() -> None:
    """Hybrid routing: the right runtime and model per agent, no model called."""
    from backends import get_backend, parse_routes
    hybrid = get_backend("hybrid", parse_routes(["reviewer=ollama/gpt-oss-agent:latest"]))
    cmd = lambda agent: resolve_cmd(hybrid, agent)  # noqa: E731
    check("route: override sends reviewer to opencode with -m",
          cmd("reviewer")[:2] == ["opencode", "run"] and "ollama/gpt-oss-agent:latest" in cmd("reviewer"))
    claude_cmd = resolve_cmd(get_backend("claude", {"test-writer": "claude:haiku"}), "test-writer")
    check("route: claude:<model> passes --model", claude_cmd[claude_cmd.index("--model") + 1] == "haiku")
    check("route: unrouted agent keeps the backend", resolve_cmd(get_backend("opencode"), "planner")[0] == "opencode")
    from backends import Router
    esc = Router("hybrid", "opencode", {"planner": "claude"}, {"implementer": "claude:haiku"}, 1)
    check("escalation: a failed fix moves implementer to its escalation route",
          esc.route("implementer") == "opencode" and esc.route("implementer", True) == "claude:haiku")
    check("escalation: agents without one keep their route", esc.route("planner", True) == "claude")
    try:
        parse_routes(["reviewer=gpt-oss"])
        check("route: a malformed route is rejected", False)
    except SystemExit:
        check("route: a malformed route is rejected", True)


def resolve_cmd(router, agent: str) -> list[str]:
    from backends import resolve
    return resolve(router.route(agent)).command("hi", ROOT, agent, None, 10)


def check_matrix() -> None:
    """matrix picks the cheapest route that is good enough, per agent."""
    from eval import current_hashes, matrix
    hashes = current_hashes()

    def run(stamp, agent, route, model, passes, cost):
        kind = "claude" if route.startswith("claude") else "opencode"
        info = {"hash": hashes[(agent, kind)], "model": model, "route": route}
        rows = [{"agent": agent, "case": f"c{i}", "pass": p, "score": float(p),
                 "seconds": 10, "cost_usd": cost} for i, p in enumerate(passes)]
        return {"kind": "agents", "backend": kind, "timestamp": stamp,
                "roster": {"agents": {agent: info}}, "cases": rows}

    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for i, data in enumerate([
                run("1", "implementer", "claude", "opus", [1, 1, 1], 0.1),
                run("2", "implementer", "opencode", "qwen", [1, 1, 0], 0.0),
                run("3", "reviewer", "claude", "opus", [1, 1, 1, 1], 0.1),
                run("4", "reviewer", "opencode", "qwen", [1, 1, 1, 0], 0.0)]):
            files.append(Path(tmp) / f"{i}.json")
            files[-1].write_text(json.dumps(data))
        files.append(files[0])  # a baseline is a copy of a run: counted once
        cells, best = matrix(files, {"implementer": 0.34})
        check("matrix: duplicate runs are counted once",
              next(c for c in cells if c["model"] == "opus" and c["agent"] == "implementer")["runs"] == 3)
        check("matrix: backstopped agent goes local within tolerance", best["implementer"] == "opencode")
        check("matrix: zero-tolerance agent keeps the best model", best["reviewer"] == "claude")


def check_run_failure_path() -> None:
    """A failed run must reach its report. Regression: event("failed",
    stage=...) collided with event()'s own `stage` and crashed every failed run
    before summary.json and the Telegram report were written."""
    import time
    import types
    from run import Run, RunFailed
    with tempfile.TemporaryDirectory() as tmp:
        fake = types.SimpleNamespace(dir=Path(tmp), started=time.time())
        exc = RunFailed("verify", "gate red")
        try:
            Run.event(fake, "failed", at=exc.stage)
            line = json.loads((Path(tmp) / "events.jsonl").read_text())
            check("run.py: failure event is logged", line == {**line, "stage": "failed", "at": "verify"})
        except TypeError as error:
            check("run.py: failure event is logged", False, str(error))
    source = (ROOT / "harness" / "run.py").read_text()
    check("run.py: no event() call passes stage= twice",
          not re.search(r"self\.event\([^)]*\bstage=", source))


def check_scope() -> None:
    from scope import classify
    quick = classify(["src/presentation/screens/SuperstarScreen.tsx"])
    check("scope: one screen is quick and maps to its screen",
          quick["level"] == "quick" and quick["screens"] == ["superstar"])
    full = classify(["src/presentation/screens/HomeScreen.tsx", "src/presentation/theme/colors.ts"])
    check("scope: a theme token is shared code -> full, with its reason",
          full["level"] == "full" and "every screen" in full["shared"][0]["why"])
    check("scope: nothing changed is none", classify([])["level"] == "none")


def check_design_rules() -> None:
    from agents import Agent, design_problems
    spec = {"planner": "planner", "build": [{"agent": "implementer"}],
            "checks": [{"agent": "reviewer"}], "fixer": "implementer"}

    def agent(name, tools):
        return Agent(name, "", tools, "inherit", "", Path(f"{name}.md"))
    good = {"planner": agent("planner", ["Read"]), "implementer": agent("implementer", ["Read", "Edit"]),
            "reviewer": agent("reviewer", ["Read", "Bash"])}
    check("design: the real-shaped roster passes", design_problems(good, spec) == [])
    bad = {**good, "reviewer": agent("reviewer", ["Read", "Edit"]),
           "implementer": agent("implementer", ["Read"]), "helper": agent("helper", ["Read", "Fly"])}
    problems = "\n".join(design_problems(bad, spec))
    check("design: a judge that can edit is rejected", "'reviewer' judges the work but can edit" in problems)
    check("design: a builder without write tools is rejected", "'implementer' builds but has no" in problems)
    check("design: an agent outside the pipeline is rejected", "'helper' is not used" in problems)
    check("design: an unknown tool is rejected", "unknown tool(s) ['Fly']" in problems)


def check_retro() -> None:
    import subprocess
    from retro import analyse, normalize
    rows = [{"session": s, "command": c} for s, c in [
        ("a", "cd /repo && ffmpeg -i in.mp4 out.gif"), ("b", "ffmpeg  -i in.mp4 out.gif"),
        ("a", "harness/gate.sh"), ("b", "git diff"), ("c", "brew install x")]]
    report = analyse(rows)
    check("retro: same work in two sessions is a candidate",
          [c["command"] for c in report["candidates"]] == ["ffmpeg -i in.mp4 out.gif"])
    check("retro: repo tools and reads count as covered", report["covered"] == 2)
    check("retro: temp paths are normalized away",
          normalize("cat /private/var/folders/zw/x/y.log") == "cat <tmp>")
    with tempfile.TemporaryDirectory() as tmp:
        event = {"tool_name": "Bash", "tool_input": {"command": "curl -H TOKEN=abc123 x"}}
        subprocess.run([sys.executable, str(ROOT / ".claude/hooks/record_command.py")],
                       input=json.dumps(event), text=True, env={"HARNESS_RUN_DIR": tmp, "PATH": ""})
        line = (Path(tmp) / "commands.jsonl").read_text()
        check("record_command: secrets are redacted", "abc123" not in line and "<redacted>" in line)


def check_redact() -> None:
    """Baselines are public: no home dir or temp paths, and still valid JSON."""
    from eval import redact
    home = str(Path.home())
    data = {"detail": f'at {home}/x.js:3\n  "quoted" /private/var/folders/ab/c/T/box/f.ts\\', "n": 1}
    out = json.dumps(redact(data))
    check("redact: no home dir or temp path", home not in out and "/var/folders" not in out)
    check("redact: output is still valid JSON", json.loads(out)["n"] == 1)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="dota2app-selftest-") as tmp:
        tmp = Path(tmp)
        base = build_base(tmp)

        for name in load_roster():
            for case in eval_cases(name):
                box = sandbox_from(base, tmp, f"{name}-{case['id']}")
                try:
                    apply_edits(box, case.get("setup", {}).get("edits", []))
                    ok = True
                    for g in case["graders"]:
                        if g["type"] == "mutation_killed":
                            for edit in g["edits"]:
                                ok &= edit["old"] in (box / edit["file"]).read_text()
                    check(f"{name}/{case['id']}: setup and mutation anchors apply", ok)
                except Exception as exc:
                    check(f"{name}/{case['id']}: setup and mutation anchors apply", False, str(exc))
                shutil.rmtree(box)

        # JSON graders: a known-good reviewer answer passes, a wrong one fails.
        box = sandbox_from(base, tmp, "json")
        good = {"verdict": "fail", "blocking": [{"file": "src/presentation/screens/HomeScreen.tsx",
                                                  "issue": "axios in presentation breaks the layer rule"}]}
        specs = [{"type": "json_equals", "path": "verdict", "value": "fail"},
                 {"type": "json_regex", "path": "blocking", "regex": "HomeScreen"},
                 {"type": "unchanged"}]
        ctx = Context(box, good, json.dumps(good), tree_fingerprint(box))
        check("json graders accept a correct answer", all(r["pass"] for r in grade(ctx, specs)))
        ctx = Context(box, {"verdict": "pass", "blocking": []}, "", tree_fingerprint(box))
        check("json graders reject a wrong answer", not any(r["pass"] for r in grade(ctx, specs[:2])))
        ctx = Context(box, None, "no json here", tree_fingerprint(box))
        check("missing JSON fails instead of crashing", not grade(ctx, specs[:1])[0]["pass"])

        # Mutation testing: a real test kills the mutant, a useless one does not.
        mutant = {"type": "mutation_killed", "edits": [
            {"file": "src/data/mappers/HeroMapper.ts", "old": "npcName.startsWith(NPC_PREFIX)", "new": "true"}]}
        test_file = box / "__tests__/data/Selftest.test.ts"
        test_file.write_text(GOOD_TEST)
        ctx = Context(box, None, "", "")
        check("mutation_killed: real test kills the mutant", grade(ctx, [mutant])[0]["pass"])
        test_file.write_text(USELESS_TEST)
        check("mutation_killed: useless test lets it survive", not grade(ctx, [mutant])[0]["pass"])
        check("mutation_killed restores the source",
              "npcName.startsWith(NPC_PREFIX)" in (box / "src/data/mappers/HeroMapper.ts").read_text())

        # Scope graders.
        check("changed_within flags out-of-scope files",
              not grade(ctx, [{"type": "changed_within", "files": ["src/"]}])[0]["pass"])
        check("unchanged detects a write",
              not grade(Context(box, None, "", tree_fingerprint(base)), [{"type": "unchanged"}])[0]["pass"])

    check_compare()
    check_routing()
    check_matrix()
    check_run_failure_path()
    check_scope()
    check_design_rules()
    check_retro()
    check_redact()
    print(f"\n{'selftest: PASS' if not failures else f'selftest: {failures} FAILED'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
