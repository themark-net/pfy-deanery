# MVP-1031 DeepSeek-V4.1-Flash-1017 fit gate

Branch `bot/mvp-dsv4-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-dsv4-1031`. Host `nimo`. Measurement clock 2026-11-01T00:04:13Z. No weights downloaded. No server started. No `./pfy build --local` pass.

## Verdict

NO-GO as a local default on this host.

The claim that the Unsloth Dynamic V3.1 GGUF runs at "Claude Sonnet 5.5 level" in 64GB+ RAM is still unverified marketing. The smallest full quant does not fit nimo RAM+VRAM under the lane rule (file size plus about 8 GB of context). Steps 3 through 7 did not run. There is no token rate, no load time, and no per-task gate.

## Repo

| Field | Value |
|-------|--------|
| Hugging Face | https://huggingface.co/unsloth/DeepSeek-V4.1-Flash-1017-GGUF |
| API id | `unsloth/DeepSeek-V4.1-Flash-1017-GGUF` |
| API sha | `8a6ec9cf118e` |
| Private / gated | no / no |
| License tag | mit |
| Unsloth post | https://x.com/UnslothAI/status/2116156587404562491 |
| Claim post | https://x.com/0x0SojalSec/status/2116263439681417554 |
| Guide | https://unsloth.ai/docs/models/deepseek-v4.1-flash |

Sizes are byte lengths from the Hugging Face tree API (`/api/models/.../tree/main/<quant>`), fetched 2026-11-01. Per-shard bytes are in `eval/mvp-1031/dsv4/fit-receipt.json`.

| Quant | Shards | Bytes | Decimal GB |
|-------|--------|------:|----------:|
| UD-IQ1_S | 5 | 232979608420 | 232.980 |
| UD-IQ1_M | 5 | 250404346724 | 250.404 |
| UD-IQ2_XXS | 6 | 300475464795 | 300.475 |
| UD-Q2_K_XL | 7 | 334793544836 | 334.794 |
| UD-IQ3_XXS | 7 | 394736596867 | 394.737 |
| UD-IQ3_S | 8 | 423631019994 | 423.631 |
| UD-Q3_K_XL | 8 | 485068639215 | 485.069 |
| UD-Q4_K_XL | 9 | 500707576573 | 500.708 |
| UD-Q8_K_XL | 9 | 508376763197 | 508.377 |

UD-IQ1_S shard names:

| File | Bytes |
|------|------:|
| `UD-IQ1_S/DeepSeek-V4.1-Flash-1017-UD-IQ1_S-00001-of-00005.gguf` | 5780868 |
| `UD-IQ1_S/DeepSeek-V4.1-Flash-1017-UD-IQ1_S-00002-of-00005.gguf` | 49120285248 |
| `UD-IQ1_S/DeepSeek-V4.1-Flash-1017-UD-IQ1_S-00003-of-00005.gguf` | 48899707008 |
| `UD-IQ1_S/DeepSeek-V4.1-Flash-1017-UD-IQ1_S-00004-of-00005.gguf` | 24358544704 |
| `UD-IQ1_S/DeepSeek-V4.1-Flash-1017-UD-IQ1_S-00005-of-00005.gguf` | 110595290592 |

Separate Engram files (not added on top of a quant; the matching shard is already inside each quant):

| File | Bytes |
|------|------:|
| `engram/DeepSeek-V4.1-Flash-1017-engram-IQ4_NL.gguf_file` | 110595290592 |
| `engram/DeepSeek-V4.1-Flash-1017-engram-Q5_K.gguf_file` | 135172021792 |
| `engram/DeepSeek-V4.1-Flash-1017-engram-Q6_K.gguf_file` | 161284798692 |
| `engram/DeepSeek-V4.1-Flash-1017-engram-MXFP8.gguf_file` | 202758032592 |

Not candidates: `dspark-DeepSeek-V4.1-Flash-1017-Q8_0.gguf` is 7976914240 bytes and `dspark/dspark-DeepSeek-V4.1-Flash-1017-BF16.gguf` is 8506281280 bytes. Those are the speculative drafter, not the 552B model. `mmproj-BF16.gguf` is 972208288 bytes and `mmproj-F16.gguf` is 971004064 bytes.

## Host

| Field | Value |
|-------|--------|
| Host | nimo |
| Cores | 32 |
| Load at 2026-11-01T00:04Z (1m 5m 15m) | 3.54 3.83 4.99 |
| MemTotal | 112641192 kB = 115344580608 bytes (107.423 GiB) |
| MemAvailable | 74340952 kB = 76125134848 bytes (70.897 GiB) |
| SwapTotal / SwapFree | 8388604 kB / 96 kB |
| GPU | AMD, `rocm-smi` present, `nvidia-smi` absent |
| VRAM total | 17179869184 bytes (16 GiB) |
| VRAM used | 3714129920 bytes |
| VRAM free | 13465739264 bytes |
| RAM+VRAM | 132524449792 bytes (123.423 GiB) |
| Disk available on `/home` | 479862718464 bytes (446.907 GiB) |
| `_vendor/models` | absent at measurement |

