# Stage 0 voice stack references (T-0095)

**Status:** 2026-10-30 PT. Reference only. Stage-0 FAIL / I0 for all three. ADR-0012 half-duplex local-first stays the product path.
**Primary voice path:** `examples/voice-stt-edge/` plus the orchestrator. Not these runtimes.
**Issue #10:** closed 2026-07-30 on the short stub. These receipts are the three-leg check (license, under-5-minute self-host quickstart, hello-world). Nothing was installed.

| Project | Entry | Stage | Install? |
|---------|-------|-------|----------|
| Pipecat | [150-pipecat.md](../../sources/entries/150-pipecat.md) | I0, Stage-0 FAIL | No |
| LiveKit Agents and server | [151-livekit.md](../../sources/entries/151-livekit.md) | I0, Stage-0 FAIL | No |
| freeapp-class (freeapp.ai) | [152-freeapp.md](../../sources/entries/152-freeapp.md) | I0, Stage-0 FAIL | No |

## Why not primary

ADR-0012: half-duplex, local STT, then a text agent, then optional short TTS later. The Pipecat quickstart needs Deepgram, OpenAI, and Cartesia keys. The LiveKit voice sample needs LiveKit Cloud credentials, and its turn-detection weights are under a separate proprietary model license. freeapp.ai is a paid client (founder price on the page: $299) with no published source pin. None of that becomes the voice runtime from this note.

## When to re-open

Only with a timed run that completes a hello without a cloud speech account, plus a new ADR if the product path should change. Do not promote the stage card off I0 from this doc. `tests/test_voice_stage0_ref.py` guards that.
