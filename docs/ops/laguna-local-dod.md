# Laguna S 2.1 - local evaluation Definition of Done (T-0062)

**Status:** DoD written 2026-07-30 · **Smoke lab:** issue #25 (hardware-gated)  
**Model:** https://huggingface.co/poolside/Laguna-S-2.1 · Entry 073 · **Pool:** ≤250 GB ([local-model-storage-and-eval.md](local-model-storage-and-eval.md))

## Hardware (document before pull)

| Item | Guidance |
|------|----------|
| Disk | GGUF/MLX quant size + 20% free; fit inside 250 GB **pool** with minis retained |
| RAM/VRAM | Prefer quant that leaves headroom for concurrent mini coders |
| Runtime | Ollama **or** llama.cpp server → LiteLLM |

## DoD checklist (lab green)

- [ ] Suitability note (external benches + X-post argument) under catalog or this doc  
- [ ] Weights **outside** git (ADR-0003); path recorded in operator env only  
- [ ] `ollama pull` / llama.cpp load succeeds; one completion via OpenAI-compatible API  
- [ ] LiteLLM route smoke (or direct Ollama)  
- [ ] `make eval-suite` or subset with model as optional matrix column (SKIP if not gate)  
- [ ] Golden validate still green; no weights committed  
- [ ] Mini models still present for concurrent low-tier work  

## Non-goals

- Not primary gate until proven vs qwen/deepseek coders on golden+implement  
- No full MoE weights in catalog repo

## Smoke note (2026-10-30 PT, issue #25)

Catalog text only. The checklist above is still open. This run did not pull Laguna, did not start llama.cpp or Ollama for it, and did not send a completion. MVP-3 run 2 had a model loaded for a timing trial, so a pull was out of scope. No weights were added to the repo. T-0062 stays hardware-gated. Issue #25 stays open until a later lab checks the boxes and writes a receipt.  
