# llama.cpp ngram-mod evq1107 (2026-11-07)

## Catalog tools on the same job

The job is local decode speed on repetitive code (MVP gap L, the speed half). Gap L is that local inference has one engine, Ollama, and the strongest models need llama-server. ngram-mod does not add an engine. It is a flag on llama-server: `--spec-type ngram-mod`. No draft model and no extra weights. The 2026-10-06 ranking row 7 pairs it with the llama-server lane. The keep bar in `docs/build-dropins/pfy-mentat-toolsets.md` is 15% faster with identical outputs on 5 repetitive code prompts.

Batch-1 results under `eval/ev1107/` and `eval/catchup-1107/` do not measure this flag. Strata is the local-engine trial there. It stayed slower than Ollama (51.86 vs 61.71 tok/s, 0.84x) on a different model and different prompts.

| Tool | Stage | What it already covers | How ngram-mod compares |
|------|-------|------------------------|------------------------|
| Ollama | I2 | Default local engine. Same raw prompts, `raw: true`, temp 0, seed 7. Median 40.92 tok/s. | ngram-mod median 185.59 tok/s is 4.54x that. Ollama does not pass `--spec-type`. Text matched llama-server on all 5 prompts. |
| llama.cpp (server mode) | I1 | GGUF server in the up order. `pipelines/dogfood/local-bench-4/run_nommap_server.sh` does not pass `--spec-type`. | Flag off, same binary and same prompts: median 39.37 tok/s, in line with Ollama. The flag is the whole difference. |
| Strata | I2 | Second engine on gfx1151. Catch-up trial stayed at 0.84x Ollama. | A whole engine, not a flag. It was slower than Ollama. This flag was faster than Ollama on this copy workload. |
| Kolibri-1 | I0 | Patched llama.cpp for one MoE smoke. | A different patch. Not a decode flag. |
| LiteLLM | I2 | OpenAI-compatible proxy. | Does not decode. |
| MLX | I1 | Apple Silicon server. | This host is Linux. |
| DeepSeek V4.1 Flash GGUF | I1 | Awareness. The separate drafter file is not the model, and the weights do not fit nimo. | Draft-model speculative decoding needs a second file. ngram-mod does not. |
| Laguna-S-2.1 | I1 | Large local coding weights. Notes mention DFlash draft models. | Needs weights this lane did not load. |
| harness2 | I1 | Decision bench on its own llama-server. | Does not set this flag. |

## Verdict

PROMOTE I2. Median decode with `--spec-type ngram-mod` was 185.59 tok/s. The same server with `--spec-type none` was 39.37 tok/s. The ratio is 4.71x. All 5 generations were identical. The bar is 1.15x and 5/5 identical. Ollama on the same prompts was 40.92 tok/s, so the flag also beat the engine we already run.

This is not I3. The lane must not wire a gate. I3 in this ticket also needs a product script plus self_pipeline evidence. The probe script is the measurement. It is not a product smoke, and this flag is not a CI or review tool.

## Pins

Install root: `~/.cache/pfy/tools/llama-cpp-ngram-mod/`. The server child got `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` under that root. No clone, no build, no sudo, no account. The runnable binary is the one already on the host. `pin.json` in that root records the same hashes as `results.json`.

