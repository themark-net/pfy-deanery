### Entry 208: Inkling 2 Mini: open-weights 26B looped MoE multimodal model (3.4B active) with llama.cpp GGUFs

- **URL**: https://huggingface.co/thinkingmachines/Inkling-2-Mini (Apache-2.0; base checkpoint about 20 GB in mixed NVFP4/MXFP8). GGUF used for the smoke: https://huggingface.co/ggml-org/Inkling-2-Mini-GGUF checked at revision `e8a2cecf0e78914f07cc27b9be711a9b2c7561d9` (2026-11-21 UTC; 2026-11-21 PT). Base repo seen at revision `b85c3cfa615fc413cc9af3379f491b963f3b586a`.
- **Date**: 2026-11-21 (daily X intake)
- **Source / Poster**: bookmarks of posts by @AlexFinn (https://x.com/i/status/2123930655000346888), @0x0SojalSec (https://x.com/i/status/2123918168515346785) and @TheAhmadOsman (https://x.com/i/status/2123936559447920931); also named by @alex_verem (https://x.com/alex_verem/status/2124096233707106732).
- **Summary / Key Claims** (upstream model card and posts; their claims, not verified here): released 2026-11-20 by Thinking Machines Lab. 24-layer decoder with sparse MoE (8 of 128 experts per token); the middle 12 layers loop three times with shared weights, so 26.4B total, 3.4B active, about 5.4B effective active per token. Text and image input, text output, up to 1M context. Posts claim it beats Qwen3.8-27B; the card lists llama.cpp, Ollama, vLLM and SGLang support.
- **Why it matters here**: a fast local model for the OpenCode fallback lane and for screenshot or document reading. With far fewer active parameters than qwen3.6:35b or Qwen3.8-27B it should decode faster on nimo, so it is an eval-auto trial target against the current lane default, not just a reference.
- **Fit on nimo**: ggml-org GGUFs are Q8_0 about 27.8 GB and IQ4_NL about 17.6 GB, plus a 0.3 to 0.6 GB mmproj, all inside the GPU carve-out. The upstream checkpoint targets NVFP4/MXFP8 (NVIDIA and Apple paths), so the GGUF route is the one for nimo. Whether llama.cpp's AMD backend handles the looped architecture is not checked here. Downloads go under `$PFY_TMP`; no account or key is needed (repo is not gated).
- **Verified** (2026-11-21): GGUF revision pin matched via the Hugging Face models API; smoke exits 2 (not downloaded). 7 stub tests pass.
- **Findings**:
  - Base repo about 2,970 likes; the unsloth GGUF repo shows about 238k downloads within a day of release.
  - An "uncensored" community LoRA variant exists; it is out of scope here.
  - Inkling 2 Small (thinkingmachines/Inkling-2-Small, also Apache-2.0) is the non-looped sibling; same trial can cover it later if Mini wins.
- **Extracted Repos / Tools**: https://huggingface.co/thinkingmachines/Inkling-2-Mini, https://huggingface.co/ggml-org/Inkling-2-Mini-GGUF, https://huggingface.co/unsloth/Inkling-2-Mini-GGUF
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row. Stage card `data/stages/inkling-2-mini.json`.
- **Smoke**: `python3 examples/x-intake-local/smoke_208.py`. Revision-metadata only. Pins `$INKLING2_MINI_COMMIT`. Fetches via `$INKLING2_MINI_FETCH_BIN` or the stdlib Hugging Face models API. Does not download. Receipt: `pipelines/smoke/inkling2mini/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_208` (7 stub tests).
- **Non-goals**: no download outside `$PFY_TMP`, no change to the default lane model without an eval-auto result, no uncensored variants. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Revision match becomes exit 0 | Keep exit 2 while it is not downloaded |
| Launch hype taken as ours | Posted comparisons read as our results | Trial on our own task set against qwen3.6:35b before any switch |
| Backend gap | llama.cpp on AMD lacks the looped-layer path or runs it slowly | Record the failure in the trial receipt and keep the current default |
| Pin drift | The GGUF repo is re-uploaded | Smoke checks this revision |

- **Status**: Cataloged I0. Next step: eval-auto trial in the OpenCode lane against qwen3.6:35b (and the 206 adapter) on the same small task set, Q8_0 GGUF, under `$PFY_TMP`.
