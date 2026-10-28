# I asked my phone to change my app, and it sent me back a screenshot

*How to wire a chat bot, a code editor and an iOS simulator into a loop you can
run from Telegram — and what actually broke along the way.*

---

There is a small React Native app on my laptop that lists the 127 Dota 2 heroes.
Nothing fancy. But I wanted a silly thing: to open Telegram, type *"rename the
Home tab to HEROES and send me a screenshot"*, and get a photo back of the app
with the change already rendered.

No IDE. No terminal. Just a chat window and a photo.

This is the story of getting that working — and, more honestly, of the six
things that stood between "the pieces exist" and "the loop works every time."

## The cast

Three moving parts, all on one Mac:

1. **OpenClaw** — an agent harness. You give it a model and a set of tools, and
   it runs an instruction loop. Telegram is one of its channels.
2. **A local model** — `qwen3-agent`, an 8B model served by Ollama. Small,
   fast, and running entirely offline. No API keys, no cloud bill.
3. **A skill script** — a little shell script that relaunches the app on the
   iOS simulator and takes a screenshot.

The app is the Dota 2 hero browser in this repo. The Telegram side is a bot I
made in two minutes with [@BotFather](https://t.me/botfather).

The promise of the setup: the model reads my Telegram message, edits the app
with `opencode`, runs the capture script, and sends the photo back. All I see is
the photo.

## Why not just ask a cloud model?

Because the whole point was to keep it local. An 8B model on my own machine
costs nothing per token and nothing leaves the laptop. The trade-off is that an
8B model is far less forgiving: it does not recover gracefully from a confusing
tool list or an ambiguous error. Most of the debugging below was really about
making the *harness* so clean that a small model could not get lost.

## The six failures

**1. The command ran on the wrong machine.**
The agent has a notion of a "gateway" (the headless service) and "nodes" (things
it can drive). A command coming in from a chat channel was routed to a node —
which is not where the repo or the simulator live. Fix: pin command execution to
the gateway host.

**2. The model went silent.**
For a while, every reply was empty. Not an error — just nothing. It turned out
the harness had a feature that hides less-used tools behind a "deferred
schemas" section, to save context. The model saw a tool *mentioned* but not
fully described, tried to use it, and produced nothing. Turning that feature off
fixed it. Lesson: a small model needs its tools fully visible.

**3. "No session found."**
Big clue, this one. The tool that runs shell commands had a companion tool for
managing long-running processes. When that companion was available, the agent
would launch the build in the *background*, immediately "forget" it had done
so, and then look for the running job under a name that did not match. The fix
was counter-intuitive: **remove** the ability to manage background processes, so
the build runs synchronously and the agent simply waits. Sometimes less power is
more reliability.

**4. The photo refused to send.**
The cleanest-looking option — call the harness's built-in "send a message" tool
— failed with a confusing *"send requires a target"*. In this execution path
there was no live chat binding for the tool to use. The fix was to stop being
clever and shell out to the harness's own command-line send command, which had
no such problem. Verified in the logs as a real `sendPhoto`.

**5. The screenshot was rejected.**
Even once we were *producing* a PNG, the harness refused to touch a file in
`/tmp`. It only reads media from a few allowed folders, and `/tmp/x.png` was not
one of them. Moving the capture to an allowed location fixed it.

**6. The screenshot was stale.**
The nastiest bug, because it was intermittent and it *looked* like success. The
capture ran before Metro (the JS bundler) had rebuilt and before the app had
re-rendered, so I got a perfectly good photo of the *previous* version of the
screen. The fix was unglamorous: wait longer, and give the bundler a moment
before relaunching. Bumping a wait from 18 seconds to 30, plus a two-second
pause, did it.

## The shape of the solution

The working loop is deliberately boring:

1. Edit the app with the code editor tool.
2. Run the capture script, writing to an allowed folder.
3. Send the PNG with the harness's own command-line send command.

The instruction that the model follows is written down once, in the harness
workspace, so I never have to explain it in the chat. My Telegram message stays
natural: *"rename the tab and send me a screenshot."* Everything technical —
paths, tool names, which command to use — lives in the instruction file, not in
my message.

That split is the real design decision. The chat is for intent. The config is
for mechanics.

## What it actually costs

Running locally, the money cost is zero. The cost that matters is context. Even
when my message is one line, every turn carries a system prompt of roughly 7,500
tokens — the instruction file, the skill definitions, the tool schemas — so a
typical turn is 8,000 to 11,000 prompt tokens, with spikes near 27,000 when the
harness compacts the conversation. There is also measurable "cache churn": every
time the system prompt changes, the cached prefix is thrown away and paid for
again. Keeping that instruction file small and *stable* is not a nicety; it is
the main way to keep the loop cheap.

## What I would tell my past self

- **Every bug here was configuration, not intelligence.** The 8B model was fine.
  The harness's defaults were built for a bigger, smarter model that can shrug
  off ambiguity. A small model cannot, so you remove the ambiguity.
- **Fewer tools, fewer failures.** Half the fixes were *removing* capabilities.
- **Verify with evidence, not vibes.** The moment I started reading the real
  gateway logs (`operation=sendPhoto`) and OCR-ing the screenshot to confirm the
  expected text was on screen, debugging went from guessing to knowing.
- **Send the artifact, always.** The magic is not the text reply. It is the
  photo. Any instruction that ends in words instead of the image is a bug.

## Where this is going

The obvious next questions are: do I even need the harness? Could I just talk to
Telegram's Bot API directly, skip the middle layer, and keep the loop simpler
and cheaper? I explored that in
[alternatives.md](./alternatives.md) — the short version is that a direct bot
buys you simplicity and control at the cost of the agent loop, memory and
multi-channel plumbing that the harness already gives you. Worth it for exactly
one flow; probably not worth it once you want more than one.

Either way, the lesson stands: the interesting engineering was not the model. It
was clearing every stumbling block between a sentence in a chat and a picture
on my phone.
