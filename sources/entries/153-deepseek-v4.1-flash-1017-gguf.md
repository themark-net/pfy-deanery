### Entry 153: Unsloth Dynamic V3.1 GGUF of DeepSeek-V4.1-Flash-1017

- **URL**: https://huggingface.co/unsloth/DeepSeek-V4.1-Flash-1017-GGUF (public, not gated, MIT). Model API sha `8a6ec9cf118e` at fetch time 2026-11-01.
- **Date**: 2026-10-31 PT lane `mvp-dsv4-1031`. Upstream Dynamic V3.1 post is 2026-10-30.
- **Source / Poster**: Claim post https://x.com/0x0SojalSec/status/2116263439681417554 (2026-10-30 20:18 UTC) quotes that author's own post https://x.com/0x0SojalSec/status/2116262927858884739, which links the Hugging Face repo. Unsloth's post is https://x.com/UnslothAI/status/2116156587404562491 (2026-10-30 13:13 UTC). Daniel Han's note is https://x.com/danielhanchen/status/2116162363313525191. Guide: https://unsloth.ai/docs/models/deepseek-v4.1-flash.
- **Summary / Key Claims** (upstream, unverified here): Dynamic V3.1 GGUFs of DeepSeek-V4.1-Flash-1017 (552B MoE backbone plus a 196B Engram table) "run on 64GB+ RAM" and are described by the claim post as "Claude Sonnet 5.5 level". Unsloth's own table lists UD-IQ1_S at about 233 GB and UD-Q8_K_XL at about 508 GB. This lane did not reproduce any benchmark number.
- **Why it matters here**: The lane asks whether this GGUF can be the local model for the MVP-3 six-task set on nimo (107 GiB RAM, 16 GiB VRAM).
- **Fit on nimo**: No. Smallest full quant UD-IQ1_S is 232979608420 bytes. RAM+VRAM is 132524449792 bytes. File plus 8 GiB context is 241569543012 bytes, short by 109045093220 bytes. Disk would have allowed the download (about 447 GiB free, 50 GB reserve still held). See `eval/mvp-1031/dsv4/REPORT.md`.
- **Verified on nimo**: Hugging Face tree API file sizes, `/proc/meminfo`, `rocm-smi` VRAM, `df`. No download, no server, no `./pfy build --local` pass.
- **Findings**:
  - The last shard of UD-IQ1_S is 110595290592 bytes, the same size as `engram/DeepSeek-V4.1-Flash-1017-engram-IQ4_NL.gguf_file`. Unsloth documents Engram SSD offload. This lane still counts the whole quant file, because the drop-in says file size plus about 8 GB.
  - `dspark-DeepSeek-V4.1-Flash-1017-Q8_0.gguf` is 7976914240 bytes. That is the speculative drafter, not the model.
  - Swap was already full (SwapFree 96 kB) at measurement. MemAvailable was about 71 GiB.
- **Extracted Repos / Tools**: https://huggingface.co/unsloth/DeepSeek-V4.1-Flash-1017-GGUF
- **TOOLS.md Link**: `DeepSeek-V4.1-Flash-1017 GGUF`, tier D, overall 42, stage I0. Not in `data/tools.json` (ADR-0015 slim subset; I1 is the stage that pins JSON).
- **Smoke**: Not run. Fit gate stopped the lane before download.
- **Non-goals**: No download on nimo, no local default, no Feature GO, no weights in git, no signal to Mark's Ollama.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| A later reader treats the marketing line as a measured result | Someone sets this GGUF as `LOCAL_CODER_MODEL` and the host swaps or OOMs | The catalog row is I0 / NO-GO. The receipt stores the byte inequality. Stay on the current local default until a larger host passes the same fit rule |
| Engram mmap is assumed to make the 233 GB file fit in 64 GB | A download starts, then load fails, and the 250 GB weight pool is full | Do not subtract the engram shard unless a new drop-in says to. Re-measure RAM+VRAM against the whole file |
| Entry number clash | Another lane also takes 153 | 150-152 were already on other branches at fetch time. `scripts/catalog_check.py` rejects two files with the same NNN |

- **Status**: Cataloged I0. Found, does not fit, not measured. NO-GO as a local default.
