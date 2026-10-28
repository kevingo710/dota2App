#!/usr/bin/env python3
"""The agent system as a Neo4j graph, updated live while the agents run.

    harness/graph.py up                  start a local Neo4j (Docker, bound to 127.0.0.1)
    harness/graph.py load                (re)load the structure: agents, tools, pipeline
                                         stages, models and routes per backend, eval scores
    harness/graph.py serve [--port N]    load, follow .harness/runs live and serve the
                                         viewer on http://localhost:7475
    harness/graph.py replay [RUN] [--speed S] [--max-gap G] [--min-gap G]
                                         replay a recorded run (default: the bundled
                                         demo, a hybrid run with an escalation)
    harness/graph.py export              print the structure as Cypher (no Neo4j needed)

Everything in the graph is derived: the structure from `.claude/agents/`,
`pipeline.json`, `backends.json` and the eval results; the runs from the
`events.jsonl` that run.py already writes. Nothing is edited in Neo4j, so the
database needs no volume and every load is safe to repeat (MERGE).

Talks to Neo4j through its HTTP API with the standard library: the harness
keeps zero Python dependencies. NEO4J_URL (default http://localhost:7474),
NEO4J_AUTH ("user:password"; unset for the local container, which runs
without auth and only listens on 127.0.0.1). Example queries:
harness/viewer/queries.cypher.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from agents import WRITE_TOOLS, Agent, load_roster, model_of  # noqa: E402
from backends import BACKENDS, get_backend  # noqa: E402

ROOT = HERE.parent
RUNS = ROOT / ".harness" / "runs"
VIEWER = HERE / "viewer"
DEMO = VIEWER / "demo-run.jsonl"
PIPELINE = json.loads((HERE / "pipeline.json").read_text())
NEO4J_URL = os.environ.get("NEO4J_URL", "http://localhost:7474")
NEO4J_IMAGE = "neo4j:5.26-community"
CONTAINER = "dota2app-neo4j"

Statement = tuple[str, dict]


# --- Neo4j -------------------------------------------------------------------

def neo4j(statements: list[Statement]) -> list[list[dict]]:
    """Run statements in one transaction; one list of row dicts per statement."""
    body = json.dumps({"statements": [{"statement": s, "parameters": p}
                                      for s, p in statements]}).encode()
    request = urllib.request.Request(f"{NEO4J_URL}/db/neo4j/tx/commit", body, {
        "Content-Type": "application/json", "Accept": "application/json"})
    if auth := os.environ.get("NEO4J_AUTH"):
        request.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.load(response)
    except urllib.error.URLError as exc:
        sys.exit(f"Neo4j is not reachable at {NEO4J_URL} ({exc.reason}); run: harness/graph.py up")
    if data["errors"]:
        raise RuntimeError(data["errors"][0]["message"])
    return [[dict(zip(r["columns"], row["row"])) for row in r["data"]] for r in data["results"]]


def up() -> int:
    running = subprocess.run(["docker", "ps", "-q", "-f", f"name={CONTAINER}"],
                             capture_output=True, text=True).stdout.strip()
    if not running:
        subprocess.run(["docker", "rm", "-f", CONTAINER], capture_output=True)
        # No volume and no auth: the graph is rebuilt from the repo, and the
        # ports only listen on loopback.
        subprocess.run(["docker", "run", "-d", "--name", CONTAINER,
                        "-p", "127.0.0.1:7474:7474", "-p", "127.0.0.1:7687:7687",
                        "-e", "NEO4J_AUTH=none", NEO4J_IMAGE], check=True, capture_output=True)
    for _ in range(60):
        try:
            urllib.request.urlopen(NEO4J_URL, timeout=2)
            print(f"Neo4j ready: {NEO4J_URL} (Browser), bolt://localhost:7687")
            return 0
        except OSError:
            time.sleep(1)
    sys.exit("Neo4j did not start; see: docker logs " + CONTAINER)


# --- structure ---------------------------------------------------------------

def label(model: str) -> str:
    """'ollama/qwen3-14b-agent:latest' -> 'qwen3-14b', 'sonnet' -> 'Claude Sonnet'."""
    if "/" not in model:
        return f"Claude {model.capitalize()}" if model != "inherit" else "Claude (session)"
    name = model.split("/", 1)[1].removesuffix(":latest").removesuffix("-agent")
    return name


def stages() -> list[dict]:
    """The pipeline as stages in order; checks send failures back to the fixer."""
    out = [{"name": PIPELINE["planner"], "kind": "agent", "agent": PIPELINE["planner"]}]
    out += [{"name": s["agent"], "kind": "agent", "agent": s["agent"], "when": s.get("when")}
            for s in PIPELINE["build"]]
    out.append({"name": "gate", "kind": "check", "agent": None, "on_fail": PIPELINE["fixer"]})
    out += [{"name": s["agent"], "kind": "agent", "agent": s["agent"], "when": s.get("when"),
             "on_fail": PIPELINE["fixer"]} for s in PIPELINE["checks"]]
    out.append({"name": "commit", "kind": "end", "agent": None})
    return [{**s, "order": i} for i, s in enumerate(out)]


def routes(roster: dict[str, Agent]) -> list[dict]:
    out = []
    for backend in BACKENDS:
        router = get_backend(backend)
        for name, agent in roster.items():
            primary, escalated = router.route(name), router.route(name, True)
            out.append({"backend": backend, "agent": name, "kind": "ROUTED_TO",
                        "model": model_of(agent, primary), "local": not primary.startswith("claude")})
            if escalated != primary:
                out.append({"backend": backend, "agent": name, "kind": "ESCALATES_TO",
                            "model": model_of(agent, escalated),
                            "local": not escalated.startswith("claude")})
    return out


def scores() -> list[dict]:
    """Pass rate per agent x model, pooled like `eval.py matrix` does."""
    from eval import BASELINES, matrix, results
    paths = (sorted(BASELINES.glob("agents-*.json"))
             + sorted((HERE / "evals" / "results").rglob("*-agents-*.json")) + results("agents"))
    cells, _ = matrix(paths, {})
    return [{k: c[k] for k in ("agent", "model", "runs", "pass_rate", "seconds", "cost_usd")}
            | {"local": "/" in c["model"]} for c in cells]


def structure() -> list[Statement]:
    roster = load_roster()
    agents = [{"name": a.name, "tools": a.tools, "hash": a.hash,
               "description": a.description.split(". ")[0],
               "role": "builder" if WRITE_TOOLS & set(a.tools) else "judge"}
              for a in roster.values()]
    models = {}
    for row in routes(roster) + scores():
        models[row["model"]] = {"name": row["model"], "label": label(row["model"]),
                                "local": row["local"]}
    return [
        # Structural edges are rebuilt; run history (Run, Call, Check) is kept.
        ("MATCH ()-[r:CAN_USE|ROUTED_TO|ESCALATES_TO|SCORED|NEXT|RUNS|ON_FAIL]->() DELETE r", {}),
        ("MATCH (a:Agent) WHERE NOT a.name IN $names DETACH DELETE a",
         {"names": list(roster)}),
        ("MATCH (s:Stage) DETACH DELETE s", {}),
        ("UNWIND $agents AS a MERGE (n:Agent {name: a.name}) "
         "SET n.role = a.role, n.tools = a.tools, n.hash = a.hash, n.description = a.description "
         "WITH n, a UNWIND a.tools AS t MERGE (tool:Tool {name: t}) MERGE (n)-[:CAN_USE]->(tool)",
         {"agents": agents}),
        ("UNWIND $models AS m MERGE (n:Model {name: m.name}) SET n.label = m.label, n.local = m.local",
         {"models": list(models.values())}),
        ("UNWIND $stages AS s CREATE (n:Stage {name: s.name, kind: s.kind, order: s.order}) "
         "SET n.when = s.when "
         "WITH n, s MATCH (a:Agent {name: s.agent}) MERGE (n)-[:RUNS]->(a)",
         {"stages": stages()}),
        ("MATCH (a:Stage), (b:Stage {order: a.order + 1}) MERGE (a)-[:NEXT]->(b)", {}),
        ("UNWIND $stages AS s MATCH (a:Stage {name: s.name}), (f:Stage {name: s.on_fail}) "
         "MERGE (a)-[:ON_FAIL]->(f)", {"stages": [s for s in stages() if s.get("on_fail")]}),
        ("UNWIND $routes AS r MATCH (a:Agent {name: r.agent}), (m:Model {name: r.model}) "
         "FOREACH (_ IN CASE r.kind WHEN 'ROUTED_TO' THEN [1] ELSE [] END | "
         "  MERGE (a)-[:ROUTED_TO {backend: r.backend}]->(m)) "
         "FOREACH (_ IN CASE r.kind WHEN 'ESCALATES_TO' THEN [1] ELSE [] END | "
         "  MERGE (a)-[:ESCALATES_TO {backend: r.backend}]->(m))", {"routes": routes(roster)}),
        ("UNWIND $scores AS s MATCH (a:Agent {name: s.agent}), (m:Model {name: s.model}) "
         "MERGE (a)-[r:SCORED]->(m) SET r.pass_rate = s.pass_rate, r.runs = s.runs, "
         "r.seconds = s.seconds, r.cost_usd = s.cost_usd", {"scores": scores()}),
    ]


# --- runs --------------------------------------------------------------------

class Tracker:
    """Turns one run's events.jsonl lines into graph writes.

    A run is a chain: (Run)-[:HAS]->(Call|Check), each step linked to the
    next by THEN, each Call to the Agent it ran and the Model it ran on."""

    def __init__(self, run_id: str, roster: dict[str, Agent], replay: bool = False):
        self.run, self.roster, self.replay = run_id, roster, replay
        self.seq, self.prev, self.open, self.escalate = 0, None, None, False
        self.last_call, self.calls = None, 0

    def _step(self, label: str, props: dict) -> list[Statement]:
        self.seq += 1
        node = f"{self.run}#{self.seq}"
        out = [(f"MATCH (r:Run {{id: $run}}) CREATE (r)-[:HAS]->(n:{label} {{id: $id}}) "
                "SET n += $props, n.seq = $seq, n.run = $run",
                {"run": self.run, "id": node, "seq": self.seq, "props": props})]
        if self.prev:
            out.append(("MATCH (a {id: $a}), (b {id: $b}) CREATE (a)-[:THEN]->(b)",
                        {"a": self.prev, "b": node}))
        self.prev = node
        return out

    def apply(self, ev: dict, now: float | None = None) -> list[Statement]:
        stage, t = ev.get("stage", ""), ev.get("t", 0)
        line = f"{t:>7.1f}s {stage} " + " ".join(
            f"{k}={v}" for k, v in ev.items() if k not in ("t", "stage") and v not in (None, ""))
        out: list[Statement] = [(
            "MERGE (r:Run {id: $run}) ON CREATE SET r.status = 'running', r.escalations = 0 "
            "SET r.t = $t, r.last = $stage, r.updated = $now, r.replay = $replay, "
            "r.log = (coalesce(r.log, []) + [$line])[-14..]",
            {"run": self.run, "t": t, "stage": stage, "line": line[:160],
             "now": now or time.time(), "replay": self.replay})]
        props = {"t": t}

        if stage == "start":
            out.append(("MATCH (r:Run {id: $run}) SET r.request = $request, r.backend = $backend",
                        {"run": self.run, "request": ev.get("request"), "backend": ev.get("backend")}))
        elif stage == "isolate":
            out.append(("MATCH (r:Run {id: $run}) SET r.branch = $branch",
                        {"run": self.run, "branch": ev.get("branch")}))
        elif stage == "agent-start" or (stage.startswith("agent:") and not stage.endswith(":done")):
            name = ev.get("agent") or (stage[6:] if stage.startswith("agent:") else "/ship")
            route = ev.get("route") or "claude"
            model = model_of(self.roster[name], route) if name in self.roster else route
            props |= {"agent": name, "route": route, "model": model, "label": label(model),
                      "local": not route.startswith("claude"), "status": "running",
                      "escalated": self.escalate}
            if self.escalate:
                out.append(("MATCH (r:Run {id: $run}) SET r.escalations = r.escalations + 1",
                            {"run": self.run}))
            self.escalate = False
            self.calls += 1
            props["n"] = self.calls
            out += self._step("Call", props)
            self.open = self.last_call = self.prev
            out += [("MATCH (c:Call {id: $id}), (a:Agent {name: $agent}) CREATE (c)-[:OF]->(a)",
                     {"id": self.open, "agent": name}),
                    ("MATCH (c:Call {id: $id}) MERGE (m:Model {name: $model}) "
                     "ON CREATE SET m.label = $label, m.local = $local CREATE (c)-[:ON]->(m)",
                     {"id": self.open, "model": model, "label": label(model),
                      "local": props["local"]})]
        elif stage == "agent-end" or stage.endswith(":done"):
            if self.open:
                out.append(("MATCH (c:Call {id: $id}) SET c.status = $status, c.seconds = $seconds, "
                            "c.turns = $turns, c.error = $error, c.cost = $cost, c.end = $t",
                            {"id": self.open, "status": "error" if ev.get("error") else "done",
                             "seconds": ev.get("seconds"), "turns": ev.get("turns"),
                             "error": ev.get("error"), "cost": ev.get("cost"), "t": t}))
                self.open = None
        elif stage in ("gate", "ocr"):
            out += self._step("Check", props | {"kind": stage, "ok": bool(ev.get("ok")),
                                                "screen": ev.get("screen")})
        elif stage == "verdict" and self.last_call:
            out.append(("MATCH (c:Call {id: $id}) SET c.verdict = $verdict",
                        {"id": self.last_call, "verdict": ev.get("verdict")}))
        elif stage == "escalate":
            self.escalate = True
        elif stage == "commit":
            out += self._step("Check", props | {"kind": "commit", "ok": ev.get("status") == "pass"})
            out.append(("MATCH (r:Run {id: $run}) SET r.status = $status",
                        {"run": self.run, "status": ev.get("status")}))
        elif stage in ("failed", "end"):
            out.append(("MATCH (r:Run {id: $run}) SET r.status = $status, r.failed_at = $at, "
                        "r.cost = coalesce($cost, r.cost)",
                        {"run": self.run, "status": ev.get("status", "fail"), "at": ev.get("at"),
                         "cost": ev.get("cost")}))
        return out


def forget(run_id: str) -> Statement:
    return ("MATCH (r:Run {id: $run}) OPTIONAL MATCH (r)-[:HAS]->(n) DETACH DELETE n, r",
            {"run": run_id})


def follow(stop: threading.Event, interval: float = 0.5) -> None:
    """Tail every run's events.jsonl into the graph, including runs started later."""
    roster, trackers, offsets = load_roster(), {}, {}
    while not stop.is_set():
        for path in sorted(RUNS.glob("*/events.jsonl")):
            size = path.stat().st_size
            if offsets.get(path, 0) >= size:
                continue
            run_id = path.parent.name
            if run_id not in trackers:
                trackers[run_id] = Tracker(run_id, roster)
                neo4j([forget(run_id)])
            with path.open() as f:
                f.seek(offsets.get(path, 0))
                chunk = f.read()
            complete, _, _ = chunk.rpartition("\n")  # a half-written line waits
            offsets[path] = offsets.get(path, 0) + len(complete) + (1 if complete else 0)
            mtime = path.stat().st_mtime
            statements = []
            for line in filter(None, complete.splitlines()):
                statements += trackers[run_id].apply(json.loads(line), now=mtime)
            if statements:
                neo4j(statements)
        stop.wait(interval)


