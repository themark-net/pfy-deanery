# Voice channel for agentic coding (goal)

**Status:** Phase **1** + **4a** + **4b** live · **ADR-0012** half-duplex local-first  
**ID:** T-0091 · OQ-0010 **resolved**  
**Related:** T-0085 worker/monitor · ADR-0011/0012 · Hermes pattern (not runtime) · T-0090 minimal levers

## Cost decision (2026-07-26)

**Full duplex cloud (GPT-Live, Realtime S2S) is not the implementation path.**  
Operator: Grok pricing rising; bulk work must be **local OpenCode + Ollama**. Half-duplex is an acceptable industry-normal sacrifice for sustainability. Tailscale is the remote access SoT.

| Default | Escalate only when needed |
|---------|---------------------------|
| Local Whisper STT | - |
| OpenCode + local coder | Grok monitor / hard problems (`VOICE_AUTO_AGENT=grok`) |
| Half-duplex (record → STT → agent → optional short TTS later) | Full duplex media (Pipecat) only if local and cheap |

See **[ADR-0012](../adr/0012-voice-half-duplex-local-first.md)**.

## Phase 1 (desk) - live

| Piece | Path |
|-------|------|
| STT edge CLI | `examples/voice-stt-edge/stt_edge.py` |
| Wiring smoke | `make smoke-voice-stt` - **mock/text only; does not record audio** |
| Real mic | `make voice-stt-install` then `make voice-listen` |
| Operator README | `examples/voice-stt-edge/README.md` |
| Handoff | `.generated/handoff.sh` after **successful** STT only (blocked if STT failed) |

## Phase 4a (Android remote) - live

| Piece | Path |
|-------|------|
| Remote HTTP edge | `make voice-remote` · `remote_server.py` |
| Phone UI | `http://<host>:8787/` (Chrome record → upload) |
| Operator doc | [voice-remote-android.md](voice-remote-android.md) |
| Smoke | `make smoke-voice-remote` (localhost API; no phone) |
| Transport | **Tailscale** (preferred) + token; not public internet |

```bash
# Desk
make voice-stt-install && make voice-listen
examples/voice-stt-edge/.generated/handoff.sh

# Android (host on tailnet)
VOICE_REMOTE_HOST=0.0.0.0 make voice-remote
# phone: http://<tailscale-host>:8787/  → token → record → Send
# host:  examples/voice-stt-edge/.generated/handoff.sh   # tools via Grok CLI
```

**Success (p1/p4a):** spoken intent → text prompt.  
**Success (p4b):** same prompt **auto-runs tool-capable Grok** (opt-in) - no manual `handoff.sh`.

```bash
# Auto tools after remote STT (opt-in - spends Grok quota)
VOICE_AUTO_AGENT=1 VOICE_REMOTE_HOST=127.0.0.1 make voice-remote
# phone: STT → poll /api/last-run for agent reply

# Desk one-shot
python3 examples/voice-stt-edge/stt_edge.py --text "run make eval-structural" --auto-agent
# or on last capture:
make voice-agent-run   # MODE via VOICE_AUTO_AGENT / VOICE_AGENT_MODE

# Smoke without cloud
make smoke-voice-agent
```

**Not yet:** TTS of the reply to the phone, true VoIP. T-0094: opt-in `VOICE_TTS=1` speaks a short local “done” / “fail”; `VOICE_TTS_MODE=reply` speaks a clipped local reply ([examples/voice-tts-status/README.md](../../examples/voice-tts-status/README.md)). **Session sticky:** default via `session.id` / last-run (T-0091).

## Problem (operator experience)

| Surface | Voice? | Tool use / GitHub / pipelines? |
|---------|--------|--------------------------------|
| Grok **mobile voice** | Excellent UX | **No** - code stays in chat; no tools |
| Grok mobile/web **text**, Grok CLI | Typing | Yes - tools, GitHub, codegen that lands |
| Local OpenCode worker (T-0080/85) | Typing | Partial (model tools vary) |
| Desired | Phone/VoIP or hands-free voice | **Same** tools as CLI agent: edit, git, CI, iterate failures |

Voice without tools is demos. Tools without voice force keyboard. Goal = **voice I/O layer in front of a tool-capable agent**, not voice as a separate dead-end product.

## Desired architecture (layers)

```text
  Phone / VoIP / mic (local or remote)
           │
           ▼
  ┌─────────────────────┐
  │  Voice edge         │  STT (in) + optional TTS (out)
  │  Whisper / cloud STT│  low latency, optional wake word
  └──────────┬──────────┘
             │ text prompts + spoken summaries
             ▼
  ┌─────────────────────┐
  │  Agent runtime      │  tool-capable: OpenCode worker and/or Grok monitor
  │  skills + MCP + git │  same process as T-0085
  └──────────┬──────────┘
             │
             ▼
  repo · make smokes · GitHub Actions · cage
```

