### Entry 091: Local-inference bench 3 — MemoryHigh=85G unlock (big MoEs)

- **URL**: harness `examples/local-bench/bench.py`. Results: a private ops note. Cases cite **#230** only. Stacks on Entry [090](090-local-bench-post-carve.md) / merged #271 (`357e3c6`).
- **Date**: 2026-10-05 evening PT (nimo)
- **Source / Poster**: Mark raised ollama `MemoryHigh` 40G→**85G**; removed unused models; rebench previously blocked gpt-oss:120b, qwen3-coder-next, GLM-4.5-Air Q4. Mid-slice: nimo lockup ~11:05pm PT + concurrent atg-framework Grok Build → raised MemAvailable floor to **16 GiB**; defer unsafe big loads.
- **Summary / Key Claims**: MemoryHigh=85G **allows** attempting 51–65 GB loads (no 40G cgroup hang), but ollama **llama-server start timeout** (~8–10 min) DROPs coder-next and gpt-oss before ready. GLM-4.5-Air **deferred: host contention** (pull incomplete). `qwen3.6:35b` **RAN** 79.2% / 0% esc / parse_ok 48 (tok/s contention-degraded vs Entry 090). Gate nits: receipt records MemoryHigh=85G + per-model `parse_ok`; relative `--outdir` unit tests; docs reconciled to receipt numbers. Catalog HOLD 70–75. Not a Feature GO.
- **Why it matters here**: Separates “cgroup allows RSS” from “ollama becomes ready.” Next unlock is `OLLAMA_LOAD_TIMEOUT`, not more BIOS carve.
- **Fit on nimo**: 22 GB MoEs yes. 51–73 GB MoEs need longer load-timeout + quiet host (one-at-a-time, MemAvailable ≳ size+25 GiB, floor 16 GiB).
- **Extracted Repos / Tools**: Ollama (existing). No TOOLS.md.
- **Smoke / harness**: `python3 -m unittest tests.test_local_bench`. Receipt: `pipelines/dogfood/local-bench-3/receipt.json`.
- **Status**: **I0 / trial-ran / no promotion**. Coding worker still **qwen3.6:35b**; decision **CUA-S1-FORMS**. See LOCAL-BENCH-3-RESULTS.md “models to point atg-framework at”. Not a Feature GO.

- **Follow-up**: Entry [092](092-local-bench-edge-probe.md) — OLLAMA_LOAD_TIMEOUT=30m edge probe.
