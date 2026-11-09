### Entry 095: Qwen3.8-Flash-Next — 180B MoE with ~6B active, low-bit GGUFs that fit nimo's GPU budget

- **URL**: https://huggingface.co/Qwen/Qwen3.8-Flash-Next (base, ~180B params in safetensors; HF card license field reads "other") · quantized GGUFs: https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF (Apache-2.0 on the card, ~2.7M downloads at this read)
- **Date**: 2026-10-06 (daily X intake)
- **Source / Poster**: @yume_arasaki, https://x.com/yume_arasaki/status/2107293459556225446 (overview) and https://x.com/yume_arasaki/status/2106204231191736763 (single DGX Spark grid)
- **Summary / Key Claims** (from the posts, not verified by us): 180B-parameter MoE that activates about 6B per token (512 experts per layer, router picks 10 plus one shared expert). Hybrid attention plus recurrent-state layers, 262k native context, MTP draft head. The poster cites Artificial Analysis intelligence index 40 vs 42 for Claude Opus 4.8, and says it beats Opus on Terminal-Bench 4.0 and AutomationBench but trails on HLE and SWE-bench Pro. Community receipts run it on llama.cpp with expert offload (e.g. 28 tok/s on an RTX 3090 + 64 GB RAM at 65k context) and on a purpose-built engine, Strata (MIT, Anthropic-compatible localhost API). Strata's receipts are all NVIDIA or Mac; AMD/ROCm/Vulkan support is not mentioned.
- **GGUF sizes we checked** (HF API, ISTA-DASLab GSQ-RCO, two shards each): Q2_0 ≈ 66.4 GB, IQ2_XS ≈ 68.0 GB, IQ3_XXS ≈ 75.8 GB, IQ3_S ≈ 83.6 GB, plus a 0.9 GB BF16 mmproj.
- **Fit on nimo**: Plausible, not proven. Since the 2026-10-05 carve-out change the GPU can address ~96 GiB GTT and models up to about 90 GB fit (Entries 090-092). Q2_0 / IQ2_XS leave room for KV cache; IQ3_S at 83.6 GB is near the edge. GLM-4.5-Air Q4 loaded fine on the no-mmap ROCm lane but produced degenerate Choice output (Entry 094), so a low-bit quant passing memory is not the same as passing quality. With ~6B active per token, decode should be far faster than a dense model of the same file size, but we have no nimo number yet.
- **Why it matters here**: `qwen3.6:35b` is the current pick on the 48-case decision benchmark (Entry 090). This is the first open model in the catalog that claims near-frontier agentic scores while fitting nimo's memory budget. If it holds up at Q2/IQ3, it could replace `qwen3.6:35b` as the local default for decisions and for the local CUA lane.
- **Extracted Repos / Tools**: https://huggingface.co/Qwen/Qwen3.8-Flash-Next · https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row, no stage card.
- **Smoke**: `QWEN38_URL=http://127.0.0.1:8080/v1 python3 examples/x-intake-local/smoke.py --entry qwen38flash`. It never loads a model itself; it needs an OpenAI-compatible server already serving the GGUF and checks an exact-token reply. Without `QWEN38_URL` it exits 2. Receipt: `pipelines/smoke/qwen38flash/latest.json`. Passing it proves serving only; quality needs the 48-case benchmark.
- **Non-goals**: No 66+ GB download from this PR, no system install, no Strata install (unverified on AMD).
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Memory edge | Q2/IQ3 plus KV cache pushes nimo past the GTT budget and locks it up | Start at Q2_0 with a small context under the 85 GB limit; document any lockup in the bench doc as the operator asked (Entries 091-092) |
| Arch support | llama.cpp ROCm or Vulkan build on nimo predates the Qwen3.8 hybrid arch and refuses the GGUF | Record the build sha and error; try the other backend before calling it unsupported |
| Low-bit quality | Loads fine but output degenerates like GLM-Air Q4 did | Score on the 48-case decision set before any promotion; keep `qwen3.6:35b` as default |
| Hype numbers | Poster's benchmark claims don't reproduce | Only our own nimo receipts count |

- **Status**: Cataloged I0. Not downloaded or run on nimo. Recommended eval-auto trial vs `qwen3.6:35b`.
