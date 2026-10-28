# Alternatives: OpenClaw vs. a direct Telegram Bot API integration

Evaluation of replacing OpenClaw with a hand-rolled bot that talks to the
Telegram Bot API directly and drives `opencode` + the capture script itself.

Scope: one flow (chat → code change → screenshot → photo back). Not a general
agent platform comparison.

## TL;DR

| | OpenClaw | Direct Telegram Bot API |
| --- | --- | --- |
| Moving parts | Gateway + node model + sessions + skills + tools | One process: long-poll + call `opencode` + send photo |
| Failure surface | High — most of §4 in the technical doc was harness config | Low — no tool routing, no schema deferral, no session model |
| Model quality needed | Higher; 8B needed heavy config tuning | Lower; the bot only needs to shell out and reply |
| Cost per turn | ~8k–11k prompt tokens (system prompt dominates) | Near-zero prompt tokens if the bot does not call an LLM at all |
| Agent loop / planning | Built in | You write it |
| Memory across messages | Built in | You write it |
| Multi-channel | Built in | Telegram only |
| Tool ecosystem | Built in | You write it |
| Time to working prototype | Days of config debugging | An afternoon |

For exactly this one flow, a direct bot is **simpler, cheaper and easier to
debug**. OpenClaw earns its complexity only once you want more than one flow,
more than one channel, or genuine multi-step planning.

## What "direct" looks like

The minimal viable version does not even need an LLM:

```python
import subprocess, requests

TOKEN, CHAT = open("/Users/…/.config/dota2app/telegram.env").read().split()
API = f"https://api.telegram.org/bot{TOKEN}"

offset = None
while True:
    r = requests.get(f"{API}/getUpdates", params={"offset": offset, "timeout": 30}).json()
    for u in r["result"]:
        offset = u["update_id"] + 1
        msg = u.get("message", {}).get("text", "")
        if not msg:
            continue
        requests.post(f"{API}/sendMessage", data={"chat_id": CHAT, "text": "on it…"})
        subprocess.run(["opencode", "run", msg], cwd=REPO, check=True)
        subprocess.run(["scripts/capture.sh"], cwd=REPO, check=True)
        with open("/tmp/openclaw/dota2-change.png", "rb") as f:
            requests.post(f"{API}/sendPhoto", data={"chat_id": CHAT}, files={"photo": f})
```

That is the entire supervisor. No gateway, no tool profiles, no deferred-schema
behaviour, no session scoping — because there is nothing to route.

### Optional: add a model for intent

If you want the message interpreted rather than executed verbatim, insert one
LLM call between the message and `opencode`:

```python
instruction = llm(f"Turn this request into an opencode prompt: {msg}")
```

This is where the cost moves: now you pay prompt tokens too, but you control the
prompt exactly (e.g. a 200-token system message, not 7,500).

## Where each option wins

### Direct Bot API wins when

- You have **one** flow and want it to be **boring**.
- You want to **debug** with `print()` and a single log file.
- You want **zero** per-turn overhead (or a tiny, controlled prompt).
- You do not need the agent to decide *which* tools to use — you already know the
  steps.
- You want to avoid the entire class of failures in the technical doc's §4:
  node routing, tool search, backgrounding, media roots.

### OpenClaw wins when

- You want **more than one** flow (change code, run tests, deploy, query a DB…)
  and want one place to describe them.
- You want **multi-step autonomy** — the model plans, retries, chooses tools.
- You want **multiple channels** (Telegram + Slack + CLI) sharing the same agent.
- You want **memory/conversation state** and session scoping for free.
- You value the **skill/tool ecosystem** over writing plumbing yourself.

## Migration sketch (if you switch)

1. Keep the two *useful* artifacts unchanged: the `opencode` invocation and
   `skills/dota2-change/scripts/capture.sh`. Neither depends on OpenClaw.
2. Replace `openclaw message send` with `POST /sendPhoto` against the Bot API
   (the repo already does exactly this in `scripts/telegram.sh`).
3. Replace the Telegram channel with a long-poll loop (or a webhook if you have
   a public endpoint).
4. Add only the pieces you actually need: a whitelist of allowed commands, a
   per-chat lock so two requests do not race, and a timeout around the build.
5. Drop `AGENTS.md`, the skill manifest and the OpenClaw config once the loop is
   self-contained.

## Recommendation

Given the current state — a single flow, a local 8B model, and a history of bugs
that were *all* harness configuration — a **direct Bot API bot is the better
default for this specific use case**. It removes the layer that produced almost
every failure, and it makes the loop cheap enough to run without thinking about
token budgets.

Keep OpenClaw in reserve for when the scope grows: the moment you want the agent
to decide what to do, or to run the same brain over several channels, the
hand-rolled bot starts to reinvent the harness — and then the harness is worth
its complexity.

The pragmatic path: build the direct bot now (an afternoon), keep the capture
script and the `opencode` step as the shared core, and treat OpenClaw as the
upgrade you reach for when one flow becomes many.

## Update: what was built

The direct approach won. `harness/bot.py` is that bot (standard library only,
owner-only chat, backlog dropped on start-up), driving `harness/run.py`
instead of a single `opencode` call. The agent loop that OpenClaw provided is
now `harness/pipeline.py` plus the `/ship` skill, and the evals measure it
([agentic-harness.md](./agentic-harness.md), [benchmarks.md](./benchmarks.md)).

## See also

- [openclaw-telegram-flow.technical.md](./openclaw-telegram-flow.technical.md)
- [openclaw-telegram-flow.blog.md](./openclaw-telegram-flow.blog.md)
- [telegram.md](./telegram.md) — the repo's existing `curl -F` send path.
- https://core.telegram.org/bots/api
