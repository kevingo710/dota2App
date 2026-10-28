#!/usr/bin/env python3
"""Evaluate the agents one by one and the system as a whole, and track how the
numbers move when the roster changes.

    harness/eval.py agents   [--backend claude|opencode|hybrid] [--route AGENT=ROUTE]
                             [--agent NAME] [--case ID] [--repeat N]
    harness/eval.py system   [--backend B] [--route AGENT=ROUTE] [--task ID] [--repeat N]
    harness/eval.py matrix   [A.json B.json ...]   pass rate per agent x model, best route
    harness/eval.py compare  [A.json [B.json]]       default: committed baseline vs latest run
    harness/eval.py baseline [--kind agents|system] [--backend B]   promote the latest run
    harness/eval.py history  [--kind agents|system] [--backend B]

Two levels:

  agents   Each agent alone, on fixed inputs, in a throw-away copy of the repo
           (harness/evals/agents/<agent>.json). Graded deterministically:
           JSON contracts, git diff scope, the quality gate, mutation tests.
  system   Full harness/run.py runs on harness/evals/system.json tasks.

Every result stores the roster fingerprint (harness/agents.py): a hash per
agent plus the skill, hooks and pipeline. `compare` lines up two results and
reports which agents were added/removed/changed next to the deltas in pass
rate, score, time, tokens and cost, and the cases that flipped. Add an agent,
run `agents` + `system`, then `compare`: you see exactly what it bought and
what it cost. `--fail-on-regression` makes compare usable as a gate.
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "evals"))

from agents import eval_cases, load_roster, snapshot  # noqa: E402
from backends import extract_json, get_backend, parse_routes  # noqa: E402
from graders import Context, changed_files, grade, tree_fingerprint  # noqa: E402

ROOT = HERE.parent
RESULTS = ROOT / ".harness" / "evals"
BASELINES = HERE / "evals" / "baselines"
SYSTEM_TASKS = HERE / "evals" / "system.json"
SKIP_IN_SANDBOX = ("ios/", "android/")
CASE_TIMEOUT = 20 * 60


# --- sandbox -------------------------------------------------------------------

def build_base(tmp: Path) -> Path:
    """Snapshot of the working tree as it is now (uncommitted work included,
    gitignored secrets excluded), committed so diffs start from zero."""
    base = tmp / "base"
    files = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.splitlines()
    for rel in files:
        src = ROOT / rel
        if rel.startswith(SKIP_IN_SANDBOX) or not src.is_file():
            continue
        dest = base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
    (base / "node_modules").symlink_to(ROOT / "node_modules")
    for cmd in (["git", "init", "-q"], ["git", "add", "-A"],
                ["git", "-c", "user.name=eval", "-c", "user.email=eval@local",
                 "commit", "-qm", "eval baseline"]):
        subprocess.run(cmd, cwd=base, check=True, capture_output=True)
    return base


def apply_edits(sandbox: Path, edits: list[dict]) -> None:
    for edit in edits:
        path = sandbox / edit["file"]
        source = path.read_text()
        if edit["old"] not in source:
            raise RuntimeError(f"setup anchor not found in {edit['file']}: {edit['old'][:60]!r}")
        path.write_text(source.replace(edit["old"], edit["new"], 1))


# --- running -------------------------------------------------------------------

def render(case: dict, sandbox: Path) -> str:
    plan = f"```json\n{json.dumps(case.get('plan', {}), indent=2)}\n```"
    return case["prompt"].replace("{plan}", plan).replace("{sandbox}", str(sandbox))


def run_agent_case(backend, agent: str, case: dict, base: Path, tmp: Path, attempt: int) -> dict:
    sandbox = tmp / f"{agent}-{case['id']}-{attempt}"
    shutil.copytree(base, sandbox, symlinks=True)
    apply_edits(sandbox, case.get("setup", {}).get("edits", []))
    baseline = tree_fingerprint(sandbox)
    env = {**os.environ, "HARNESS_MANAGED": "1", "HARNESS_RUN_DIR": str(sandbox / ".harness")}
    result = backend.run(render(case, sandbox), cwd=sandbox, agent=agent, env=env,
                         log=tmp / f"{sandbox.name}.log", max_turns=60, timeout=CASE_TIMEOUT)
    ctx = Context(sandbox=sandbox, output=extract_json(result.text), text=result.text,
                  baseline=baseline)
    graders = grade(ctx, case["graders"])
    passed = sum(g["pass"] for g in graders)
    ok = not result.error and passed == len(graders)
    row = {
        "agent": agent, "case": case["id"], "attempt": attempt,
        "pass": ok, "failure": None if ok else failure_kind(result.error),
        "score": round(passed / len(graders), 3) if graders else 0.0,
        "graders": graders, "error": result.error[:300],
        "seconds": round(result.seconds, 1), "turns": result.turns,
        "tokens": result.tokens, "cost_usd": round(result.cost_usd, 4),
        "changed": changed_files(ctx),
        "answer": result.text[-1200:],  # for auditing a verdict, not for grading
    }
    shutil.rmtree(sandbox, ignore_errors=True)
    return row


INFRA_ERRORS = ("timed out", "permission requested", "connection refused", "no output")


def failure_kind(error: str) -> str:
    """'infra' failures say nothing about the agent (timeouts, permission
    prompts, a dead Ollama): fix the harness and rerun, do not tune prompts."""
    return "infra" if any(e in error.lower() for e in INFRA_ERRORS) else "model"


def run_system_task(backend, task: dict, base: Path, tmp: Path, attempt: int) -> dict:
    sandbox = tmp / f"system-{task['id']}-{attempt}"
    shutil.copytree(base, sandbox, symlinks=True)
    started = time.time()
    # The sandbox's own copy of the harness, so the run is isolated from the
    # real checkout. Visual checks need Metro serving the sandbox: off here;
    # visual-qa is measured at the agent level with fixture screenshots.
    routes = [f"--route={a}={r}" for a, r in backend.routes.items()]
    proc = subprocess.run([sys.executable, "harness/run.py", task["request"], "--backend", backend.name,
                           *routes, "--no-telegram", "--no-visual", "--stay"],
                          cwd=sandbox, capture_output=True, text=True)
    summaries = sorted((sandbox / ".harness" / "runs").glob("*/summary.json"))
    summary = json.loads(summaries[-1].read_text()) if summaries else {}
    ctx = Context(sandbox=sandbox, output=None, text="", baseline="")
    passed_run = summary.get("status") == "pass"
    failure = summary.get("failure") or {}
    # An adversarial task (safe_failure) may be refused: failing without
    # landing the forbidden change is a correct answer too.
    safe = task.get("safe_failure") and summary.get("status") == "fail"
    graders = [{"type": "run_passed", "pass": passed_run or bool(safe),
                "detail": f"{failure.get('stage', '')}: {failure.get('detail', '')[:160]}"
                if summary else proc.stderr[-300:]}]
    if passed_run or safe:
        # run.py committed on the agent branch (a wip commit when it failed):
        # grade that commit's diff.
        if subprocess.run(["git", "log", "-1", "--format=%s"], cwd=sandbox, capture_output=True,
                          text=True).stdout.strip() != "eval baseline":
            subprocess.run(["git", "reset", "-q", "--soft", "HEAD~1"], cwd=sandbox)
        graders += grade(ctx, task.get("graders", []))
        if passed_run:
            graders += grade(ctx, task.get("graders_if_pass", []))
    usage = summary.get("usage", {})
    passed = sum(g["pass"] for g in graders)
    row = {
        "agent": "system", "case": task["id"], "attempt": attempt,
        "pass": passed == len(graders), "score": round(passed / len(graders), 3),
        "graders": graders, "error": "", "seconds": round(time.time() - started, 1),
        "turns": usage.get("turns", 0), "tokens": usage.get("tokens", 0),
        "cost_usd": round(usage.get("cost_usd", 0.0), 4),
        "fix_iterations": summary.get("fix_iterations"),
        "diff": subprocess.run(["git", "diff", "HEAD", "--stat"], cwd=sandbox, capture_output=True,
                               text=True).stdout[-800:],
    }
    # Keep the run's artifacts (plan, gate reports, agent logs) for auditing:
    # the sandbox is deleted, a failed case should still be explainable.
    if summaries:
        keep = RESULTS / "runs" / f"{backend.name}-{summaries[-1].parent.name}"
        shutil.copytree(summaries[-1].parent, keep, dirs_exist_ok=True)
        row["artifacts"] = str(keep.relative_to(ROOT))
    shutil.rmtree(sandbox, ignore_errors=True)
    return row


def summarize(rows: list[dict]) -> dict:
    groups: dict[str, list[dict]] = {}
    for row in rows:
        groups.setdefault(row["agent"], []).append(row)
    summary = {}
    for name, items in sorted(groups.items()) + [("ALL", rows)]:
        n = len(items) or 1
        summary[name] = {
            "runs": len(items),
            "pass_rate": round(sum(r["pass"] for r in items) / n, 3),
            "score": round(sum(r["score"] for r in items) / n, 3),
            "seconds": round(sum(r["seconds"] for r in items) / n, 1),
            "tokens": sum(r["tokens"] for r in items),
            "cost_usd": round(sum(r["cost_usd"] for r in items), 4),
            "infra_failures": sum(r.get("failure") == "infra" for r in items),
        }
    return summary


def redact(value):
    """Results get committed as baselines in a public repo: no home directory
    or temp paths in agent output, grader details or stack traces. Works on
    the decoded data, so JSON escapes are never touched."""
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if not isinstance(value, str):
        return value
    value = value.replace(str(Path.home()), "~")
    # Output is often truncated mid-path ("s/<user>/Projects/..."): drop any
    # leftover fragment that still carries the user name.
    value = re.sub(rf"[^\s\"']*\b{re.escape(Path.home().name)}/", "~/", value)
    return re.sub(r"(/private)?/var/folders/[^\s\"'):]+|/tmp/[^\s\"'):]+", "<tmp>", value)


def save(kind: str, backend, rows: list[dict]) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    stamp = f"{dt.datetime.now():%Y%m%d-%H%M%S}"
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip())
    data = {"kind": kind, "backend": backend.name, "timestamp": stamp,
            "git": {"commit": commit, "dirty": dirty},
            "roster": snapshot(backend.name, backend.route), "routes": backend.routes,
            "summary": summarize(rows), "cases": rows}
    path = RESULTS / f"{stamp}-{kind}-{backend.name}.json"
    path.write_text(json.dumps(redact(data), indent=2))
    return path


def print_summary(path: Path) -> None:
    data = json.loads(path.read_text())
    print(f"\n{data['kind']} eval on {data['backend']} · roster {data['roster']['fingerprint']}")
    print(f"{'agent':14} {'runs':>4} {'pass':>6} {'score':>6} {'sec':>6} {'tokens':>8} {'$':>7}")
    for name, s in data["summary"].items():
        print(f"{name:14} {s['runs']:>4} {s['pass_rate']:>6.0%} {s['score']:>6.2f} "
              f"{s['seconds']:>6.0f} {s['tokens']:>8} {s['cost_usd']:>7.2f}")
    for row in data["cases"]:
        if not row["pass"]:
            failed = [f"{g['type']}: {g['detail'][:90]}" for g in row["graders"] if not g["pass"]]
            print(f"  ✗ [{row.get('failure') or 'model'}] {row['agent']}/{row['case']}#{row['attempt']} "
                  f"{row['error'][:90] or ' | '.join(failed)}")
    infra = data["summary"]["ALL"].get("infra_failures", 0)
    if infra:
        print(f"⚠ {infra} infra failure(s): the harness or environment failed, not the agent. "
              "Fix and rerun before comparing.")
    print(f"saved {path.relative_to(ROOT)}")


def cmd_agents(args) -> int:
    backend = get_backend(args.backend, parse_routes(args.route))
    roster = load_roster()
    names = args.agent or sorted(roster)
    unknown = [n for n in names if n not in roster]
    if unknown:
        sys.exit(f"unknown agent(s) {unknown}; roster: {sorted(roster)}")
    rows = []
    with tempfile.TemporaryDirectory(prefix="dota2app-evals-") as tmp:
        # Canonical path: on macOS /var is a symlink to /private/var, and a
        # prompt mentioning the /var spelling looks like an outside directory
        # to opencode (permission prompt -> hang or denial).
        tmp = Path(tmp).resolve()
        base = build_base(tmp)
        for name in names:
            cases = [c for c in eval_cases(name) if not args.case or c["id"] in args.case]
            if not cases:
                print(f"!! {name}: no eval cases (harness/evals/agents/{name}.json)")
            for case in cases:
                for attempt in range(1, args.repeat + 1):
                    print(f"== {name}/{case['id']}#{attempt}", flush=True)
                    row = run_agent_case(backend, name, case, base, tmp, attempt)
                    kind = "" if row["pass"] else f" ({row['failure']})"
                    print(f"   {'PASS' if row['pass'] else 'FAIL'}{kind} score={row['score']} "
                          f"{row['seconds']}s", flush=True)
                    rows.append(row)
    path = save("agents", backend, rows)
    print_summary(path)
    return 0


def cmd_system(args) -> int:
    backend = get_backend(args.backend, parse_routes(args.route))
    tasks = [t for t in json.loads(SYSTEM_TASKS.read_text())
             if not args.task or t["id"] in args.task]
    rows = []
    with tempfile.TemporaryDirectory(prefix="dota2app-evals-") as tmp:
        tmp = Path(tmp).resolve()
        base = build_base(tmp)
        for task in tasks:
            for attempt in range(1, args.repeat + 1):
                print(f"== system/{task['id']}#{attempt}", flush=True)
                rows.append(run_system_task(backend, task, base, tmp, attempt))
    path = save("system", backend, rows)
    print_summary(path)
    return 0


# --- tracking ------------------------------------------------------------------

def results(kind: str | None = None, backend: str | None = None) -> list[Path]:
    paths = sorted(RESULTS.glob("*.json"))
    return [p for p in paths
            if (not kind or f"-{kind}-" in p.name) and (not backend or p.stem.endswith(f"-{backend}"))]


def delta(a, b, fmt="{:+.0%}") -> str:
    if a is None or b is None:
        return "new" if a is None else "gone"
    return "=" if a == b else fmt.format(b - a)


def compare(a: dict, b: dict) -> tuple[str, bool]:
    out = [f"# {a['kind']} eval: {a['timestamp']} ({a['backend']}) → {b['timestamp']} ({b['backend']})", ""]
    ra, rb = a["roster"], b["roster"]
    roster_lines = []
    for name in sorted(set(ra["agents"]) | set(rb["agents"])):
        x, y = ra["agents"].get(name), rb["agents"].get(name)
        if x is None:
            note = "" if y["eval_cases"] else " ⚠ no eval cases"
            roster_lines.append(f"+ {name} added ({y['model']}, {y['eval_cases']} cases){note}")
        elif y is None:
            roster_lines.append(f"- {name} removed")
        else:
            changes = [k for k in ("hash", "model", "tools") if x[k] != y[k]]
            if changes:
                detail = ", ".join(f"{k} {x[k]}→{y[k]}" if k != "hash" else "prompt/config changed"
                                   for k in changes)
                roster_lines.append(f"~ {name}: {detail}")
    for part in ("skill", "hooks", "pipeline"):
        if ra.get(part) != rb.get(part):
            roster_lines.append(f"~ {part} changed")
    out += ["## Roster", *(roster_lines or ["(unchanged)"]), ""]

    out += ["## Per agent", "| agent | pass | Δ pass | score Δ | sec Δ | tokens Δ | $ Δ |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    sa, sb = a["summary"], b["summary"]
    for name in sorted(set(sa) | set(sb), key=lambda n: (n == "ALL", n)):
        x, y = sa.get(name), sb.get(name)
        get = lambda s, k: s[k] if s else None  # noqa: E731
        pass_now = f"{y['pass_rate']:.0%}" if y else "–"
        out.append(f"| {name} | {pass_now} | {delta(get(x, 'pass_rate'), get(y, 'pass_rate'))} | "
                   f"{delta(get(x, 'score'), get(y, 'score'), '{:+.2f}')} | "
                   f"{delta(get(x, 'seconds'), get(y, 'seconds'), '{:+.0f}')} | "
                   f"{delta(get(x, 'tokens'), get(y, 'tokens'), '{:+d}')} | "
                   f"{delta(get(x, 'cost_usd'), get(y, 'cost_usd'), '{:+.2f}')} |")

    def rates(data):
        acc: dict[tuple, list] = {}
        for row in data["cases"]:
            acc.setdefault((row["agent"], row["case"]), []).append(row["pass"])
        return {k: sum(v) / len(v) for k, v in acc.items()}

    ca, cb = rates(a), rates(b)
    flips, regressed = [], False
    for key in sorted(set(ca) | set(cb)):
        x, y = ca.get(key), cb.get(key)
        if x is not None and y is not None and x != y:
            arrow = "▲" if y > x else "▼"
            regressed |= y < x
            flips.append(f"{arrow} {key[0]}/{key[1]}: {x:.0%} → {y:.0%}")
        elif x is None:
            flips.append(f"+ {key[0]}/{key[1]}: new case, {y:.0%}")
    out += ["", "## Cases that changed", *(flips or ["(none)"])]
    return "\n".join(out) + "\n", regressed


def load_pair(args) -> tuple[dict, dict]:
    if len(args.files) == 2:
        return tuple(json.loads(Path(f).read_text()) for f in args.files)
    if len(args.files) == 1:
        b = json.loads(Path(args.files[0]).read_text())
    else:
        latest = results(args.kind, args.backend)
        if not latest:
            sys.exit("no eval results yet; run harness/eval.py agents first")
        b = json.loads(latest[-1].read_text())
    baseline = BASELINES / f"{b['kind']}-{b['backend']}.json"
    if not baseline.exists():
        sys.exit(f"no baseline {baseline.relative_to(ROOT)}; create it with: harness/eval.py baseline")
    return json.loads(baseline.read_text()), b


def cmd_compare(args) -> int:
    a, b = load_pair(args)
    report, regressed = compare(a, b)
    print(report)
    return 1 if regressed and args.fail_on_regression else 0


def cmd_baseline(args) -> int:
    latest = results(args.kind, args.backend)
    if not latest:
        sys.exit("no eval results to promote")
    data = json.loads(latest[-1].read_text())
    BASELINES.mkdir(parents=True, exist_ok=True)
    target = BASELINES / f"{data['kind']}-{data['backend']}.json"
    target.write_text(json.dumps(redact(data), indent=2))
    print(f"baseline {target.relative_to(ROOT)} ← {latest[-1].name} "
          f"(pass {data['summary']['ALL']['pass_rate']:.0%})")
    return 0


def current_hashes() -> dict[tuple[str, str], str]:
    """(agent, 'claude'|'opencode') -> hash of the prompt that runs today."""
    out = {}
    for kind in ("claude", "opencode"):
        for name, a in snapshot(kind)["agents"].items():
            out[(name, kind)] = a["hash"]
    return out


def matrix(paths: list[Path], tolerance: dict[str, float],
           prefer: str = "cost") -> tuple[list[dict], dict[str, str]]:
    """Every (agent, model) measured with the agent's *current* prompt, pooled
    over all runs, and the route to pick per agent: the cheapest (then the
    fastest) among those within the agent's tolerance of the best pass rate."""
    hashes = current_hashes()
    pooled: dict[tuple[str, str], dict] = {}
    seen = set()
    for path in paths:
        data = json.loads(path.read_text())
        # A baseline is a copy of a run in .harness/evals: count it once.
        if data.get("kind") != "agents" or (data["timestamp"], data["backend"]) in seen:
            continue
        seen.add((data["timestamp"], data["backend"]))
        for row in data["cases"]:
            info = data["roster"]["agents"].get(row["agent"])
            if not info or row.get("failure") == "infra":
                continue  # infra failures say nothing about the model
            route = info.get("route") or data["backend"]
            kind = "claude" if route.startswith("claude") else "opencode"
            if hashes.get((row["agent"], kind)) != info["hash"]:
                continue  # produced by an older prompt
            cell = pooled.setdefault((row["agent"], info["model"]), {
                "agent": row["agent"], "model": info["model"], "route": route, "rows": []})
            cell["rows"].append(row)
    cells = []
    for cell in pooled.values():
        rows = cell.pop("rows")
        n = len(rows)
        cells.append({**cell, "runs": n,
                      "pass_rate": round(sum(r["pass"] for r in rows) / n, 3),
                      "score": round(sum(r["score"] for r in rows) / n, 3),
                      "seconds": round(sum(r["seconds"] for r in rows) / n, 1),
                      "cost_usd": round(sum(r["cost_usd"] for r in rows) / n, 4)})
    cells.sort(key=lambda c: (c["agent"], -c["pass_rate"], c["cost_usd"], c["seconds"]))
    best: dict[str, str] = {}
    for agent in sorted({c["agent"] for c in cells}):
        mine = [c for c in cells if c["agent"] == agent]
        top = max(c["pass_rate"] for c in mine)
        good = [c for c in mine if c["pass_rate"] >= top - tolerance.get(agent, 0.0)]
        order = ((lambda c: (c["cost_usd"], c["seconds"])) if prefer == "cost"
                 else (lambda c: (c["seconds"], c["cost_usd"])))
        best[agent] = min(good, key=order)["route"]
    return cells, best


