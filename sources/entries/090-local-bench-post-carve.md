### Entry 090: Local-inference bench 2 — post BIOS/GTT carve + GLM shortlist

- **URL**: harness `examples/local-bench/bench.py` (path/`relative_to` fix). Results: a private ops note. Cases: `data/decision-gates/laya-trial.cases.v0.json` (cite **#230** only).
- **Date**: 2026-10-05 / 2026-10-06 (nimo; the operator BIOS carve + TTM same evening)
- **Source / Poster**: operator follow-up after Entry 089: remeasure under 16 GiB VRAM + ~96 GiB GTT (~107 GiB Linux RAM); research open MoE shortlist for ≤~90 GB weight budget with emphasis on Z.ai GLM Air / 5.x family; do not Feature GO.
- **Summary / Key Claims**: After the operator lowered BIOS VRAM carve 64→16 GiB and raised `ttm.pages_limit` / `ttm.page_pool_size`, Linux sees ~107 GiB and GPU-addressable ~112 GiB. Re-ran `qwen3-coder:30b` and `glm-4.7-flash`; pulled and ran `qwen3.6:35b` (~22 GB Q4_K_M). Documented that **ollama.service `MemoryHigh=40G`** still blocks 51–73+ GB weights (coder-next, gpt-oss:120b, **GLM-4.5-Air Q4 ~68–73.5 GB**) despite GTT. GLM autopsy: 4.7-flash 39.6% was **typo/invented Choice keys**, not thinking-token JSON parse failure (48/48 `parse_ok`; typo-normalized ~54.2%). Full-size GLM-4.5/4.6 (~355B) and GLM-5.3-Flash (320B/18B; Q4 ~176–200 GB, Q2 ~106+ GB) do **not** fit ≤90 GB at a usable quant; no GLM-4.6-Air released. Catalog HOLD 70–75.
- **Why it matters here**: The carve unlocked host RAM/GTT, but the Ollama cgroup still caps what we can actually load. Separating “fits 90 GB weights” from “runs under MemoryHigh=40G” prevents chasing GLM-4.5-Air / gpt-oss until the operator raises the guardrail.
- **Fit on nimo**: 18–24 GB MoEs yes under current Ollama. 51–73 GB MoEs fit the new GTT map but not the 40G MemoryHigh. GLM-5.3-Flash no.
- **Extracted Repos / Tools**: Ollama (existing). No new vendor / no TOOLS.md.
- **TOOLS.md Link**: None. **No promotion**.
- **Smoke / harness**: `python3 examples/local-bench/bench.py --check`. Receipt: `pipelines/dogfood/local-bench-2/receipt.json`. Tests: `python3 -m unittest tests.test_local_bench`.
- **Non-goals**: No Feature GO. No default-lane change (CUA-S1-FORMS). No BIOS/kernel/sysctl edits in-bot. No raise of `MemoryHigh` without the operator. No merge of build logs/weights.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| MemoryHigh=40G | Large MoE cold-load hangs | Document blocked list; ask the operator to raise MemoryHigh; unload via `keep_alive:0` |
| Relative `--outdir` | Successful run → DROP / FAIL_CANNOT_RUN | Resolve paths; try/except `relative_to` |
| GLM thinking tokens | Assumed parse failure | Autopsy: parse_ok; typo-normalize offline |
| Catalog creep | Promote on tok/s alone | HOLD 70–75; cite #230 only |

- **Status**: **I0 / trial-ran / no promotion**. Live nimo 2026-10-05 evening PT. See LOCAL-BENCH-2-RESULTS.md. Not a Feature GO.

- **Follow-up**: Entry [091](091-local-bench-memoryhigh-85g.md) — MemoryHigh=85G unlock; big MoE rebench.
