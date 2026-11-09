# Entry 092 — local-bench edge probe (nimo / no-double-load)

- **Date**: 2026-10-05/06 (PT)
- **Cite**: #230 · stacks #272 · PR #273 · branch `bot/local-bench-4`
- **Summary / Key Claims**: One-at-a-time edge probe of qwen3-coder-next (51G), gpt-oss:120b (65G), GLM-4.5-Air Q4 (~73G) under MemoryHigh=85G + 30m load timeout. **Extended with no-double-load path**: Ollama-bundled `llama-server` + ROCm HIP `--no-mmap -ngl 999` + `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1`. Ollama defaults double-held ~51GB (RSS+GTT) and never became ready; no-mmap hosts **51GB RAN** (Choice 83.3%) and **65GB RAN** (memory OK, Choice weak). Air SKIP (incomplete pull). Catalog HOLD. Not a Feature GO.
- **Method**: `pipelines/dogfood/local-bench-4/run_nommap_server.sh` + `bench_llamacpp.py` (48 #230 cases, gate 0.85). PeakSampler for RSS/GTT/MemAvailable/swap. Stalls documented in `stalls.json`.
- **Status**: **I0 / trial-ran / no promotion**. Ollama-default edge ~22 GB remains for that loader; **no-mmap hardware edge ≥51 GB** (coder-next). Not a Feature GO. See LOCAL-BENCH-4-EDGE.md.
- **Artifacts**: a private ops note, `pipelines/dogfood/local-bench-4/receipt*.json`, `peak-*.json`, `stalls.json`
