# Flow: Telegram → code change → screenshot (technical reference)

Reference documentation for the pipeline that lets a user ask, in natural
language over Telegram, for a change to this app, have the agent apply it with
`opencode`, capture the running iOS simulator, and send the photo back to the
same chat.

- **Machine**: macOS, Apple Silicon.
- **Agent harness**: OpenClaw 2026.10.5, gateway as a LaunchAgent (port 18789).
- **Model**: `ollama/qwen3-agent:latest` (local, 8B) served by Ollama.
- **App under change**: this repo (React Native 0.87, bundle id
  `org.reactjs.native.example.dota2App`).
- **Simulator**: iPhone 18 Pro, iOS 27, Metro on `:8081`.
- **Telegram**: a private bot, user/chat id `<CHAT_ID>` (kept in the local credentials file, never in the repo),
  session key `agent:main:telegram:direct:<CHAT_ID>`.

For the user-facing capture helper see [telegram.md](./telegram.md); this
document covers the OpenClaw configuration that makes the end-to-end flow work.

## 1. Flow overview

```
Telegram message
      │  (Bot API getUpdates / webhook)
      ▼
OpenClaw gateway ── prompt assembly ──► Ollama (qwen3-agent)
      │                                      │
      │  tool calls                          │ native tools
      ▼                                      ▼
   exec (gateway host)  ──►  opencode  ──►  edit files in dota2App
      │
      ▼
   skills/dota2-change/scripts/capture.sh  ──►  /tmp/openclaw/dota2-change.png
      │
      ▼
   openclaw message send --channel telegram --media …  ──►  Telegram chat
```

The model never calls the `message` tool itself. It shells out to the OpenClaw
CLI to send the photo, because the `message` tool has no live channel context
inside this tool-execution path (see failure 4).

## 2. Configuration

All of this lives in `~/.openclaw/openclaw.json`.

### 2.1 Session scoping

```json
"session": { "dmScope": "per-channel-peer" }
```

Each DM peer gets its own session, so history is not shared across chats.

### 2.2 Tools

```json
"tools": {
  "profile": "minimal",
  "toolSearch": false,
  "exec": { "host": "gateway", "security": "full", "ask": "off" },
  "alsoAllow": ["exec", "read", "edit", "apply_patch"]
}
```

Key decisions:

| Setting | Value | Why |
| --- | --- | --- |
| `profile` | `minimal` | Fewer tools in-context; the 8B model picks the right one more reliably. |
| `toolSearch` | `false` | With it on, tools such as `message` are moved to a "Deferred Tool Schemas" section; the model silently returns an empty response instead of calling them. |
| `exec.host` | `gateway` | Channel-origin `exec` otherwise routes to a paired node, which is not where the repo/simulator live. |
| `exec.security` | `full` | The capture script needs to drive `xcrun`/`openclaw` without sandbox denials. |
| `exec.ask` | `off` | Non-interactive; there is no prompt loop over Telegram. |
| `alsoAllow` | `exec, read, edit, apply_patch` | Exactly the tools the flow needs. No `process`, no `message`. |

Two tools are **deliberately excluded**:

- **`process`** — when present, `exec` backgrounds long-running commands and
  hands back a job id. The model does not wait for completion and instead polls
  a pid that is not the process name it recorded, producing "No session found".
  Removing it makes `exec` run synchronously; the long build is bounded by
  `yieldMs`/`timeoutSeconds` instead.
- **`message`** — fails with `Action send requires a target` because there is no
  live channel binding in this execution path. The flow sends media via the
  shell instead (see §3, step 3).

### 2.3 Model parameters

```json
"params": { "thinking": false }
```

Thinking must stay off for this model; with it enabled the responses come back
empty.

## 3. The instruction (AGENTS.md)

`~/.openclaw/workspace/AGENTS.md` is injected into the system prompt (verified:
the real prompt is ~29.8k chars and contains the flow). The `## Tools` section
defines a fixed 3-step procedure:

1. **Apply the change** with `opencode`:

   ```sh
   exec pty opencode  # yieldMs: 600000, timeoutSeconds: 900
   ```

   The high `yieldMs` is what keeps the call synchronous now that `process` is
   gone: the gateway waits up to 10 minutes for the build to finish.

