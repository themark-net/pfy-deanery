# ADR-0012: Voice half-duplex, local-first (not cloud full-duplex)

- **Date:** 2026-07-26
- **Status:** Accepted
- **Deciders:** operator (cost + local direction); agent (write-up)
- **Related:** ADR-0011 (hybrid Grok/OpenCode) · OQ-0010 · T-0091 · [voice-agent-channel.md](../ops/voice-agent-channel.md)

## Context

We have working **half-duplex** voice I/O into tool-capable agents:

- Desk STT (`make voice-listen`) and remote Tailscale STT (`make voice-remote`)
- Opt-in agent runner (`VOICE_AUTO_AGENT`, T-0091 4b) → Grok headless with tools

X/research shows mature **full-duplex** products (OpenAI GPT-Live + Codex desktop, Claude voice+tools, LiveKit/Pipecat media stacks, Hermes voice, freeapp-class Tailscale voice coding). Those systems are real-but they pull in one or more of:

- Continuous cloud speech-to-speech tokens (often expensive per minute)
- A non-Grok primary coding runtime (Codex, Hermes, Claude Code)
- Heavy GPU for open full-duplex models (PersonaPlex-class)

Operator constraints (2026-07-26):

- Grok subscription **cost is about to rise sharply**; current usage ~5% of weekly limit is not a safe long-term budget.
- Direction: **local OpenCode + Ollama** for bulk work; cloud only when necessary.
- Willing to **sacrifice full duplex** for a sustainable path.
- **Tailscale** is now reliable for phone → host (routing/DNS/split resolved).

Question: which voice path should we **implement next**, given cost and local focus?

## Decision

1. **Do not implement full-duplex cloud voice** (GPT-Live, OpenAI Realtime, continuous S2S) as the primary path for this lab.
2. **Stay half-duplex** for the product path:  
   `speak/record → STT (local Whisper) → text agent run → optional short TTS later`.
3. **Default tool brain for voice auto-runs = OpenCode → Ollama** (local), not Grok.  
   Grok remains **optional monitor / hard problems** when budget allows (ADR-0011 inverted for voice cost: local default, cloud escalate).
4. **Tailscale** remains the remote access SoT (phone → host edge); no public internet voice agent.
5. **Catalog-only** (no primary install): Pipecat/LiveKit duplex media, Hermes voice, freeapp, Codex desktop voice-score as references / optional later.
6. **Full duplex deferred** until either: local duplex media is cheap enough (Pipecat + local STT/TTS without continuous cloud S2S), or cloud budget returns.

## Economics (why this matches industry practice)

| Mode | Token/audio shape | Cost character |
|------|-------------------|----------------|
| Full-duplex cloud S2S | Continuous audio in/out + tool calls | High per minute; bad for long coding sessions |
| Half-duplex local STT → local coder | One short audio blob + local LLM tokens | Near-zero marginal $; GPU/RAM only |
| Half-duplex local STT → cloud coder | Short STT + few agent turns | Bounded; you control when to escalate |

X/builder discourse often separates **“voice that feels alive”** (duplex media) from **“agent that ships code”** (text agent + tools). Sustainable local setups (Tailscale + Hermes/OpenCode + Whisper) commonly use **push-to-talk / end-of-utterance**, not always-on full duplex. Sacrificing duplex for cost is a **normal** tradeoff, not a unique compromise.

## Path comparison (implementation choice)

| Path | Duplex | Primary tools | $ sustainability | Aligns ADR-0011/local | Implement now? |
|------|--------|---------------|------------------|----------------------|----------------|
| **L1 - Half-duplex local (chosen)** | No | OpenCode+Ollama | High | Yes (local bulk) | **Yes** |
| L2 - Half-duplex + Grok auto default | No | Grok | Low under new pricing | Grok-primary voice | No (opt-in only) |
| D1 - Pipecat/LiveKit duplex + local STT/TTS + local agent | Partial→full media | OpenCode | Medium (GPU) | Yes if no cloud S2S | Later |
| D2 - GPT-Live / Realtime / Codex desktop | Yes | OpenAI agents | Low / wrong SoT | No | Reject as primary |
| H1 - Hermes voice primary | Yes-ish | Hermes | Medium | No (runtime pivot) | Reject as primary; catalog ref |
| F1 - freeapp-class product | Varies | Their agent | Unknown | Eval only | Catalog Stage 0 |

## Consequences

### Do

- Default `VOICE_AUTO_AGENT` target for production recipes: **`opencode`** (or explicit local mode), not `grok`.
- Keep Grok path as `VOICE_AUTO_AGENT=grok` for rare escalations.
- Improve **OpenCode tools** situation (tools-capable local model or guided non-tools worker + occasional monitor).
- Prefer **local Whisper** in `.venv` (already); optional short **local TTS** later (Kokoro/piper) for “agent finished” without duplex.
- Document Tailscale as the remote norm; polish Termux client as primary phone UX (half-duplex is fine there).

### Do not

- Build continuous WebRTC duplex that streams every second into cloud LLMs.
- Make Hermes/Codex the primary coding runtime for this repo’s voice track.
- Assume full duplex is required for “real” agentic coding-**tools + iteration** matter more than barge-in.

### Follow-ups (TODO)

- ~~T-0092: OpenCode-default voice auto-agent + smoke~~ **done**  
- T-0093: tools-capable local model or explicit tool-split  
- Optional later: Pipecat local duplex media **without** cloud S2S (D1)  
- Distillation track: cloud → local coder eval (separate from voice media)

## Rejected alternatives

| Alternative | Why rejected now |
|-------------|------------------|
| Full-duplex GPT-Live / OpenAI Realtime as primary | High continuous cost; wrong vendor SoT; locks coding to Codex/ChatGPT |
| Pipecat/LiveKit duplex immediately | Valuable later; adds media complexity before local OpenCode voice path is default and cheap |
| Hermes voice as primary | Productized duplex+agent, but runtime pivot vs ADR-0010/0011 |
| Defer all voice (OQ D) | Half-duplex path already works; throwing it away wastes Tailscale+STT progress |
| Grok auto-agent as default | Unaffordable under rising Grok cost; keep opt-in only |

## Links

- OQ-0010 (resolved toward A + local OpenCode default)  
- ADR-0011 (hybrid surfaces; this ADR specializes **voice cost default**)  
- [voice-agent-runner.md](../ops/voice-agent-runner.md) · [voice-remote-android.md](../ops/voice-remote-android.md)  
