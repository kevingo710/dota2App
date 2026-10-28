#!/usr/bin/env python3
"""Telegram front-end for the harness: chat with the repo from your phone.

    harness/bot.py            # long-polls until Ctrl-C

Commands (only from the owner's private chat, TG_CHAT; everything else is ignored):
    <text> | /ship <text>   run harness/run.py with that request
    /continue <text>        same, starting from the last successful branch
    /local <text>           same pipeline on local models (opencode + Ollama)
    /hybrid <text>          a route per agent: Claude judges, local models build
    /status                 current job and last run
    /gate                   run harness/gate.sh on the current checkout
    /screen <name>          capture a screen (home|explore|superstar|settings|detail)
    /pr                     push the last successful branch and open a PR
    /cancel                 stop the running job
    /help

One job at a time. Messages that arrived while the bot was down are dropped
on start-up instead of replayed: a stale request should not touch the code.
Python standard library only.
"""

import json
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / ".harness" / "runs"
SCREENS = {"home", "explore", "superstar", "settings", "detail"}


def load_credentials() -> tuple[str, str]:
    """Same lookup order as scripts/telegram.sh: env, .env.local, ~/.config."""
    values = {k: os.environ.get(k, "") for k in ("TG_TOKEN", "TG_CHAT")}
    for file in (ROOT / ".env.local", Path.home() / ".config/dota2app/telegram.env"):
        if not file.exists():
            continue
        for line in file.read_text().splitlines():
            line = line.strip().removeprefix("export ").strip()
            key, sep, value = line.partition("=")
            if sep and key.strip() in values and not values[key.strip()]:
                values[key.strip()] = value.strip().strip("'\"")
    if not all(values.values()):
        sys.exit("TG_TOKEN / TG_CHAT not found (see docs/telegram.md)")
    return values["TG_TOKEN"], values["TG_CHAT"]


TOKEN, CHAT = load_credentials()
API = f"https://api.telegram.org/bot{TOKEN}"


def api(method: str, timeout: int = 30, **params) -> dict:
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"{API}/{method}", data=data, timeout=timeout) as resp:
        return json.load(resp)


def say(text: str) -> None:
    try:
        api("sendMessage", chat_id=CHAT, text=text[:4000])
    except OSError as exc:
        print(f"send failed: {exc}", file=sys.stderr)


def last_run(status: str | None = None) -> dict:
    for summary in sorted(RUNS.glob("*/summary.json"), reverse=True):
        data = json.loads(summary.read_text())
        if status is None or data.get("status") == status:
            return data
    return {}


class Jobs:
    def __init__(self):
        self.proc: subprocess.Popen | None = None
        self.label = ""
        self.started = 0.0

    def busy(self) -> bool:
        return self.proc is not None and self.proc.poll() is None

    def start(self, label: str, cmd: list[str], reply_output: bool = False) -> None:
        if self.busy():
            say(f"⏳ busy with: {self.label}. /status or /cancel")
            return
        log = (ROOT / ".harness" / "bot-job.log").open("w")
        self.proc = subprocess.Popen(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True)
        self.label, self.started = label, time.time()
        threading.Thread(target=self._watch, args=(self.proc, reply_output), daemon=True).start()

    def _watch(self, proc: subprocess.Popen, reply_output: bool) -> None:
        code = proc.wait()
        if reply_output or code not in (0, 1):
            tail = (ROOT / ".harness" / "bot-job.log").read_text()[-1500:]
            say(f"{'✅' if code == 0 else '❌'} {self.label} (exit {code})\n{tail}")

    def cancel(self) -> None:
        if not self.busy():
            say("nothing running")
            return
        os.killpg(self.proc.pid, signal.SIGTERM)
        say(f"🛑 cancelled: {self.label}")


JOBS = Jobs()


def ship(request: str, base: str | None = None, backend: str = "claude") -> None:
    if not request:
        say("usage: /ship <what to change>")
        return
    cmd = [sys.executable, "harness/run.py", request]
    if base:
        cmd += ["--base", base]
    cmd += ["--backend", backend]
    JOBS.start(f"ship ({backend}): {request}", cmd)
    say(f"👍 on it{f' (from {base})' if base else ''}. I'll send screenshots once every check passes.")


def open_pr() -> None:
    run = last_run("pass")
    if not run:
        say("no successful run to open a PR from")
        return
    report = RUNS / run["id"] / "report.md"
    # The summary is written by the agent: quote everything that reaches bash.
    q = shlex.quote
    script = (f"git push -u origin {q(run['branch'])} && "
              f"gh pr create --base {q(run.get('base') or 'master')} --head {q(run['branch'])} "
              f"--title {q(run['summary'])} --body-file {q(str(report))}")
    JOBS.start(f"pr: {run['branch']}", ["bash", "-c", script], reply_output=True)


def handle(text: str) -> None:
    command, _, rest = text.strip().partition(" ")
    rest = rest.strip()
    if command in {"/help", "/start"}:
        commands = __doc__.split("ignored):\n")[1].split("\n\n")[0]
        say("\n".join(line.strip() for line in commands.splitlines()))
    elif command == "/status":
        run = last_run()
        current = (f"running: {JOBS.label} ({(time.time() - JOBS.started) / 60:.1f} min)"
                   if JOBS.busy() else "idle")
        say(f"{current}\nlast run: {run.get('id', '-')} {run.get('status', '')}")
    elif command == "/cancel":
        JOBS.cancel()
    elif command == "/gate":
        JOBS.start("gate", ["harness/gate.sh"], reply_output=True)
    elif command == "/screen":
        if rest not in SCREENS:
            say(f"usage: /screen <{'|'.join(sorted(SCREENS))}>")
            return
        JOBS.start(f"screen {rest}", ["scripts/telegram.sh", "--screen", rest,
                                      "--caption", f"{rest} (current checkout)"])
    elif command == "/pr":
        open_pr()
    elif command == "/continue":
        ship(rest, base=last_run("pass").get("branch"))
    elif command == "/local":
        ship(rest, backend="opencode")
    elif command == "/hybrid":
        ship(rest, backend="hybrid")
    elif command == "/ship":
        ship(rest)
    elif command.startswith("/"):
        say("unknown command, try /help")
    else:
        ship(text.strip())


def main() -> None:
    (ROOT / ".harness").mkdir(exist_ok=True)
    pending = api("getUpdates", timeout=10, offset=-1).get("result", [])
    offset = pending[-1]["update_id"] + 1 if pending else None
    print(f"bot ready, chat {CHAT}; dropped {len(pending)} stale update(s)", flush=True)
    say("🤖 harness bot online. Send a change request or /help.")
    while True:
        try:
            params = {"timeout": 50, **({"offset": offset} if offset else {})}
            updates = api("getUpdates", timeout=60, **params).get("result", [])
        except OSError as exc:
            print(f"poll failed: {exc}; retrying", file=sys.stderr)
            time.sleep(5)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message") or {}
            chat = message.get("chat") or {}
            # Private chat with the owner only: in a group, any member could
            # otherwise make the agent edit code on this machine.
            if chat.get("type") != "private" or str(chat.get("id")) != CHAT:
                print(f"ignored message from chat {chat.get('id')}", flush=True)
                continue
            if message.get("text"):
                handle(message["text"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
