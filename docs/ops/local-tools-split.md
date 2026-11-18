# Local tools split (T-0093)

**Status:** Active  
**Related:** ADR-0011 · ADR-0012 · T-0080 · T-0092 · [worker-monitor.md](worker-monitor.md)

## Problem

Many Ollama coding tags (notably **`deepseek-coder:6.7b`**) answer chat completions fine but **reject tool schemas**:

```text
Error: registry.ollama.ai/library/deepseek-coder:6.7b does not support tools
```

OpenCode **agent** mode needs tools (shell, multi-file). Without a tools-capable local model, local-first voice/coding cannot fully replace Grok for agent loops.

## Decision (T-0093)

| Role | Env | Typical model | Use for |
|------|-----|---------------|---------|
| **Coder (completion)** | `LOCAL_CODER_MODEL` | `deepseek-coder:6.7b` | Cheap implement, guided edit, voice completion fallback |
| **Tools agent** | `LOCAL_TOOLS_MODEL` | `qwen2.5-coder:7b-instruct` (if tools probe OK) | OpenCode agent / tool-calling |
| **Escalate** | Grok / monitor | subscription | Architecture, multi-tool, when no local tools model |

**`TOOLS_MODE`:**

| Value | Meaning |
|-------|---------|
| `local_tools` | `LOCAL_TOOLS_MODEL` set and tools API accepted |
| `split` | No tools model - completion local + tools on Grok/monitor |

## Select + probe

```bash
# Host: Ollama up
make eval-select-tools-model
# → probes pulled tags; writes examples/opencode-ollama/.generated/tools-model.env

set -a; . examples/opencode-ollama/.generated/tools-model.env; set +a
echo $LOCAL_TOOLS_MODEL $TOOLS_MODE
```

Manual probe one tag:

```bash
python3 examples/eval-harness/select_tools_model.py --probe-only qwen2.5-coder:7b-instruct
```

### If no tools model (split)

```bash
# optional pull (disk/RAM required)
ollama pull qwen2.5-coder:7b-instruct
make eval-select-tools-model
```

Until then, **honest split**:

1. Voice / OpenCode **completion** on `LOCAL_CODER_MODEL`  
2. Tool-heavy steps: `VOICE_AUTO_AGENT=grok` **or** dual-session monitor (Grok)  
3. Do not claim full local agent tools on deepseek 6.7b  

## OpenCode usage

```bash
set -a
. examples/opencode-ollama/.generated/worker.env
. examples/opencode-ollama/.generated/tools-model.env   # if present
set +a

# Prefer tools model when available
export OPENCODE_CONFIG=$PWD/examples/opencode-ollama/.generated/opencode.json
if [[ -n "${LOCAL_TOOLS_MODEL:-}" ]]; then
  opencode run -m "ollama/${LOCAL_TOOLS_MODEL}" "…"
else
  # completion-oriented; avoid agent tools mode
  opencode run -m "ollama/${LOCAL_CODER_MODEL}" "…"
fi
```

`make worker-stage` regenerates worker.env and can source tools-model.env when present.

## Voice auto-agent (T-0092)

| Setting | Behavior |
|---------|----------|
| `VOICE_AUTO_AGENT=opencode` | Local path; uses `LOCAL_TOOLS_MODEL` if set, else `LOCAL_CODER_MODEL` (completion fallback) |
| `VOICE_AUTO_AGENT=grok` | Cloud tools when local tools_mode=split or task needs it |

## Smoke

```bash
make smoke-tools-model
# exit 0: probe ran; tools_mode local_tools or split documented
# exit 1: Ollama down (fail closed for this smoke on host)
```

## Candidates (preference order when pulled)

1. `qwen2.5-coder:7b-instruct` / `7b`  
2. `qwen2.5-coder:14b*` (if RAM fits)  
3. `llama3.1:8b-instruct`  
4. `mistral-nemo` / other instruct tags that pass probe  

**Authoritative:** probe result, not the list (Ollama templates change).

## Related

- [local-cloud-split.md](local-cloud-split.md)  
- [ADR-0012](../adr/0012-voice-half-duplex-local-first.md) half-duplex local-first  