Host pressure exit did not fire. MemAvailable stayed above 16 GiB. Load stayed under 2x cores (64). Swap was already full. That is recorded so a later load is not attempted on top of a full swap.

## Fit rule

Lane rule: largest quant whose file size plus about 8 GB of context fits RAM+VRAM, and which leaves at least 50 GB free disk after download.

Context overhead used here: 8 GiB = 8589934592 bytes.

| Check | Bytes | Result |
|-------|------:|--------|
| Smallest quant UD-IQ1_S | 232979608420 | candidate |
| Plus 8 GiB | 241569543012 | required |
| RAM+VRAM | 132524449792 | budget |
| Shortfall | 109045093220 | 101.556 GiB over budget |
| Disk after UD-IQ1_S | 246883110044 | above 50 GB (50000000000) and above 50 GiB (53687091200) |

Every larger quant is a bigger file. None fit RAM+VRAM. Disk is not the blocker.

The UD-IQ1_S last shard equals the IQ4_NL Engram file (110595290592 bytes). Dropping that shard would leave a 122384317828 byte backbone. Backbone plus 8 GiB is 130974252420 bytes. That is 1550197372 bytes (1.444 GiB) under total RAM+VRAM and 54849117572 bytes (51.082 GiB) over MemAvailable. SwapFree was 96 kB. This lane does not treat that as a fit. The drop-in counts the file.

The operator weight pool is 250 GB (`docs/ops/local-model-storage-and-eval.md`). UD-IQ1_S at 232.980 decimal GB would fill that pool. That is a second reason to skip the download. The RAM rule already stopped the lane.

## Steps

| Step | Result |
|------|--------|
| 1 Find the repo | Found. Table above. |
| 2 Measure and pick a quant | No quant fits. Stop. |
| 3 Download | Skipped. |
| 4 Serve | Skipped. No pid. Nothing to stop. |
| 5 Smoke | Skipped. No tokens/s. No load time. |
| 6 MVP-3 six tasks | Skipped. |
| 7 Compare | No new task numbers. Prior baselines stand. |

MVP-3 tasks left unrun: t1 smolvm stderr first, t2 tree_sig 119, t3 daemon stop fail, t4 timeout substep, t5 receipts outside repo, t6 tree_sig three.

## Comparison

| Arm | Gate | Loop accept | Human accept | Wall |
|-----|------|-------------|--------------|------|
| MVP-3 local (`eval/mvp3/REPORT.md`) | 5/6 | 5/6 | 4/6 | 3859.9 s |
| MVP-2 cloud (same report) | 6/6 | 6/6 | 6/6 | 583.6 s |
| This GGUF on nimo | not run | not run | not run | 0 s |

Human reading of a diff: none. There is no diff.

The prior local model (`qwen3.6:35b` in the MVP-3 report) remains the measured local point. This GGUF does not replace it.

## Catalog

`TOOLS.md` row `DeepSeek-V4.1-Flash-1017 GGUF`. Scores are the CATEGORIZATION.md weights applied to what this host could check, not to Unsloth's benchmark table.

| Stage | Score | Why |
|-------|------:|-----|
| S1 | 40 | A GGUF and a llama.cpp path are published. No chat and no tool call ran here. |
| S2 | 20 | No tokens/s. The file does not fit the lane's 64 GB-class rule or this host. |
| S3 | 50 | Integration would be the existing llama.cpp server. It was not wired. |
| S4 | 70 | Public docs, MIT, HF repo, posts on 2026-10-30. |
| Overall | 42 | 0.35*40 + 0.25*20 + 0.25*50 + 0.15*70 |
| Tier | D | Below the C band (50-64). Stage I0. |

Not added to `data/tools.json`. That file is the ADR-0015 slim subset. I1 is the stage that pins a JSON row.

## How this fails / how we recover

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Someone downloads UD-IQ1_S anyway | The 233 GB file fills the 250 GB pool and the load OOMs on a full swap | Do not download. The receipt's `fits` field is false |
| A later host is large enough and this report is treated as a quality NO-GO | A real MVP-3 pass never happens | The quality claim is unmeasured. On a host that passes the byte check, run one locked `./pfy build --local` pass and replace this verdict |
| Catalog scores get quoted as a benchmark | 42 is read as a model-quality score | The notes say the claim was not measured. Re-score only after a task pass |

## Gate

Docs and catalog only. Reviewer plus pregate. This lane did not run `scripts/pregate.sh` (the drop-in says the operator runs it). `python3 scripts/catalog_check.py` is the catalog lint.