- Upstream commit `6f3a9f3dee3c27545371044a3a38005721ac8a8e` on `ggml-org/llama.cpp` (2026-06-04, "server: avoid unnecessary checkpoint restore when new tokens are present (#24110)"). `llama-server --version` printed `version: 1 (6f3a9f3de)`, which is that commit.
- Binary `/usr/local/lib/ollama/llama-server` sha256 `dbfeea380cdc1de9bbfe32399befbcd8381a3c5ac83e573d79d0fa41bdc40037`.
- `libllama-server-impl.so` sha256 `9cd25af56b2ecc46ed412261229ae4c7c2bda19b99da7430be496e81c23e1784`.
- `libllama.so.0.0.1` sha256 `35917ae8f9566b7a198c900a928c73dc08dc9806187b89913504c71b92da1088`.
- Ollama 0.30.8. HIP backend `/usr/local/lib/ollama/rocm_v7_2/libggml-hip.so`. The log enumerated `ROCm0 : Radeon 8060S Graphics`. Start flags included `-ngl 999`.
- Debian `llama.cpp-tools 8681+dfsg-1` also has `--spec-type ngram-mod` and only CPU backends. It was not used for the smoke.
- Model `qwen2.5-coder:7b-instruct`. Blob `/usr/share/ollama/.ollama/models/blobs/sha256-60e05f2100071479f596b964f89f510f057ce397ea22f2833a0cfe029bfc2463`, 4683074048 bytes. Streaming sha256 matched the blob name. `qwen3.6:35b` is 22 GB and was not loaded.
- Entry 051 names `--spec-ngram-simple-size-n` and `--spec-ngram-simple-size-m`. This build still has those flags for `ngram-simple` (defaults 12 and 48). `ngram-mod` uses its own defaults: `n_match=24`, `n_min=48`, `n_max=64`. The probe passed `--spec-type` only, so those defaults applied. The log line was `mod size=4194304 (16.000 MB)`.

There is no `sources/entries/051-*.md`. The entry text lives in shared `sources/x-posts.md`. This lane did not edit that file.

## Commands

```bash
scripts/model_lock.sh python3 eval/evq1107/llama-cpp-ngram-mod/ngram_probe.py live
```

The probe hashed the blob, waited until `ollama ps` was empty and MemAvailable was at least the file size plus 25 GiB, then ran llama-server twice on `127.0.0.1:18151` (`--spec-type none`, then `--spec-type ngram-mod`). Each request was `/completion` with temperature 0, top_k 1, seed 7, repeat_penalty 1, n_predict 256, stop `# END`. After both servers exited, it called Ollama `/api/generate` with `raw: true` and the same sampling. The model was not loaded, so the body sent `keep_alive: "2m"`. The probe does not call `ollama stop`.

At the start of the lock, `ollama ps` showed `qwen2.5-coder:7b-instruct` already resident (100% GPU, until 2 minutes). The probe waited. Nine polls at 20 seconds, 180 seconds, then ps was empty and MemAvailable was about 76 GiB (need about 29.4 GiB). The other holder was not unloaded.

Server child env followed `pipelines/dogfood/local-bench-4/run_nommap_server.sh`: `HSA_OVERRIDE_GFX_VERSION=11.5.1`, `GGML_BACKEND_PATH` pointed at `libggml-hip.so`, `GGML_CUDA_ENABLE_UNIFIED_MEMORY=1`, `GGML_HIP_UMA=1`, `--no-mmap`, `-c 2048`, `-fa on`.

## Numbers

Decode tok/s is `timings.predicted_per_second` for llama-server and `eval_count / eval_duration` for Ollama. The headline ratio is the median of the five on-rates divided by the median of the five off-rates, not the median of the five ratios. Generation wall starts after `/health` and does not include model load.

| Prompt | Off tok/s | On tok/s | On/off | Ollama tok/s | Identical on vs off | Matched the requested lines |
|--------|----------:|---------:|-------:|-------------:|:-------------------:|:---------------------------:|
| repeat-load-rows | 38.98 | 147.12 | 3.77x | 39.06 | yes | yes |
| repeat-clamp-scores | 41.65 | 349.85 | 8.40x | 40.92 | yes | yes |
| repeat-merge-maps | 35.64 | 296.37 | 8.32x | 40.60 | yes | yes |
| edit-retry-delay | 39.78 | 116.01 | 2.92x | 41.14 | yes | no |
| edit-row-label | 39.37 | 185.59 | 4.71x | 41.17 | yes | yes |
| Median | 39.37 | 185.59 | 4.71x | 40.92 | 5/5 | 4/5 |

Generation wall: off 21.161 s, on 6.049 s, Ollama 26.577 s.

`edit-retry-delay` asked for `time.sleep(4)` and all three engines wrote `time.sleep(4)  # Use 4 instead of 3` plus the rest of the function. The extra comment is why the gold check failed. The three texts still matched each other. The flag did not change the text.

