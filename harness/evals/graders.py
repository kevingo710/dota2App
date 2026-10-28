"""Deterministic graders for agent evals.

Each grader takes the grading context and its own spec from the case JSON and
returns (passed, detail). No grader asks a model for its opinion: agent output
is judged by JSON contracts, git diffs, the quality gate and mutation tests.
"""

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

GRADERS = {}


@dataclass
class Context:
    sandbox: Path
    output: dict | None      # the agent's final JSON block, if any
    text: str                # the agent's full final answer
    baseline: str            # working-tree fingerprint right after setup


def grader(fn):
    GRADERS[fn.__name__] = fn
    return fn


def sh(ctx: Context, *cmd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=ctx.sandbox, capture_output=True, text=True)


def changed_files(ctx: Context) -> list[str]:
    tracked = sh(ctx, "git", "diff", "--name-only", "HEAD").stdout.split()
    untracked = sh(ctx, "git", "ls-files", "--others", "--exclude-standard").stdout.split()
    return sorted(set(tracked + untracked))


def tree_fingerprint(sandbox: Path) -> str:
    ctx = Context(sandbox, None, "", "")
    diff = sh(ctx, "git", "diff", "HEAD").stdout
    untracked = sh(ctx, "git", "ls-files", "--others", "--exclude-standard").stdout
    return hashlib.sha256((diff + untracked).encode()).hexdigest()


def lookup(data, path: str):
    for key in path.split(".") if path else []:
        if isinstance(data, dict):
            data = data.get(key)
        else:
            return None
    return data


def needs_json(fn):
    def wrapper(ctx: Context, spec: dict):
        if ctx.output is None:
            return False, "no JSON block in the answer"
        return fn(ctx, spec)
    wrapper.__name__ = fn.__name__
    return wrapper


# --- output contract ---------------------------------------------------------

@grader
@needs_json
def json_keys(ctx, spec):
    missing = [k for k in spec["keys"] if k not in ctx.output]
    return not missing, f"missing keys {missing}" if missing else ""


@grader
@needs_json
def json_equals(ctx, spec):
    value = lookup(ctx.output, spec["path"])
    return value == spec["value"], f"{spec['path']} = {json.dumps(value)[:120]}"


@grader
@needs_json
def json_contains(ctx, spec):
    value = lookup(ctx.output, spec["path"]) or []
    found = spec["value"] in value if isinstance(value, (list, str)) else False
    return found, f"{spec['path']} = {json.dumps(value)[:160]}"


@grader
@needs_json
def json_subset(ctx, spec):
    value = lookup(ctx.output, spec["path"]) or []
    extra = [v for v in value if v not in spec["allowed"]]
    return not extra, f"unexpected {extra}" if extra else ""


@grader
@needs_json
def json_regex(ctx, spec):
    value = json.dumps(lookup(ctx.output, spec["path"]))
    return bool(re.search(spec["regex"], value)), f"{spec['path']} = {value[:200]}"


@grader
@needs_json
def json_len_gte(ctx, spec):
    value = lookup(ctx.output, spec["path"]) or []
    return len(value) >= spec["min"], f"len({spec['path']}) = {len(value)}"


@grader
@needs_json
def json_len_lte(ctx, spec):
    value = lookup(ctx.output, spec["path"]) or []
    return len(value) <= spec["max"], f"len({spec['path']}) = {len(value)}"


# --- effects on the repository -----------------------------------------------

@grader
def unchanged(ctx, spec):
    """Read-only agents must leave the tree exactly as the setup left it."""
    same = tree_fingerprint(ctx.sandbox) == ctx.baseline
    return same, "" if same else f"modified: {changed_files(ctx)}"


@grader
def changed_include(ctx, spec):
    changed = changed_files(ctx)
    missing = [f for f in spec["files"] if f not in changed]
    return not missing, f"not changed: {missing}; changed: {changed}" if missing else ""


@grader
def changed_within(ctx, spec):
    """Only the listed files (or directories ending in /) may change."""
    allowed = spec["files"]
    extra = [f for f in changed_files(ctx)
             if not any(f == a or (a.endswith("/") and f.startswith(a)) for a in allowed)]
    return not extra, f"out of scope: {extra}" if extra else ""


@grader
def diff_regex(ctx, spec):
    """Regex over the added lines of one file (absent: true inverts it)."""
    path = ctx.sandbox / spec["file"]
    tracked = sh(ctx, "git", "ls-files", "--error-unmatch", spec["file"]).returncode == 0
    if tracked:
        diff = sh(ctx, "git", "diff", "HEAD", "--", spec["file"]).stdout
        added = "\n".join(l[1:] for l in diff.splitlines() if l.startswith("+") and not l.startswith("+++"))
    else:
        added = path.read_text() if path.exists() else ""
    found = bool(re.search(spec["regex"], added))
    want = not spec.get("absent", False)
    verb = "found" if found else "not found"
    return found == want, f"/{spec['regex']}/ {verb} in added lines of {spec['file']}"


@grader
def gate(ctx, spec):
    proc = sh(ctx, "harness/gate.sh", "--quiet")
    return proc.returncode == 0, proc.stdout[-600:] if proc.returncode else ""


@grader
def tests_pass(ctx, spec):
    proc = sh(ctx, "npx", "jest", "--ci", "--silent")
    return proc.returncode == 0, (proc.stdout + proc.stderr)[-600:] if proc.returncode else ""


@grader
def mutation_killed(ctx, spec):
    """Break the production code on purpose; the new tests must notice."""
    originals = {}
    try:
        for edit in spec["edits"]:
            path = ctx.sandbox / edit["file"]
            originals.setdefault(path, path.read_text())
            source = path.read_text()
            if edit["old"] not in source:
                return False, f"mutation anchor not found in {edit['file']} (agent changed it?)"
            path.write_text(source.replace(edit["old"], edit["new"], 1))
        tests = [f for f in changed_files(ctx) if f.startswith("__tests__/")]
        if not tests:
            return False, "no test files changed"
        proc = sh(ctx, "npx", "jest", "--ci", "--silent", *tests)
        return proc.returncode != 0, "mutant survived: tests still pass" if proc.returncode == 0 else "mutant killed"
    finally:
        for path, text in originals.items():
            path.write_text(text)


def grade(ctx: Context, specs: list[dict]) -> list[dict]:
    results = []
    for spec in specs:
        fn = GRADERS.get(spec["type"])
        if fn is None:
            results.append({"type": spec["type"], "pass": False, "detail": "unknown grader"})
            continue
        try:
            passed, detail = fn(ctx, spec)
        except Exception as exc:  # a broken grader must not crash the whole eval
            passed, detail = False, f"grader error: {exc}"
        results.append({"type": spec["type"], "pass": bool(passed), "detail": detail})
    return results