def replay(path: Path, speed: float, max_gap: float, min_gap: float = 0.0) -> None:
    run_id = "demo" if path == DEMO else "replay-" + (
        path.parent.name if path.name == "events.jsonl" else path.stem)
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    tracker = Tracker(run_id, load_roster(), replay=True)
    neo4j([forget(run_id)])
    last = 0.0
    for ev in events:
        time.sleep(max(min(max(ev.get("t", 0) - last, 0) / speed, max_gap), min_gap))
        last = ev.get("t", last)
        neo4j(tracker.apply(ev))
        print(f"{ev.get('t', 0):>7.1f}s {ev.get('stage')}", flush=True)


# --- viewer ------------------------------------------------------------------

Q_STAGES = ("MATCH (s:Stage) OPTIONAL MATCH (s)-[:RUNS]->(a:Agent) "
            "OPTIONAL MATCH (s)-[:ON_FAIL]->(f:Stage) "
            "RETURN s.name AS name, s.kind AS kind, s.order AS order, s.when AS when, "
            "a.name AS agent, a.role AS role, a.tools AS tools, collect(f.name) AS on_fail "
            "ORDER BY order")
Q_ROUTES = ("MATCH (a:Agent)-[r:ROUTED_TO|ESCALATES_TO {backend: $backend}]->(m:Model) "
            "OPTIONAL MATCH (a)-[s:SCORED]->(m) "
            "RETURN a.name AS agent, type(r) AS kind, m.name AS model, m.label AS label, "
            "m.local AS local, s.pass_rate AS pass_rate, s.runs AS runs")
