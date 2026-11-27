### Entry 209: Ternary Bonsai 2.5 27B: ternary (1.76 bits/weight) Qwen3.8-27B model built for agents

- **URL**: https://huggingface.co/prism-ml/Ternary-Bonsai-2.5-27B-GGUF (Apache-2.0; GGUF, PTQ1_0 file about 5.93 GB at 1.76 bits/weight; base model Qwen3.8 27B). Checked at revision `28a7093cc25bc151cc2b284c5570f12ce343fdcf` (2026-11-24 UTC; 2026-11-24 PT).
- **Date**: 2026-11-26 (daily X intake; watch post seen 2026-11-26 PT)
- **Source / Poster**: post by @PrismML, https://x.com/PrismML/status/2125310762390552588, seen via @DanKornas, https://x.com/DanKornas/status/2125915211336953959 ("offload simple tasks onto this model")
- **Summary / Key Claims** (upstream model card; their claims, not verified here): "a 27B ternary model built for agents", based on Qwen3.8 27B, said to be stronger than Ternary Bonsai 2 27B at agentic coding, multi-turn tool use and long-horizon tasks. Files come in PTQ1_0, PQ2_0 and Q2_0, each also with an `-mtp` draft-head variant for speculative decoding, plus an optional mmproj vision tower (BF16 or Q8_0).
- **Why it matters here**: a 27B-class agent model in about 6 GB is a cheap candidate for offloading small, low-risk tasks in the local fallback lane, next to the current qwen3.6:35b pick and the entry 206 adapter. Worth a trial on nimo, not a design reference.
- **Fit on nimo**: nimo is AMD Strix Halo (Radeon 8060S) with no NVIDIA GPU. PTQ1_0 and PQ2_0 need the PrismML llama.cpp fork (https://github.com/PrismML-Eng/llama.cpp), whose kernels target CUDA and Metal (CPU and SYCL also listed), so on nimo only the Q2_0 file on stock upstream llama.cpp (Vulkan, ROCm or CPU) is realistic. Q2_0 support on the Vulkan or ROCm backend is not verified here. Downloads go under `$PFY_TMP`; no account or key is needed (repo is not gated).
- **Verified** (2026-11-26): revision pin matched via the Hugging Face models API; smoke exits 2 (not downloaded, and the box that ran it has no GPU). 7 stub tests pass.
- **Findings**:
  - About 59k downloads and 523 likes on the GGUF repo, created 2026-11-24 UTC.
  - The card says to pass `--min-p 0` and recommends Qwen3.8 sampling (temperature 1.0, top-p 0.95, top-k 20).
  - The repo ships llama.cpp MTP presets for CUDA, Metal, SYCL and Hexagon only; none for Vulkan or ROCm.
  - Related: the older 1-bit Bonsai 27B is pfy-mentat `sources/x-posts.md` entry 045.
- **Extracted Repos / Tools**: https://huggingface.co/prism-ml/Ternary-Bonsai-2.5-27B-GGUF, https://github.com/PrismML-Eng/llama.cpp
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row. Stage card `data/stages/ternary-bonsai-2-5-27b.json`.
- **Smoke**: `python3 examples/x-intake-local/smoke_209.py`. Revision-metadata only. Pins `$TERNARY_BONSAI25_COMMIT`. Fetches via `$TERNARY_BONSAI25_FETCH_BIN` or the stdlib Hugging Face models API. Does not download. Receipt: `pipelines/smoke/ternarybonsai25/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_209` (7 stub tests).
- **Non-goals**: no download outside `$PFY_TMP`, no PrismML fork build outside `$PFY_TMP`, no change to the default lane model without an eval-auto result. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Revision match becomes exit 0 | Keep exit 2 while it is not downloaded |
| Benchmark claims taken as ours | Upstream agentic claims read as our results | Trial on our own small task set against qwen3.6:35b |
| Backend gap | Q2_0 is slow or unsupported on Vulkan or ROCm, and the fork kernels are CUDA/Metal only | Try CPU, then record the result and stop; do not port the fork |
| Pin drift | The repo is updated | Smoke checks this revision |

- **Status**: Cataloged I0. Next step: trial on nimo with stock llama.cpp and the Q2_0 file on a small task set against qwen3.6:35b, under `$PFY_TMP`.
