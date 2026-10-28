#!/usr/bin/env python3
"""The agent roster: one definition per agent, every backend fed from it.

`.claude/agents/*.md` is the single source of truth. This module:

    harness/agents.py roster [--backend B] [--route A=R] [--models]
                                             print the roster and its fingerprint
    harness/agents.py sync                   regenerate the opencode copies
    harness/agents.py check                  fail if copies are stale, an agent
                                             has no eval cases or breaks a design
                                             rule (run by gate.sh)

The roster fingerprint (a hash per agent over prompt, tools and model, plus
the orchestration skill and hooks) is stored with every eval result. That is
how `harness/eval.py compare` can say "you added security-auditor and changed
reviewer's prompt" next to the change in the numbers.
"""

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = ROOT / ".claude" / "agents"
SKILL = ROOT / ".claude" / "skills" / "ship" / "SKILL.md"
HOOKS_DIR = ROOT / ".claude" / "hooks"
EVALS_DIR = ROOT / "harness" / "evals" / "agents"
OPENCODE_DIR = ROOT / ".opencode"
BACKENDS = json.loads((ROOT / "harness" / "backends.json").read_text())

# Claude Code tool -> opencode tool. Tools an agent does not list are disabled.
TOOL_MAP = {"Read": ["read", "list"], "Grep": ["grep"], "Glob": ["glob"],
            "Edit": ["edit", "patch"], "Write": ["write"], "Bash": ["bash"]}
OPENCODE_TOOLS = ["read", "list", "grep", "glob", "edit", "patch", "write", "bash",
                  "webfetch", "task", "todowrite", "todoread"]
GENERATED = "<!-- generated from {src} by harness/agents.py sync; edit the source, not this file -->\n"


@dataclass
class Agent:
    name: str
    description: str
    tools: list[str]
    model: str
    body: str
    source: Path

    @property
    def hash(self) -> str:
        return hashlib.sha256(self.source.read_bytes()).hexdigest()[:12]

    def model_for(self, backend: str) -> str:
        cfg = BACKENDS[backend]
        return cfg.get("models", {}).get(self.name) or cfg.get("default_model") or self.model


def parse(path: Path) -> Agent:
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise ValueError(f"{path}: missing frontmatter")
    meta = dict(line.split(":", 1) for line in match.group(1).splitlines() if ":" in line)
    meta = {k.strip(): v.strip() for k, v in meta.items()}
    return Agent(
        name=meta["name"], description=meta.get("description", ""),
        tools=[t.strip() for t in meta.get("tools", "").split(",") if t.strip()],
        model=meta.get("model", "inherit"), body=match.group(2).strip() + "\n", source=path,
    )


def load_roster() -> dict[str, Agent]:
    return {a.name: a for a in map(parse, sorted(AGENTS_DIR.glob("*.md")))}


def file_hash(*paths: Path) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def eval_cases(name: str) -> list[dict]:
    path = EVALS_DIR / f"{name}.json"
    return json.loads(path.read_text())["cases"] if path.exists() else []


def model_of(agent: Agent, route: str) -> str:
    """The model a route runs `agent` on, named the way eval results name it."""
    if route.startswith("claude"):
        return route.partition(":")[2] or agent.model
    return agent.model_for("opencode") if route == "opencode" else route


def snapshot(backend: str, route=None) -> dict:
    """What an eval result was produced with. Compared by eval.py.

    `route(agent)` is the backend's per-agent route (harness/backends.py); by
    default every agent runs on `backend` itself."""
    roster = load_roster()
    route = route or (lambda name, escalated=False: backend)

    def describe(agent: Agent) -> dict:
        where = route(agent.name)
        if where.startswith("claude"):
            # Hash what actually runs: on Claude that is the source .md...
            digest = agent.hash
        else:
            # ...on opencode the generated file, whose permissions and model
            # come from more than the source.
            digest = hashlib.sha256(render_opencode(agent).encode()).hexdigest()[:12]
        info = {"hash": digest, "model": model_of(agent, where), "route": where, "tools": agent.tools,
                "eval_cases": len(eval_cases(agent.name))}
        if route(agent.name, True) != where:
            info["escalation"] = route(agent.name, True)
        return info

    agents = {name: describe(a) for name, a in roster.items()}
    parts = {
        "skill": file_hash(SKILL),
        "hooks": file_hash(*sorted(HOOKS_DIR.glob("*.py"))),
        "pipeline": file_hash(ROOT / "harness" / "pipeline.json"),
    }
    combined = hashlib.sha256(json.dumps([agents, parts], sort_keys=True).encode()).hexdigest()[:12]
    return {"fingerprint": combined, "backend": backend, "agents": agents, **parts}


# --- opencode ----------------------------------------------------------------

def bash_rules() -> list[tuple[str, str]]:
    """The Claude Code Bash allowlist as opencode patterns; everything else is denied.

    Set per agent on purpose: opencode lets agent-level permissions override the
    global ones in opencode.json, so a global deny alone did not stop `git push`.
    """
    allow = json.loads((ROOT / ".claude/settings.json").read_text())["permissions"]["allow"]
    patterns = [re.sub(r"^Bash\((.*?):?\*?\)$", r"\1", rule).rstrip(":") + "*"
                for rule in allow if rule.startswith("Bash(")]
    return [("*", "deny")] + [(pattern, "allow") for pattern in patterns]