def cmd_matrix(args) -> int:
    paths = [Path(f) for f in args.files] or sorted(BASELINES.glob("agents-*.json")) + results("agents")
    config_path = HERE / "backends.json"
    config = json.loads(config_path.read_text())
    tolerance = config["hybrid"].get("tolerance", {})
    if args.tolerance is not None:
        tolerance = dict.fromkeys(load_roster(), args.tolerance)
    cells, best = matrix(paths, tolerance, args.prefer)
    if not cells:
        sys.exit("no agent eval results for the current prompts; run harness/eval.py agents")
    print("| agent | model | runs | pass | score | s/case | $/case | pick |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for c in cells:
        pick = "◀" if best[c["agent"]] == c["route"] else ""
        print(f"| {c['agent']} | {c['model']} | {c['runs']} | {c['pass_rate']:.0%} | "
              f"{c['score']:.2f} | {c['seconds']:.0f} | {c['cost_usd']:.3f} | {pick} |")
    print("\nsuggested hybrid routes (harness/backends.json):")
    print(json.dumps(best, indent=2))
    if args.write:
        default = config["hybrid"]["default"]
        config["hybrid"]["routes"] = {a: r for a, r in best.items() if r != default}
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        print(f"wrote {config_path.relative_to(ROOT)}")
    return 0


def cmd_history(args) -> int:
    print(f"{'timestamp':16} {'kind':7} {'backend':9} {'roster':13} {'agents':>6} "
          f"{'pass':>6} {'score':>6} {'$':>7}")
    for path in results(args.kind, args.backend):
        d = json.loads(path.read_text())
        s = d["summary"]["ALL"]
        print(f"{d['timestamp']:16} {d['kind']:7} {d['backend']:9} {d['roster']['fingerprint']:13} "
              f"{len(d['roster']['agents']):>6} {s['pass_rate']:>6.0%} {s['score']:>6.2f} "
              f"{s['cost_usd']:>7.2f}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("agents")
    p.add_argument("--backend", default="claude")
    p.add_argument("--route", action="append", metavar="AGENT=ROUTE")
    p.add_argument("--agent", action="append")
    p.add_argument("--case", action="append")
    p.add_argument("--repeat", type=int, default=1)
    p.set_defaults(fn=cmd_agents)
    p = sub.add_parser("system")
    p.add_argument("--backend", default="claude")
    p.add_argument("--route", action="append", metavar="AGENT=ROUTE")
    p.add_argument("--task", action="append")
    p.add_argument("--repeat", type=int, default=1)
    p.set_defaults(fn=cmd_system)
    p = sub.add_parser("matrix")
    p.add_argument("files", nargs="*", help="default: baselines + every local agents run")
    p.add_argument("--tolerance", type=float,
                   help="accept a route this much below the best pass rate if it is cheaper, "
                        "for every agent (default: hybrid.tolerance in backends.json)")
    p.add_argument("--prefer", choices=["cost", "speed"], default="cost",
                   help="tie-break among good-enough routes: cheapest or fastest")
    p.add_argument("--write", action="store_true", help="store the picks as the hybrid routes")
    p.set_defaults(fn=cmd_matrix)
    p = sub.add_parser("compare")
    p.add_argument("files", nargs="*")
    p.add_argument("--kind")
    p.add_argument("--backend")
    p.add_argument("--fail-on-regression", action="store_true")
    p.set_defaults(fn=cmd_compare)
    for name, fn in (("baseline", cmd_baseline), ("history", cmd_history)):
        p = sub.add_parser(name)
        p.add_argument("--kind")
        p.add_argument("--backend")
        p.set_defaults(fn=fn)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
