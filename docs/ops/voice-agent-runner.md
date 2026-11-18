# Voice → tool-capable agent runner (T-0091 phase 4b)

**Status:** Live  
**Closes the gap:** STT file → **actual tools** without `handoff.sh`

## What it does

```text
transcript / agent-prompt.md
        │
        ▼
  agent_runner.py
        │  VOICE_AUTO_AGENT=1|mock|grok|opencode
        ▼
  grok --cwd REPO --max-turns N \\
       [--always-approve]  # only if VOICE_AGENT_ALWAYS_APPROVE=1
       --output-format plain --prompt-file …
        │
        ▼
  last-run.json · last-reply.txt · last-run.log
  (phone: GET /api/last-run)
```

## Opt-in (important) - ADR-0012 / T-0092

| `VOICE_AUTO_AGENT` | Behavior | Cost |
|--------------------|----------|------|
| unset / `0` | STT only | $0 |
| **`1` / `on` / `auto` / `opencode`** | **Local bulk:** OpenCode CLI → Ollama, or Ollama HTTP fallback | Local only |
| `grok` | Grok headless with tools | **Cloud - escalate only** |
| `mock` | Fake agent (smokes) | $0 |

**T-0096:** bare `VOICE_AUTO_AGENT=1` means **orchestrate** (default **high-first** dual-tier).  
Use `=opencode` for local-only cost control.

| Value | Behavior |
|-------|----------|
| `1` / `orchestrate` | Dual-tier - see [voice-orchestrator.md](voice-orchestrator.md) |
| `opencode` | Local only |
| `grok` | High only |

```bash
# Full operator (high coordinates → local implements)
VOICE_AUTO_AGENT=1 VOICE_ROUTE=high-first make voice-remote

# Cheap day
VOICE_AUTO_AGENT=opencode make voice-remote
```

If OpenCode CLI is missing, runner falls back to **Ollama chat completions**.

Model preference (T-0093):

1. `LOCAL_TOOLS_MODEL` / `OPENCODE_AGENT_MODEL` (tools-capable, if set)  
2. else `LOCAL_CODER_MODEL`  

```bash
make eval-select-tools-model
set -a; . examples/opencode-ollama/.generated/tools-model.env; set +a
VOICE_AUTO_AGENT=opencode make voice-agent-run
```

See [local-tools-split.md](local-tools-split.md).

Remote open without this flag will **not** burn cloud quota.

## Host recipes

```bash
# A) Remote phone + auto tools
VOICE_AUTO_AGENT=1 VOICE_REMOTE_HOST=127.0.0.1 make voice-remote
make voice-remote-serve   # HTTPS for mic
# speak/text on phone → tools run on host → poll last-run in UI

# B) Desk after STT
examples/voice-stt-edge/python.sh examples/voice-stt-edge/stt_edge.py \
  --text "run make eval-structural and report" --auto-agent

# C) Re-run agent on last prompt only
make voice-agent-run
# VOICE_AGENT_MODE=mock make voice-agent-run

# D) Smoke (no cloud)
make smoke-voice-agent
```

## Caps

| Env | Default | Meaning |
|-----|---------|---------|
| `VOICE_AGENT_MAX_TURNS` | `8` | Grok `--max-turns` |
| `VOICE_AGENT_TIMEOUT` | `600` | subprocess timeout (s) |
| `VOICE_AGENT_ALWAYS_APPROVE` | unset / `0` | pass `--always-approve` only when set to `1`, `true`, `yes`, or `on`. Default **off**. |
| `VOICE_AGENT_REPO` | repo root | `--cwd` for Grok |
| `VOICE_TTS` | unset / `0` | speak a short “done” / “fail” only when set to `1`, `true`, `yes`, or `on`. Default **off**. See [examples/voice-tts-status/README.md](../../examples/voice-tts-status/README.md). |
| `VOICE_TTS_MODE` | unset / `status` | `reply` or `full` speaks a clipped agent reply (400 characters, word boundary). A typo stays on status. No phone playback. |

## Artifacts (gitignored)

| File | Role |
|------|------|
| `.generated/last-run.json` | status: queued/running/done/error |
| `.generated/last-reply.txt` | assistant text |
| `.generated/last-run.log` | full stdout/stderr |
| `.generated/last-agent-prompt.txt` | exact prompt sent |

## API

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/text` `/api/audio` | include `agent_queued` when auto on |
| GET | `/api/last-run` | auth; poll for status/reply |

## Security

- Default **off**
- Still require Tailscale + token for remote
- `--always-approve` is off by default and is powerful - only set `VOICE_AGENT_ALWAYS_APPROVE=1` on a trusted host
- Do not expose runner to the public internet

## Not in 4b

- TTS of the reply to the phone (T-0094 now has opt-in local status and a clipped local reply via `VOICE_TTS_MODE=reply`; see [examples/voice-tts-status/README.md](../../examples/voice-tts-status/README.md))
- Sticky multi-session resume (use `grok -c` later)  
- Hermes primary runtime  

## Related

- [voice-agent-channel.md](voice-agent-channel.md)  
- [voice-remote-android.md](voice-remote-android.md)

## Session sticky (T-0091)

- File: `examples/voice-stt-edge/.generated/session.id`
- Env: `VOICE_SESSION_ID=…` pin; `VOICE_SESSION_RESET=1` new session
- Every `last-run.json` includes `session_id` for phone `/api/last-run` continuity
- Grok multi-turn: same session id across `voice-agent-run` / orchestrator turns (operator may still use `grok -c` for CLI chat history)

## MCP deep path (monitor)

High tier (Grok) is the **tool-capable** path: filesystem MCP, write-guard, GitHub when configured on host/cage.

| Surface | MCP depth |
|---------|-----------|
| Grok monitor | Full host/cage MCP stack (primary) |
| OpenCode worker | Local tools/config only - not full GitHub MCP by default |
| Orchestrator high-first | Coordinator may use MCP; delegates bulk to local |

Smoke: `make smoke-voice-agent` (mock) + G1 soft voice-stt. Human UAT (G2) for real mic/MCP feel.

## Cross-turn memory (GAP-17)

- File: `.generated/memory.jsonl` (ring via `VOICE_MEMORY_TURNS`, default 5)
- Default on (`VOICE_MEMORY=1`); set `0` to disable
- Injected into agent prompts via `memory_prompt_block()`
- `last-run.json` includes `memory_turns` count