2. **Capture** to an allowed media root:

   ```sh
   skills/dota2-change/scripts/capture.sh
   # default OUT=/tmp/openclaw/dota2-change.png
   ```

   Media must be written under `/tmp/openclaw/`; OpenClaw rejects files outside
   its allowed roots with `LocalMediaAccessError`.

3. **Send** with the CLI (not the `message` tool):

   ```sh
   openclaw message send \
     --channel telegram --target <CHAT_ID> \
     --media /tmp/openclaw/dota2-change.png \
     --message "<caption>"
   ```

   Verified working: the gateway logs `operation=sendPhoto deliveryKind=photo`.

The instruction also **forbids**:

- Emitting a `.MEDIA:` string in the response instead of sending a real photo.
- Using the `message` tool.
- Asking the user for their chat id (it is fixed).

The user-facing instruction is intentionally generic ("change the Home tab to
X and send me a screenshot") — all technical detail stays in the workspace, not
in the Telegram message.

## 4. Failure catalogue

Every blocker in getting this flow stable was harness/config, not model
reasoning. In order of discovery:

| # | Symptom | Root cause | Fix |
| --- | --- | --- | --- |
| 1 | `exec` ran on the wrong machine | Channel-origin `exec` routed to a paired node | `tools.exec.host: "gateway"` |
| 2 | Empty model response | `toolSearch` hid `message` under "Deferred Tool Schemas" | `tools.toolSearch: false` |
| 3 | "No session found" | `process` tool made `exec` background the build; model polled the wrong id | Remove `process`; `exec` runs synchronously with high `yieldMs` |
| 4 | `Action send requires a target` | `message` tool has no live channel context on this path | Send via shell `openclaw message send`; drop `message` from `alsoAllow` |
| 5 | `LocalMediaAccessError` | `/tmp/x.png` outside allowed media roots | Capture into `/tmp/openclaw/` |
| 6 | Stale screenshot | Capture fired before Metro rebuilt / app re-rendered | `WAIT_SECONDS` 18 → 30 and `sleep 2` before relaunch (commit `0c55c4e`) |

## 5. Token cost

Measured from `/tmp/openclaw/openclaw-2026-10-21.log`:

- **Prompt tokens per turn**: ~7.9k–10.8k typical; peaks of 18.8k and
  ~24.7k–26.7k when context is compacted
  (`estimatedPromptTokens=24738…` vs `promptBudgetBeforeReserve=24576`).
- The fixed system prompt (~29.8k chars ≈ 7.5k tokens) dominates every turn
  even for a one-line user message. `AGENTS.md` alone is ~8.3k chars
  (~2k tokens).
- **Prompt-cache churn**: the log shows repeated `cache read dropped`
  (`5093 -> 0`, `10273 -> 106`, `11754 -> 89`). Each time the system-prompt
  digest changes (sections *Skills*, *Tooling*, *Other*, *Project Context*) the
  cache is invalidated and the full prompt is paid again.

Practical levers: keep `AGENTS.md`/skills small and stable, avoid editing them
mid-session, and keep `profile: minimal`.

## 6. Diagnosis tricks

- **Trajectory exports** redact oversized system prompts
  ("Oversized diagnostic JSON redacted"):
  `openclaw sessions export-trajectory --session-key <key> --output <name>`
  writes to `<cwd>/.openclaw/trajectory-exports/<name>/`.
- **See the real prompt**: point `models.providers.ollama.baseUrl` at a logging
  proxy (e.g. `/tmp/opencode/ollama_proxy.py`) and inspect the outgoing request.

## 7. Key paths

| Path | Purpose |
| --- | --- |
| `~/.openclaw/openclaw.json` | Harness config (tools, session, model). |
| `~/.openclaw/workspace/AGENTS.md` | Injected flow instructions. |
| `~/.openclaw/workspace/skills/dota2-change/SKILL.md` | Skill definition. |
| `~/.openclaw/workspace/skills/dota2-change/scripts/capture.sh` | Relaunch + screenshot. |
| `/tmp/openclaw/dota2-change.png` | Capture output (allowed media root). |
| `/tmp/openclaw/openclaw-2026-10-21.log` | Gateway log (check `operation=sendPhoto`). |

## See also

- [openclaw-telegram-flow.blog.md](./openclaw-telegram-flow.blog.md) — narrative
  version.
- [alternatives.md](./alternatives.md) — OpenClaw vs. a direct Telegram Bot
  API integration.
- [telegram.md](./telegram.md) — the repo-local capture helper.