**Not required:** replace Grok subscription. Voice can drive **monitor** (cloud) or **worker** (local) or both via the same dual-role model.

## What worker-monitor is today (honest)

`make worker-stage` + two terminals is a **human-mediated handoff**, not automatic task routing:

| Works | Does not |
|-------|----------|
| Shared DoD file + exit card | Automatic “assign ticket to worker” |
| Worker implements on Ollama | Shared live context without paste |
| Monitor reviews diffs | Single process voice→tools |
| Escalation after 3 fails (process) | Phone call into the agent |

So: **useful scaffold**, not yet “hands-free agentic coding.” Gaps: shared state bus, tool-capable local models (or tools always on monitor), voice edge, remote access (Tailscale/VoIP).

## Building blocks found (post-doc research)

### Already in *this* catalog

| Item | Relevance |
|------|-----------|
| Hermes **feedback loops** (Entry 048) | Patterns only (`/hermes-feedback`) - **not** voice |
| awesome-hermes-skills (053) | Skills library - no voice channel scored |
| Worker/monitor (T-0085) | Dual session for local/cloud - **text** |
| Grok CLI + GitHub MCP | Tool path for monitor |
| OpenCode + Ollama (T-0080) | Local worker path |

**No prior TOOLS.md row** for voice STT/TTS, VoIP agent gateways, or “voice → coding agent” stacks was found in-repo (X pipeline has not absorbed a dedicated voice-coding seed yet).

### External (high signal, not adopted)

| Source | What | Fit |
|--------|------|-----|
| [NousResearch/hermes-agent voice mode](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/features/voice-mode.md) | Voice in CLI + Telegram/Discord; live Discord VC | Closest “productized” voice+agent; **runtime** conflicts with “no Hermes primary” unless adapter-only |
| [Use Voice Mode with Hermes](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/guides/use-voice-mode-with-hermes.md) | Practical setup | Reference recipe |
| [l0cut15/hermes-voice-assistant](https://github.com/l0cut15/hermes-voice-assistant) | Local Whisper STT + Kokoro TTS → Hermes API; Docker; Tailscale note | **Best local STT/TTS edge** pattern to reuse without full Hermes UI |
| Hermes issues: Twilio skill, AgentPhone, mobile companion | Phone/SMS/VoIP tracks | Telephony = separate spike |
| OpenCode + Ollama tools | Model-dependent tools | Worker tools ≠ voice |

**Recommendation (not yet decided):**

1. **Do not** make Hermes Agent the primary runtime (ADR-0010/0011 posture).  
2. **Do** catalog Hermes voice + hermes-voice-assistant as **A/B reference**.  
3. Prefer **voice edge (STT/TTS) → our worker/monitor text agents** (OpenCode local + Grok monitor with tools/GitHub).  
4. Phone/VoIP = phase 4 after local mic loop works.

## Phased plan

| Phase | Deliverable | Success | Status |
|-------|-------------|---------|--------|
| **0** | This doc + OQ-0010 + T-0091 | Goal visible; no silent scope creep | **done** |
| **1** | Local mic / file / text: Whisper (or cloud STT) → text into **monitor** Grok or worker OpenCode | Spoken “run smoke / fix fail” becomes a prompt with tools | **done** (`make smoke-voice-stt`) |
| **2** | TTS replies + optional wake word | Hands-free loop at desk | open |
| **3** | Shared worksheet auto-update (worker progress → monitor brief) | Less paste between terminals | open |
| **4a** | Remote HTTP + Android UI over Tailscale | Phone STT → same handoff as desk | **done** (`make voice-remote`) |
| **4b** | Auto agent runner (tools; Grok opt-in) | No manual handoff.sh | **done** (`agent_runner.py`) |
| **4b-L / T-0092** | **OpenCode default** for voice auto-agent (local $) | `1`→opencode; Ollama fallback | **done** |
| **4c** | Short local TTS status (not duplex) | Hear “done/fail” | open |
| **4d** | Optional local Pipecat duplex (no cloud S2S) | Only if free enough | deferred |
| **5** | Product lever: voice as input to `stage`/`ship` | Aligns T-0090 simplicity | open |

## Security / non-goals

- No “disable all cage policy for voice”  
- No committing always-on open phone agents to the internet without ADR  
- Voice edge must not hold raw cloud API keys in mobile apps carelessly  
- Greenfield STT/TTS only if catalog edges fail Stage 0  

## Open questions

See **OQ-0010** (channel priority, Hermes eval depth, latency budget).

## Related

- [worker-monitor.md](worker-monitor.md)  
- [product-operator-surface.md](product-operator-surface.md)  
- Entry 048 Hermes feedback (loops only)  
