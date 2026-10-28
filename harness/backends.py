"""Agent backends behind one interface, so the harness and the evals do not
care whether an agent runs on Claude (cloud) or opencode + Ollama (local).

    backend = get_backend("opencode")
    result = backend.run("Change request: ...", cwd=ROOT, agent="planner")
    plan = extract_json(result.text)

A route says where one agent runs:

    claude                 Claude Code, model from the agent's frontmatter
    claude:<model>         Claude Code with --model (sonnet, opus, haiku, ...)
    opencode               opencode, model from the generated .opencode agent
    <provider>/<model>     opencode with -m, e.g. ollama/gpt-oss-agent:latest

The `hybrid` backend (harness/backends.json) is a table of routes, one per
agent: each role goes to the cheapest model that passes its evals.
`--route agent=<route>` overrides one entry on any backend, which is how a
candidate model is measured for one role without touching the others.
"""

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT = 45 * 60


@dataclass
class AgentResult:
    text: str = ""
    session: str | None = None
    turns: int = 0
    tokens: int = 0
    cost_usd: float = 0.0
    seconds: float = 0.0
    error: str = ""
    raw: str = field(default="", repr=False)

    @property
    def ok(self) -> bool:
        return not self.error


def extract_json(text: str) -> dict | None:
    """The last ```json block in an agent's answer, or the last bare object."""
    blocks = re.findall(r"```(?:json)?\s*\n(.*?)```", text, re.S)
    candidates = blocks[::-1] or []
    # Small models often forget the fence: fall back to the last {...} span.
    start = text.rfind("\n{") + 1 if "\n{" in text else text.find("{")
    if start >= 0:
        candidates.append(text[start:text.rfind("}") + 1])
    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


class Backend:
    name = "base"

    def run(self, prompt: str, cwd: Path = ROOT, agent: str | None = None,
            session: str | None = None, env: dict | None = None,
            log: Path | None = None, max_turns: int = 120,
            timeout: int = TIMEOUT) -> AgentResult:
        cmd = self.command(prompt, cwd, agent, session, max_turns)
        started = time.time()
        try:
            proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                                  env=env, timeout=timeout)
        except subprocess.TimeoutExpired:
            return AgentResult(error=f"timed out after {timeout // 60} min",
                               seconds=time.time() - started)
        if log:
            log.write_text(proc.stdout + ("\n--- stderr ---\n" + proc.stderr if proc.stderr else ""))
        result = self.parse(proc.stdout)
        result.raw = proc.stdout
        result.seconds = result.seconds or time.time() - started
        # An agent may legitimately end on a tool call with no closing text
        # (an implementer that just edits files): only a non-zero exit with
        # no answer is an error.
        if proc.returncode != 0 and not result.text and not result.error:
            result.error = (proc.stderr or proc.stdout or "no output")[-1500:]
        return result

    def command(self, prompt, cwd, agent, session, max_turns) -> list[str]:
        raise NotImplementedError

    def parse(self, stdout: str) -> AgentResult:
        raise NotImplementedError


class ClaudeBackend(Backend):
    """Claude Code headless. Agents run as the main session (`--agent`)."""

    name = "claude"

    def __init__(self, model: str | None = None):
        self.model = model

    def command(self, prompt, cwd, agent, session, max_turns):
        # Passed explicitly: in an untrusted checkout (fresh clone, eval
        # sandbox) project settings are ignored and every check would be denied.
        settings = json.loads((ROOT / ".claude/settings.json").read_text())
        cmd = ["claude", "-p", prompt, "--output-format", "json",
               "--permission-mode", "acceptEdits", "--max-turns", str(max_turns),
               "--allowedTools", *settings["permissions"]["allow"]]
        if agent:
            cmd += ["--agent", agent]
        if self.model:
            cmd += ["--model", self.model]
        if session:
            cmd += ["--resume", session]
        return cmd

    def parse(self, stdout):
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return AgentResult(error=stdout[-1500:] or "no JSON from claude")
        usage = data.get("usage") or {}
        error = ""
        if data.get("is_error") and data.get("subtype") != "error_max_turns":
            error = str(data.get("result", data.get("subtype")))[-1500:]
        return AgentResult(
            text=data.get("result") or "", session=data.get("session_id"),
            turns=data.get("num_turns", 0), cost_usd=data.get("total_cost_usd", 0.0),
            tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            + usage.get("cache_read_input_tokens", 0),
            seconds=data.get("duration_ms", 0) / 1000, error=error,
        )


