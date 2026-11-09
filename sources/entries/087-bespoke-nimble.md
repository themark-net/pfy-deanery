### Entry 087: Bespoke Nimble — open recipe and 9B model for Jev-style typed decisions

- **URL**: https://github.com/bespokelabsai/nimble
- **Date**: 2026-10-05 (daily X intake)
- **Source / Poster**: the operator's bookmark of @aisearchio, https://x.com/aisearchio/status/2101394114176806966 ("Jev is not open-source and only available via API. Here's an open version called Nimble")
- **Summary / Key Claims** (upstream README): Data, model and training recipe for an open Jev-like decision model. Takes text plus a flat schema of enum or boolean fields and returns the picked answer and the probability of each allowed answer, read from one-token answer codes (no generated JSON). Model: https://huggingface.co/bespokelabs/Bespoke-Nimble-9B, a LoRA fine-tune of Qwen3.5-9B; the latest checkpoint has 8,192-token context and up to 255 choices per field. Upstream reports 90.12% agreement with reference labels on its 324 held-out examples, vs 66.36% for base Qwen3.5-9B and 93.21% for Jev 1.13.0. The authors say the labels are synthetic and the test is narrow (six source families). Training data (2,676 examples) and holdout (324) are published. The README says no TypeSafe or generation API key is needed for local inference. Upstream says they did not distill from Jev.
- **Fit on nimo** (AMD Strix Halo, 61 GB RAM, no NVIDIA): Not on the documented paths. Upstream supports Apple Silicon (MLX) or Linux with an NVIDIA BF16 GPU (CUDA). Unquantized 9B weights are about 18 GB, and the merge step runs on CPU. A ROCm or CPU path on the Radeon 8060S is not documented upstream and is untested here.
- **Extracted Repos / Tools**: https://github.com/bespokelabsai/nimble · https://huggingface.co/bespokelabs/Bespoke-Nimble-9B
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/typed-decisions-local/smoke.py --entry nimble`. It exits 2 on a host without `nvidia-smi` that isn't Apple Silicon, which is nimo today. On a supported host with `NIMBLE_DIR` (a prepared checkout with `.cache/nimble-model.json`) and `NIMBLE_PYTHON`, it runs the README priority example and expects `HIGH` and `true`. Receipt: `pipelines/smoke/nimble/latest.json`.
- **Why keep it**: It is the most transparent open alternative to the Jev slot (published data, recipe and evals), and it is the reference to compare Laya (Entry 086) against. Its contrastive data-curation method is reusable for building our own labeled Choice set for the ADR-0016 gate.
- **Non-goals**: No 18 GB weight download onto nimo in this slice. No Modal or hosted API use (that would need an account).
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| "Performs just as well" taken at face value | The X post's claim is cited as fact | Upstream's own numbers are 90.1% vs 93.2% for Jev on a narrow synthetic set. Quote those, not the post |
| Hardware assumed | Someone tries the CUDA scorer on nimo | Smoke exits 2 before loading anything. A ROCm attempt needs its own slice and the operator's OK for anything outside `~/DEVELOP` |

- **Status**: Cataloged I0. Can't run on nimo as documented upstream (smoke exits 2).
