#!/usr/bin/env bash
# Prepare the local (no cloud) backend: Ollama models with agent-sized context.
# Usage: harness/local/setup.sh [--candidates]
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
command -v ollama >/dev/null || { echo "install Ollama: https://ollama.com" >&2; exit 1; }
command -v opencode >/dev/null || { echo "install opencode: brew install sst/tap/opencode" >&2; exit 1; }
ollama pull qwen3:8b
ollama pull gemma4:12b
ollama create qwen3-agent -f qwen3-agent.Modelfile
ollama create gemma4-agent -f gemma4-agent.Modelfile
# Optional candidates measured by `harness/eval.py matrix` (docs/hybrid.md).
if [[ "${1:-}" == --candidates ]]; then
  ollama pull gpt-oss:20b
  ollama pull qwen3:14b
  ollama create gpt-oss-agent -f gpt-oss-agent.Modelfile
  ollama create qwen3-14b-agent -f qwen3-14b-agent.Modelfile
fi
echo "ready: opencode models ollama/qwen3-agent:latest, ollama/gemma4-agent:latest"