def render_opencode(agent: Agent) -> str:
    enabled = {t for tool in agent.tools for t in TOOL_MAP.get(tool, [])}
    tools = "\n".join(f"  {t}: {'true' if t in enabled else 'false'}" for t in OPENCODE_TOOLS)
    description = json.dumps(agent.description)
    edit = "allow" if "Edit" in agent.tools or "Write" in agent.tools else "deny"
    bash = ("\n".join(f"    {json.dumps(p)}: {a}" for p, a in bash_rules())
            if "Bash" in agent.tools else None)
    # external_directory: deny, never ask: an unattended run has nobody to
    # answer a prompt, so "ask" would hang until the timeout.
    permission = (f"permission:\n  edit: {edit}\n  webfetch: deny\n  external_directory: deny\n"
                  + (f"  bash:\n{bash}\n" if bash else "  bash: deny\n"))
    return (f"---\ndescription: {description}\nmode: all\n"
            f"model: {agent.model_for('opencode')}\ntools:\n{tools}\n{permission}---\n"
            + GENERATED.format(src=agent.source.relative_to(ROOT)) + "\n" + agent.body)


def render_ship_command() -> str:
    body = re.sub(r"^---\n.*?\n---\n", "", SKILL.read_text(), flags=re.S)
    return ('---\ndescription: "Plan, implement, test, gate, review and visually verify a change"\n---\n'
            + GENERATED.format(src=SKILL.relative_to(ROOT)) + body)


def expected_files() -> dict[Path, str]:
    files = {OPENCODE_DIR / "agents" / f"{a.name}.md": render_opencode(a)
             for a in load_roster().values()}
    files[OPENCODE_DIR / "commands" / "ship.md"] = render_ship_command()
    return files


def sync() -> None:
    expected = expected_files()
    for stale in (OPENCODE_DIR / "agents").glob("*.md"):
        if stale not in expected:
            stale.unlink()
            print(f"removed {stale.relative_to(ROOT)}")
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text() != content:
            path.write_text(content)
            print(f"wrote {path.relative_to(ROOT)}")


WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def design_problems(roster: dict[str, Agent], spec: dict) -> list[str]:
    """Design rules for the team, enforced rather than written down
    (docs/agent-design.md):

    SoC/SRP  a judge (the planner, every check agent) cannot edit: whoever
             decides "is this right?" must not be able to change the answer.
    ISP      a builder has the write tools its job needs, and no agent lists
             a tool the runtime does not know.
    YAGNI    every agent is used by the pipeline, and the pipeline only names
             agents that exist.
    """
    problems = []
    judges = {spec["planner"], *(c["agent"] for c in spec["checks"])}
    builders = {spec["fixer"], *(b["agent"] for b in spec["build"])}
    for name in sorted((judges | builders) - set(roster)):
        problems.append(f"harness/pipeline.json names '{name}', which has no .claude/agents/{name}.md")
    for name, agent in sorted(roster.items()):
        unknown = sorted(set(agent.tools) - set(TOOL_MAP) - WRITE_TOOLS)
        if unknown:
            problems.append(f"agent '{name}': unknown tool(s) {unknown}")
        if name in judges and WRITE_TOOLS & set(agent.tools):
            problems.append(f"agent '{name}' judges the work but can edit "
                            f"({sorted(WRITE_TOOLS & set(agent.tools))}): judges are read-only")
        if name in builders and not WRITE_TOOLS & set(agent.tools):
            problems.append(f"agent '{name}' builds but has no Edit/Write tool")
        if name not in judges | builders:
            problems.append(f"agent '{name}' is not used by harness/pipeline.json: "
                            "add it to a stage or delete it")
    return problems


def check() -> int:
    problems = design_problems(load_roster(),
                               json.loads((ROOT / "harness" / "pipeline.json").read_text()))
    expected = expected_files()
    for path, content in expected.items():
        if not path.exists() or path.read_text() != content:
            problems.append(f"{path.relative_to(ROOT)} is stale: run harness/agents.py sync")
    for extra in set((OPENCODE_DIR / "agents").glob("*.md")) - set(expected):
        problems.append(f"{extra.relative_to(ROOT)} has no source agent: run harness/agents.py sync")
    for name in load_roster():
        if not eval_cases(name):
            problems.append(f"agent '{name}' has no eval cases: add harness/evals/agents/{name}.json")
    print("\n".join(problems) or "agents ok: design rules hold, opencode copies in sync, "
          "every agent has eval cases")
    return 1 if problems else 0


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "roster"
    if command == "sync":
        sync()
        return 0
    if command == "check":
        return check()
    if command == "roster":
        import argparse
        from backends import get_backend, parse_routes
        parser = argparse.ArgumentParser(prog="agents.py roster")
        parser.add_argument("--backend", default="claude")
        parser.add_argument("--route", action="append")
        parser.add_argument("--models", action="store_true",
                            help="one 'agent route model' line per agent (for preflight)")
        args = parser.parse_args(sys.argv[2:])
        backend = get_backend(args.backend, parse_routes(args.route))
        roster = snapshot(args.backend, backend.route)
        if args.models:
            for name, a in roster["agents"].items():
                print(name, a["route"], a["model"])
        else:
            print(json.dumps(roster, indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