class OpenCodeBackend(Backend):
    """opencode + Ollama. Model per agent comes from the generated
    .opencode/agents/<name>.md (see harness/backends.json)."""

    name = "opencode"

    def __init__(self, model: str | None = None):
        self.model = model

    def command(self, prompt, cwd, agent, session, max_turns):
        cmd = ["opencode", "run", "--format", "json", "--dir", str(cwd)]
        if agent:
            cmd += ["--agent", agent]
        # -m beats the agent file's model; the prompt, tools and permissions
        # still come from the generated agent.
        model = self.model or (None if agent else CONFIG["opencode"]["default_model"])
        if model:
            cmd += ["-m", model]
        if session:
            cmd += ["--session", session]
        return cmd + [prompt]

    def parse(self, stdout):
        result = AgentResult()
        texts, errors = [], []
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            part = event.get("part") or {}
            result.session = event.get("sessionID", result.session)
            kind = event.get("type")
            if kind == "text" and part.get("text"):
                texts.append(part["text"])
            elif kind == "step_finish":
                result.turns += 1
                result.tokens += (part.get("tokens") or {}).get("total", 0)
                result.cost_usd += part.get("cost") or 0.0
            elif kind == "error":
                errors.append(json.dumps(event.get("error") or event)[:500])
        result.text = "\n".join(texts)
        result.error = "" if texts else "\n".join(errors)
        if not result.turns and not result.error:
            result.error = "no output: opencode never reached the model"
        return result


def resolve(route: str) -> Backend:
    if route == "claude" or route.startswith("claude:"):
        return ClaudeBackend(route.partition(":")[2] or None)
    if route == "opencode":
        return OpenCodeBackend()
    if "/" in route:
        return OpenCodeBackend(route)
    raise SystemExit(f"bad route '{route}' (claude, claude:<model>, opencode, <provider>/<model>)")


class Router(Backend):
    """Sends each agent to its own route. Unlisted agents take `default`.

    `escalation` is a stronger route per agent for when the first one is not
    enough: the pipeline asks for it once a fix iteration has failed on the
    cheap route (harness/pipeline.py, `escalate_after`)."""

    def __init__(self, name: str, default: str, routes: dict[str, str],
                 escalation: dict[str, str] | None = None, escalate_after: int | None = None):
        self.name, self.default, self.routes = name, default, routes
        self.escalation, self.escalate_after = escalation or {}, escalate_after

    def route(self, agent: str | None, escalated: bool = False) -> str:
        if escalated and agent in self.escalation:
            return self.escalation[agent]
        return self.routes.get(agent or "", self.default)

    def run(self, prompt, cwd=ROOT, agent=None, session=None, escalated=False,
            **kwargs) -> AgentResult:
        return resolve(self.route(agent, escalated)).run(prompt, cwd=cwd, agent=agent,
                                                         session=session, **kwargs)


CONFIG = json.loads((ROOT / "harness" / "backends.json").read_text())
BACKENDS = ["claude", "opencode", "hybrid"]


def parse_routes(pairs: list[str] | None) -> dict[str, str]:
    """`--route reviewer=claude --route planner=ollama/x` -> {agent: route}."""
    routes = {}
    for pair in pairs or []:
        agent, sep, route = pair.partition("=")
        if not sep or not route:
            raise SystemExit(f"--route expects agent=<route>, got '{pair}'")
        resolve(route)
        routes[agent] = route
    return routes


def get_backend(name: str, overrides: dict[str, str] | None = None) -> Router:
    if name not in BACKENDS:
        raise SystemExit(f"unknown backend '{name}' (choose: {', '.join(BACKENDS)})")
    if name != "hybrid":
        return Router(name, name, dict(overrides or {}))
    cfg = CONFIG[name]
    return Router(name, cfg["default"], {**cfg.get("routes", {}), **(overrides or {})},
                  cfg.get("escalation"), cfg.get("escalate_after"))
