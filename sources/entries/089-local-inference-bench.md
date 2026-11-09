### Entry 089: Local-inference bench on nimo (Ollama GPU tok/s + #230 Choice set)

- **URL**: in-tree harness `examples/local-bench/bench.py` (stdlib). Decision case set: `data/decision-gates/laya-trial.cases.v0.json` (cite **#230** only).
- **Date**: 2026-10-06 (nimo dogfood slice)
- **Source / Poster**: operator request to measure already-pulled Ollama models on nimo (Strix Halo, 64 GiB BIOS VRAM carve). Not an X-intake tool.
- **Summary / Key Claims**: Run qwen2.5-coder:1.5b, glm-4.7-flash:latest, and qwen3-coder:30b through a cold load, a ~400-token prompt+decode timing, and the same 48 labeled Choice cases used in Entry 086, at gate 0.85. Optional stretch qwen3-coder-next:latest (~80B / 51 GB) only if 1–3 finish and MemAvailable stays ≥ 8 GiB. Skip gpt-oss:120b (65 GB > 64 GiB carve). Unload with `keep_alive: 0`. Never pull. Never change BIOS/kernel/sysctl.
- **Why it matters here**: nimo already has Ollama 0.30.8 on GPU and a pile of weights. This is the first receipt that records tok/s, load, peak runner RSS, and Choice accuracy/escalate/wbc on those weights against the #230 case set, plus a document-only expansion path (lower VRAM carve + TTM/GTT; current-price Halo vs Spark vs used A6000).
- **Fit on nimo**: Yes — that is the point. 30B-class Q4_K_M MoEs (~18–19 GB) fit the 64 GiB carve at `num_ctx` 2048. 120B does not.
- **Extracted Repos / Tools**: Ollama (already the local adapter). No new vendor.
- **TOOLS.md Link**: None. **No promotion**. No `data/tools.json` row, no stage card. Catalog 70–75 HOLD.
- **Smoke / harness**: `python3 examples/local-bench/bench.py --check` (Ollama down → non-zero). Full run writes `pipelines/dogfood/local-bench/receipt.json`. Tests: `python3 -m unittest tests.test_local_bench`.
- **Non-goals**: No product attach. No default-lane change (CUA-S1-FORMS stays primary local). No GUI. No Feature GO. No BIOS/kernel/sysctl. No sudo / no new services / no weight downloads.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Ollama down | Bench invents tok/s or accuracy | Fail closed (`FAIL_CANNOT_RUN`) on `/api/version` |
| Missing model name | Skip looks like a successful run | Fail closed if the tag is not in `/api/tags`; no pull |
| Load stall / OOM | One 30B hangs the slice | Drop that model after 30 min or on generate timeout; unload; continue |
| Host starved | MemAvailable collapses under the desktop | Stop further loads under 8 GiB; document |
| Confidence as correctness | High-margin wrong JSON treated as a GO | Gate 0.85; wbc counted; CUA-S1-FORMS stays default |

- **Status**: **I0 / trial-ran / no promotion**. Live on nimo 2026-10-06 (Ollama 0.30.8, ctx 2048, 48 cases, gate 0.85): qwen3-coder:30b **79.2% / 2.1% escalate / 10 wbc / 65 decode tok/s**; stretch qwen3-coder-next **83.3% / 18 tok/s**. CUA-S1-FORMS stays default. Results: a private ops note. Receipt: `pipelines/dogfood/local-bench/receipt.json`. Not a Feature GO.

- **Follow-up**: Entry [090](090-local-bench-post-carve.md) / LOCAL-BENCH-2-RESULTS.md — post BIOS/GTT carve rebench + GLM shortlist (2026-10-05).
