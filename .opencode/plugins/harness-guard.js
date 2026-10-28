// Ports the Claude Code hooks to opencode so both backends run under the same
// guardrails. It does not reimplement them: it calls the very same scripts in
// .claude/hooks/ with the event shape they expect.
//
//   tool.execute.before -> guard.py         (exit 2 = block the tool call)
//   tool.execute.after  -> lint_changed.py  (problems appended to the tool
//                                            output, so the model sees them)
//                       -> record_command.py (bash: input for harness/retro.py)
//
// opencode has no Stop hook; harness/run.py re-runs the gate after every agent
// run instead, which is backend-independent anyway.
import { spawnSync } from "node:child_process";

const TOOL_NAMES = { bash: "Bash", read: "Read", edit: "Edit", write: "Write", patch: "Edit" };

const callHook = (directory, script, event) =>
  spawnSync("python3", [`${directory}/.claude/hooks/${script}`], {
    input: JSON.stringify(event),
    env: { ...process.env, CLAUDE_PROJECT_DIR: directory },
    encoding: "utf8",
  });

const toolInput = (args = {}) => ({
  command: args.command,
  file_path: args.filePath ?? args.file_path ?? args.path,
});

export const HarnessGuard = async ({ directory }) => ({
  "tool.execute.before": async (input, output) => {
    const tool = TOOL_NAMES[input.tool];
    if (!tool) return;
    const result = callHook(directory, "guard.py", { tool_name: tool, tool_input: toolInput(output.args) });
    if (result.status === 2) throw new Error(result.stderr.trim());
  },
  "tool.execute.after": async (input, output) => {
    if (input.tool === "bash") {
      callHook(directory, "record_command.py", { tool_name: "Bash", tool_input: toolInput(input.args) });
      return;
    }
    if (!["edit", "write", "patch"].includes(input.tool)) return;
    const result = callHook(directory, "lint_changed.py", { tool_input: toolInput(input.args) });
    if (result.status === 2) output.output = `${output.output ?? ""}\n\n${result.stderr.trim()}`;
  },
});
