# Entry 094 — GLM-Air score + runtime matrix (nimo)

- **Date**: 2026-10-06 (PT)
- **Cite**: #230 · base `e009030` · branch `bot/local-bench-5`
- **Summary**: Completed GLM-4.5-Air Q4 on no-mmap ROCm (memory OK, **Choice quality fail / degenerate GGGG**). Runtime matrix on qwen3.6:35b: Ollama vs llama.cpp ROCm vs Vulkan; Lemonade skipped (no local weights); vLLM blocked (ROCm 7.1 vs rocm723 wheel + missing libs). Folded #273 nits.
- **Status**: I0 / trial-ran / no promotion. Not Feature GO.
- **Artifacts**: a private ops note, `pipelines/dogfood/local-bench-5/receipt*.json`, `stalls.json`
