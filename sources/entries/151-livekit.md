### Entry 151: LiveKit Agents and server (Stage-0 receipt, reference only)

- **URL**: https://github.com/livekit/agents and https://github.com/livekit/livekit
- **Date**: 2026-10-30 PT (T-0095). Docs read only. Nothing installed.
- **Poster / source**: ADR-0012 catalog-only voice list. Agents README, `LICENSE`, and `MODEL_LICENSE` at pin `11c8ad8d74c272cf046e65d83cfe7be46abaec64` (committer 2026-10-30T10:47:32Z). Media server pin `8f7597e0caba095834a9812fe7d19d57a6a1b79d` on `master` (committer 2026-10-31T01:36:13Z). GitHub API at this read: agents SPDX Apache-2.0, 15015 stars; server SPDX Apache-2.0, 21944 stars. Not scores.
- **Summary / Key Claims**: LiveKit Agents is a Python framework (a separate Node library exists) that joins a LiveKit room as a participant. The README sample builds a voice agent with `AgentSession` and LiveKit Inference (`inference.STT`, `inference.LLM`, `inference.TTS`), which the same sample calls a unified API on LiveKit Cloud. The media server is a separate Apache-2.0 repo. This receipt did not run either repo.
- **Extracted Repos / Tools**: https://github.com/livekit/agents (Apache-2.0 `LICENSE`). Turn-detection model weights are under `MODEL_LICENSE` (LiveKit Model License Agreement): proprietary models, usable with the Agents framework, not standalone and not with other frameworks. https://github.com/livekit/livekit (Apache-2.0 media server).
- **TOOLS.md Link**: None. Stage-0 FAIL / I0 awareness. No TOOLS.md row. No `data/tools.json` row. No triple-write. The stage card `LiveKit` stays `integration_stage` I0, `intent` ref_only.
- **Notes (Stage-0 gate):**
  - **License:** PASS for the Agents framework and the media server. Both GitHub licenses are Apache-2.0 (commercial and research use; not copyleft). The Agents `MODEL_LICENSE` is not Apache. It is a proprietary model license that limits those weights to the Agents framework. Do not read the Apache LICENSE as covering the turn-detection models.
  - **Self-host / quickstart:** FAIL. The README shows `pip install "livekit-agents[openai,deepgram,cartesia]"`. It does not show an under-5-minute fresh setup. The voice sample needs `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET`, and it calls LiveKit Inference. `python myagent.py dev` connects to LiveKit Cloud or a self-hosted server. This run did not install the package, did not start the media server, and did not time a hello (MVP-3 is busy; ADR-0012 says no primary install).
  - **Hello-world:** SHOWN, not executed. `python myagent.py console` is documented as terminal audio with no external servers. The voice sample on the same page is the LiveKit Inference agent above, which does need the three environment variables. Neither command was run.
  - **Fail closed:** Stage-0 FAIL / I0 awareness. The framework license passes. An under-5-minute self-host voice hello is not shown, and the shown voice sample needs LiveKit Cloud credentials. I0 stays awareness only. No catalog row, no pin in `data/tools.json`, no clone, no Make target, no env required var.
  - **Non-goals:** Do not install `livekit-agents`. Do not run `npx skills add livekit/agent-skills`. Do not start the media server. Do not make LiveKit the voice runtime. Half-duplex local STT stays the product path (ADR-0012). No Feature GO. Catalog HOLD 70-75 unchanged.
- **Score note (not scored):** I0. No S1-S4 and no tier.
- **How this fails / how we recover:**

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Apache read as the whole stack | A later slice vendors the turn-detection weights under the Apache LICENSE | Re-read `MODEL_LICENSE` at the pin. Those weights stay out of this repo. |
| Console line read as a pass | The receipt is marked pass because `python myagent.py console` is one command, while the voice sample still needs `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` | Keep Stage-0 FAIL until a timed console or self-hosted run is logged. `tests/test_voice_stage0_ref.py` fails if the receipt says pass while those variable names remain. |
| Silent promotion | A TOOLS.md row or a `data/tools.json` object, or the stage card leaves I0 | The same test fails. Revert the catalog row. Entry 151 stays the artifact. |

- **Status**: Stage-0 FAIL / I0 awareness (T-0095, issue #10). Receipt only. Not a primary install.
