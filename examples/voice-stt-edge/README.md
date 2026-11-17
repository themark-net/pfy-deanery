# Voice STT edge → tool-capable agents (T-0091 phase 1)

**Host-only edge.** Turns speech into a **transcript + agent prompt**, then hands off to Grok (monitor) or OpenCode (worker).

This is **not** Grok mobile voice (code stuck in chat).  
This is **not** Hermes as primary runtime (OQ-0010 path **A**).

## Two different commands (do not confuse)

| Command | Records mic? | Runs Whisper? | Purpose |
|---------|--------------|---------------|---------|
| **`make smoke-voice-stt`** | **No** | **No** | Wiring test: mock/text → prompt/handoff files |
| **`make voice-listen`** | **Yes (desk)** | **Yes** | Real speech → STT → Grok/OpenCode |
| **`make voice-remote`** | **Yes (Android)** | **Yes (on host)** | Phone → host STT → handoff; prefer **Termux client** if browser hangs ([clients/](clients/README.md)) |
| **`VOICE_AUTO_AGENT=1 make voice-remote`** | Yes | Yes + **tools** | Phase **4b**: STT → Grok headless with tools (no `handoff.sh`) |
| **`make voice-agent-run`** | No | Re-run agent | Run tools on last transcript/prompt |
| **`make smoke-voice-agent`** | No | Mock agent | 4b smoke without cloud |

If smoke **PASS** but you never spoke into a mic, that is expected. Smoke only proves the edge files work.

```bash
# 1) Lab wiring (what you already ran)
make smoke-voice-stt

# 2) Real voice path (host, once + each listen)
make voice-stt-install          # creates examples/voice-stt-edge/.venv + faster-whisper
make voice-stt-probe            # should exit 0
make voice-listen               # record 5s → STT → artifacts
examples/voice-stt-edge/.generated/handoff.sh
```

**PEP 668 / Debian:** install never uses system `pip` (that fails with
`externally-managed-environment`). It uses a **project venv**. If venv creation
fails: `sudo apt install python3-venv python3-full`.

Always run STT via `make voice-listen` or `examples/voice-stt-edge/python.sh`
(not bare `python3`, which will not see the venv packages).

### Empty transcript / near-silent capture

If probe is ready but STT says **empty** or **near-silent**:

1. Speak a **full English phrase** for the whole window (not a single word at the end).
2. Lengthen: `VOICE_LISTEN_SECONDS=8 make voice-listen`
3. Check mic device:
   ```bash
   arecord -l
   pactl list short sources
   VOICE_ARECORD_DEVICE=default make voice-listen
   # or: VOICE_ARECORD_DEVICE=pulse
   ```
4. Stronger model: `VOICE_STT_WHISPER_MODEL=small.en make voice-listen`
5. Re-decode last wav (no re-record):
   ```bash
   examples/voice-stt-edge/python.sh examples/voice-stt-edge/stt_edge.py \
     --audio examples/voice-stt-edge/.generated/last-capture.wav \
     --backend local --target monitor
   ```

Look at the `peak=` / `rms=` line after capture — if `NEAR-SILENT`, Whisper cannot invent speech.

### Re-transcribe a capture you already made

Your earlier run **did record** (`last-capture.wav`) but failed STT because Whisper was not installed:

```bash
make voice-stt-install
examples/voice-stt-edge/python.sh examples/voice-stt-edge/stt_edge.py \
  --audio examples/voice-stt-edge/.generated/last-capture.wav \
  --backend local --target monitor
examples/voice-stt-edge/.generated/handoff.sh
```

Do **not** run `handoff.sh` after a failed STT — it used to re-launch whatever smoke left behind (often raw `ping` → Grok “Pong”). Failed STT now **blocks** handoff until a successful transcription.

## Simulate without STT

```bash
python3 examples/voice-stt-edge/stt_edge.py \
  --text "Run make eval-structural and fix any failures" \
  --target monitor
examples/voice-stt-edge/.generated/handoff.sh
```

## Targets

| Target | Runtime | Tools |
|--------|---------|-------|
| `monitor` (default) | Grok Build CLI | Yes — GitHub, shell, edit |
| `worker` | OpenCode → Ollama | Partial (model-dependent) |
| `raw` | transcript only | — |

## STT backends

| Backend | Needs |
|---------|--------|
| `mock` | Fixture only (smoke) |
| `text` | `--text` or stdin |
| `local` | `make voice-stt-install` → `.venv` + faster-whisper (or system whisper CLI) |
| `openai` | `OPENAI_API_KEY` |
| `ollama` | Experimental; often 404 unless you pull a whisper-capable model |
| `auto` | local → openai → ollama (quiet probes) |

```bash
# Mic → local Whisper → Grok monitor
python3 examples/voice-stt-edge/stt_edge.py --mic --seconds 6 --backend local --target monitor

# Cloud Whisper
OPENAI_API_KEY=… python3 examples/voice-stt-edge/stt_edge.py --mic --backend openai --target monitor
```

Mic capture uses `arecord` or `ffmpeg` when installed.

## Artifacts (gitignored)

Under `examples/voice-stt-edge/.generated/`:

| File | Role |
|------|------|
| `last-capture.wav` | Last mic recording (even if STT failed) |
| `last-transcript.txt` | Clean spoken intent (only after successful STT) |
| `agent-prompt.md` | Wrapped prompt (role + tool instructions) |
| `handoff.sh` | Launch `grok` / `opencode` — **blocked** if STT failed |
| `STT-NEEDED.txt` | Written when capture ok but STT missing |
| `last-meta.json` | Backend/target metadata (`ok: true/false`) |

## Grok `--always-approve` (opt-in)

The voice agent runner does **not** pass `--always-approve` unless you set `VOICE_AGENT_ALWAYS_APPROVE=1` (also `true` / `yes` / `on`). Leave it unset for an attended run that can confirm each tool call. Only enable this on a trusted host; it is powerful. See [docs/ops/voice-agent-runner.md](../../docs/ops/voice-agent-runner.md).

## Env vars

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Cloud Whisper (`--backend openai`) |
| `VOICE_STT_WHISPER_MODEL` | Local model (default `base`) |
| `VOICE_STT_OLLAMA_MODEL` | Ollama audio model (default `whisper`) |
| `OLLAMA_HOST` | Ollama base |
| `VOICE_STT_OUT` | Override artifact dir |
| `VOICE_LISTEN_SECONDS` | `make voice-listen` duration (default 5) |
| `VOICE_TARGET` | `monitor` \| `worker` \| `raw` |
| `VOICE_HANDOFF=1` | `make voice-listen` also exec handoff |
| `VOICE_AGENT_ALWAYS_APPROVE=1` | Opt in: pass `--always-approve` to Grok. Default **off** — Grok will prompt for tool approval unless you set this to `1`, `true`, `yes`, or `on`. |
| `VOICE_TTS=1` | Opt in: speak a short local “done” / “fail” after the agent run ([voice-tts-status](../voice-tts-status/README.md)). Default **off**. No model is downloaded. |

## Phase map

| Phase | This package |
|-------|----------------|
| **1** (here) | STT → text → Grok/OpenCode handoff |
| 2 | TTS replies + wake word |
| 3 | Auto worksheet with worker-monitor |
| 4 | Remote Tailscale/VoIP |
| 5 | Product lever voice→stage/ship |

See [docs/ops/voice-agent-channel.md](../../docs/ops/voice-agent-channel.md).
