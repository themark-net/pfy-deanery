### Entry 150: Pipecat (Stage-0 receipt, reference only)

- **URL**: https://github.com/pipecat-ai/pipecat
- **Date**: 2026-10-30 PT (T-0095). Docs read only. Nothing installed.
- **Poster / source**: ADR-0012 catalog-only voice list. Upstream README and LICENSE at pin `6f777a0ef3bb98163d10d708525a0db21cda5fbf` (committer 2026-10-30T18:09:03Z). Quickstart page https://docs.pipecat.ai/getting-started/quickstart read the same day. GitHub API at this read: default branch `main`, SPDX BSD-2-Clause, 16955 stars. Not a score.
- **Summary / Key Claims**: Open-source Python framework for real-time voice and multimodal agents (Daily and community). A pipeline of frame processors: audio in, speech-to-text, an LLM, text-to-speech, audio out. Transports include Daily WebRTC, LiveKit WebRTC, WebSocket, and a local transport. The services table names local-capable pieces (Kokoro, Piper, local transport) and many cloud services. This receipt did not run any of them.
- **Extracted Repos / Tools**: https://github.com/pipecat-ai/pipecat (BSD-2-Clause, copyright 2024-2026, Daily). Python 3.11 minimum, 3.12 recommended (README "Developing Pipecat").
- **TOOLS.md Link**: None. Stage-0 FAIL / I0 awareness. No TOOLS.md row. No `data/tools.json` row. No triple-write. The stage card `Pipecat` stays `integration_stage` I0, `intent` ref_only.
- **Notes (Stage-0 gate):**
  - **License:** PASS. Upstream `LICENSE` at the pin is BSD 2-Clause. Commercial and research use are allowed. It is not copyleft.
  - **Self-host / quickstart:** FAIL. The quickstart page says "Build and run your first Pipecat voice AI bot in under 5 minutes" and shows `uv tool install "pipecat-ai[cli]"`, `pipecat init quickstart`, `uv sync`, `uv run bot.py`. The same page requires API keys for Deepgram, OpenAI, and Cartesia (`DEEPGRAM_API_KEY`, `OPENAI_API_KEY`, `CARTESIA_API_KEY`) before that bot can talk. A fresh machine with only the repo cannot complete the hello. The page also says the first startup may take about 20 seconds while it downloads models. This run did not time it and did not install Pipecat (MVP-3 is busy; ADR-0012 says no primary install).
  - **Hello-world:** SHOWN, not executed. After the scaffold, `uv run bot.py` is documented to serve `http://localhost:7860/client`. That command was not run.
  - **Fail closed:** Stage-0 FAIL / I0 awareness. The license leg passes. The under-5-minute self-host hello does not: the shown path needs three cloud accounts. I0 stays awareness only. No catalog row, no pin in `data/tools.json`, no clone, no Make target, no env required var.
  - **Non-goals:** Do not install Pipecat. Do not scaffold `pipecat init` in this repo (it writes `AGENTS.md` and `CLAUDE.md`). Do not make it the voice runtime. Half-duplex local STT stays the product path (ADR-0012). No Feature GO. Catalog HOLD 70-75 unchanged.
- **Score note (not scored):** I0. No S1-S4 and no tier.
- **How this fails / how we recover:**

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Headline read as a pass | A later edit marks a pass because the docs say "under 5 minutes" while the same page still requires `DEEPGRAM_API_KEY`, `OPENAI_API_KEY`, and `CARTESIA_API_KEY` | Keep this receipt at Stage-0 FAIL until a timed run completes with no cloud speech or LLM account. `tests/test_voice_stage0_ref.py` fails if the receipt says pass while those key names remain. |
| Scaffold in this repo | `pipecat init` overwrites operator docs | Run it only in a throwaway directory outside this worktree. |
| Silent promotion | A TOOLS.md row or a `data/tools.json` object, or the stage card leaves I0 | The same test fails. Revert the catalog row. Entry 150 stays the artifact. |
| Local services treated as the quickstart | Kokoro, Piper, or the local transport are cited as if this receipt ran them | They are names in the upstream services table only. Run one in a scratch dir before any catalog row. |

- **Status**: Stage-0 FAIL / I0 awareness (T-0095, issue #10). Receipt only. Not a primary install.