Draft acceptance from the ngram-mod server log (accepted / generated draft tokens):

| Prompt | Accepted / generated | Rate |
|--------|---------------------:|-----:|
| repeat-load-rows | 128 / 128 | 1.00 |
| repeat-clamp-scores | 128 / 128 | 1.00 |
| repeat-merge-maps | 151 / 192 | 0.79 |
| edit-retry-delay | 91 / 192 | 0.47 |
| edit-row-label | 146 / 256 | 0.57 |
| All five (server totals) | 644 / 896 | 0.72 |

The log also recorded 14 generated drafts and 14 accepted drafts across the five calls. Prompt token counts were 184 to 265, above the match length of 24.

## Gates

Value (3 of 4 required, all four hold for this workload):

1. Gap fill. It does not add a second engine, so it does not by itself close "Ollama cannot hold the big model." It does close the speed hole the ranking named: free decode on repetitive code, and on these prompts it is several times Ollama.
2. Operator leverage. One flag on the server we already start. No new service.
3. Evidence. This probe, with pins and per-prompt rates.
4. Blast radius. 16 MB table, no weights in git, MIT llama.cpp, opt-in. The product path is unchanged.

Modularity (all four):

1. Local code needed. The speed is a measurement on this GPU, not a docs claim.
2. Bounded surface. One flag and three size defaults.
3. Isolatable. Cache pin plus the existing binary. Not the product runtime.
4. Reversible. Delete the cache dir. The card and this report stay.

The computed A-tier ceiling in `scripts/catalog_stage_eval.py` stays I1. The stage is I2 because this probe cleared the ticket bar. `catalog_check.py` does not reject a stage above that ceiling. A later `--apply` does not lower `integration_stage`.

I2 size gate: nothing from llama.cpp was copied into the repo. The in-repo files are the probe, the test, this report, and the card.

## Risks

| Risk | How it fails | How we recover |
|------|----------------|----------------|
| Best-case prompts | The continuation is in the prompt. A mixed coding sample may sit under 1.15x. | The flag stays off the product server until that sample is measured. |
| Gold miss on one edit | The model added a comment. A caller that needs exact bytes can still see a "faster" wrong edit. | Compare on vs off, which matched. Do not treat the flag as a better editor. |
| Host busy | Another model is resident, or MemAvailable is under file size plus 25 GiB. | The probe waits up to 30 min, then writes HOST-BUSY and skips. It does not call `ollama stop`. This run waited 180 s. |
| Server missing or down | A missing binary, a help text without `ngram-mod`, or `/health` never returning. | Status `skipped`, exit 0, no speed number. `tests/test_llama_cpp_ngram_mod_probe.py` covers those three with stubs. |
| Ollama ps unread | If both the HTTP ps and `ollama ps` fail, the probe still starts llama-server when memory is enough. | The mem floor still applies. This run read ps and waited. |
| Pin drift | An Ollama upgrade changes the commit in `--version`. | Re-run the probe. Do not assume 4.71x on a new build. |

## Next gate

Stay I2. Do not add the flag to `run_nommap_server.sh` or to any Make target in this lane. A later ticket can offer it as an opt-in after a mixed prompt set still clears 1.15x with identical greedy text.

## Five questions (this tool in the pipeline)

1. What triggers it? Nothing today. A later opt-in would be the llama-server start command passing `--spec-type ngram-mod` for a repetitive edit. Pregate does not call it.
2. What does it do, and which services does it read and write? llama-server drafts from a 16 MB table over the current context. It reads the GGUF and writes tokens to the caller. No account and no second model.
3. What does it trigger next? The caller reads the completion. Nothing else starts.
4. Where does a human re-enter? If a mixed-prompt run drops under 1.15x or the texts diverge, leave the flag off. Turning it on for the product lane is a separate ticket.
5. What stops two runs doing the same work? `scripts/model_lock.sh` holds `~/.cache/pfy/locks/local-model.lock` for the whole live step. One server, one port. Two servers would be two loads, and the lock stops that.