Q_RUN = ("MATCH (r:Run) WHERE $run IS NULL OR r.id = $run WITH r ORDER BY r.updated DESC LIMIT 1 "
         "OPTIONAL MATCH (r)-[:HAS]->(n) WITH r, n ORDER BY n.seq "
         "RETURN r {.*} AS run, collect(n {.*, type: labels(n)[0]}) AS steps")
Q_RUNS = ("MATCH (r:Run) RETURN r.id AS id, r.status AS status, r.backend AS backend "
          "ORDER BY r.updated DESC LIMIT 30")


def snapshot_view(run: str | None) -> dict:
    found = neo4j([(Q_RUN, {"run": run})])[0]
    current = found[0] if found and found[0]["run"] else {"run": None, "steps": []}
    backend = (current["run"] or {}).get("backend") or "hybrid"
    stages_rows, route_rows, runs = neo4j([(Q_STAGES, {}), (Q_ROUTES, {"backend": backend}),
                                           (Q_RUNS, {})])
    return {"backend": backend, "stages": stages_rows, "routes": route_rows,
            "run": current["run"], "steps": current["steps"], "runs": runs}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 (http.server API)
        path, _, query = self.path.partition("?")
        params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)
        if path == "/api/graph":
            body = json.dumps(snapshot_view(urllib.parse.unquote(params["run"])
                                            if params.get("run") else None)).encode()
            kind = "application/json"
        elif path in ("/", "/index.html"):
            body, kind = (VIEWER / "index.html").read_bytes(), "text/html; charset=utf-8"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def serve(port: int) -> int:
    neo4j(structure())
    stop = threading.Event()
    threading.Thread(target=follow, args=(stop,), daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"viewer: http://localhost:{port}  ·  following {RUNS.relative_to(ROOT)}/  ·  "
          f"Neo4j Browser: {NEO4J_URL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        stop.set()
    return 0


def literal(value) -> str:
    """A Python value as a Cypher literal (map keys unquoted)."""
    if isinstance(value, dict):
        return "{" + ", ".join(f"`{k}`: {literal(v)}" for k, v in value.items()) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(map(literal, value)) + "]"
    return json.dumps(value)  # strings, numbers, true/false/null match Cypher


def export() -> int:
    """The structure as Cypher for Neo4j Browser or cypher-shell (:param, then the statement)."""
    for statement, params in structure():
        for key, value in params.items():
            print(f":param {key} => {literal(value)}")
        print(f"{statement};\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("up")
    sub.add_parser("load")
    sub.add_parser("export")
    p = sub.add_parser("serve")
    p.add_argument("--port", type=int, default=7475)
    p = sub.add_parser("replay")
    p.add_argument("run", nargs="?", help="a run directory or events.jsonl (default: the demo)")
    p.add_argument("--speed", type=float, default=20, help="time compression (default 20x)")
    p.add_argument("--max-gap", type=float, default=2.5, help="cap on any wait, in seconds")
    p.add_argument("--min-gap", type=float, default=0.0, help="floor on every wait, so each step shows")
    args = parser.parse_args()

    if args.cmd == "up":
        return up()
    if args.cmd == "load":
        neo4j(structure())
        print("structure loaded")
        return 0
    if args.cmd == "export":
        return export()
    if args.cmd == "serve":
        return serve(args.port)
    path = Path(args.run) if args.run else DEMO
    replay(path / "events.jsonl" if path.is_dir() else path, args.speed, args.max_gap, args.min_gap)
    return 0


if __name__ == "__main__":
    sys.exit(main())
