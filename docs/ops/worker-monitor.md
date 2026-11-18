# Worker / monitor split (T-0085)

**Status:** Active recipe  
**Depends:** ADR-0011 · T-0080 (`make smoke-opencode-ollama`) · [local-cloud-split.md](local-cloud-split.md)

## Intent

| Role | Runtime | Model | Job |
|------|---------|-------|-----|
| **Worker** | OpenCode → Ollama | `LOCAL_CODER_MODEL` (e.g. `deepseek-coder:6.7b`) | Implement, edit, run cheap loops |
| **Monitor** | Grok Build (subscription) | cloud | DoD / exit card, review, escalate |

Grok does **not** auto-switch to Ollama. Offload = run a **worker client** on local models while Grok **supervises**.

## Prerequisites (host)

```bash
# Lab green
make smoke-litellm-ollama      # optional cage path
make smoke-opencode-ollama     # worker path (T-0080)
make eval-structural

# Worker model present
export LOCAL_CODER_MODEL=deepseek-coder:6.7b   # or from eval-select-models
curl -sS http://127.0.0.1:11434/api/tags | grep -q "$LOCAL_CODER_MODEL"
```

**Tools (T-0093):** Many Ollama tags (including `deepseek-coder:6.7b`) **do not support tools**.

```bash
make eval-select-tools-model   # probe + write tools-model.env
set -a; . examples/opencode-ollama/.generated/tools-model.env; set +a
```

| `TOOLS_MODE` | Meaning |
|--------------|---------|
| `local_tools` | Use `LOCAL_TOOLS_MODEL` for OpenCode agent |
| `split` | Completion on `LOCAL_CODER_MODEL`; tool-heavy → **monitor (Grok)** |

Full policy: [local-tools-split.md](local-tools-split.md).

## Stage worker (one command)

```bash
make worker-stage
# → runs smoke-opencode-ollama, writes worksheet + env exports
```

Artifacts (gitignored under `.generated/` or local):

- `examples/opencode-ollama/.generated/opencode.json`
- `examples/opencode-ollama/.generated/worker.env`
- `examples/opencode-ollama/.generated/monitor-brief.md`

## Dual-session loop (manual, reliable)

### Terminal A - Worker

```bash
set -a; . examples/opencode-ollama/.generated/worker.env; set +a
export OPENCODE_CONFIG=$PWD/examples/opencode-ollama/.generated/opencode.json
opencode
# model: ollama/$LOCAL_CODER_MODEL
# skills: .opencode/skills → bootstrap/grok-cli/skills
# implement against the DoD in monitor-brief.md
```

### Terminal B - Monitor

```bash
grok
# or: make cage-grok-shell → grok
```

Paste or open `examples/opencode-ollama/.generated/monitor-brief.md`, then:

1. `/agent-loops plan` - fill exit card for the **product** goal  
2. `/one-shot` only if you take over implementation on Grok  
3. Otherwise: review worker diffs (`git diff`), restate DoD, **escalate** only after 3 worker failures / no-progress  
4. `/hermes-feedback memory` at end of session  

## Escalation rules (exit card)

| Event | Action |
|-------|--------|
| Worker green on DoD checks | Monitor verifies → ship |
| Same error 3× | Monitor takes over or changes plan |
| Architecture / product fork | Monitor `/adr` or `/open-questions` |
| Tools required, worker model no-tools | Monitor does tool-heavy steps **or** switch worker model |

## Make targets

| Target | Role |
|--------|------|
| `make worker-stage` | Prove Ollama worker path + write brief/env |
| `make worker-env` | Print/export worker env only |
| `make monitor-brief` | Regenerate monitor brief from template + git status |
| `make smoke-opencode-ollama` | T-0080 underlying smoke |

## Automation boundary (honest handoff)

This recipe is **two processes + shared DoD file**, not automatic task assignment.

| Works today | Still missing for “hands-free” |
|-------------|------------------------------|
| Shared DoD / exit card file | Live shared context without paste |
| Worker implements on Ollama | Reliable OpenCode **tools** on small models |
| Monitor reviews + escalates (process) | Single orchestrator watching both |
| Git as source of truth | Auto-update brief from worker CI |

**Will it hand off tasks “in this shape”?**  
**Partially:** yes for a disciplined human-in-the-loop (you or monitor Grok stating DoD, worker executing).  
**Not yet:** voice-driven, phone-driven, or fully automatic ticket→worker→PR without a supervisor session.

Future automation (post T-0085):

- append worker progress / `git diff --stat` into monitor brief  
- stop when DoD `make` targets exit 0  

**Voice (T-0091 p1):** STT edge → same agents - `make smoke-voice-stt` · [voice-agent-channel.md](voice-agent-channel.md) · `examples/voice-stt-edge/`

```bash
python3 examples/voice-stt-edge/stt_edge.py --text "Review worker diff and update DoD" --target monitor
# or --mic --backend local  (host Whisper)
examples/voice-stt-edge/.generated/handoff.sh
```


Do **not** wait for a multi-agent company runtime; this matches ADR-0005 light process.

## Related

- [product-operator-surface.md](product-operator-surface.md) · T-0090 minimal levers  
- [loop-engineering.md](loop-engineering.md) · eight exits  
- ADR-0011 hybrid surfaces  
