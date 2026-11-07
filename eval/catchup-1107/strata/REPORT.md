# Strata catch-up trial (2026-11-07)

Host nimo (AMD Strix Halo, gfx1151). Branch `bot/catchup-strata-1107`. Weights, the engine, and the install stay under gitignored `tmp/strata/`.

## What ran

Strata terminal v0.2.12 installed under `tmp/strata/` with `STRATA_DATA_DIR`, `STRATA_BIN_DIR`, `STRATA_HOME`, and `HOME` all pointed at that tree. `install.sh` matches SHA256SUMS (`d47754af1f74c95bf763e0b8d484232443466decd1a22d0be3208760a2f53822`). The control tarball `strata-control-0.1.58-linux-x86_64.tar.gz` matches (`fcce4c7b90f59c4f10f16181a7190b3abe79faadbc9eef38278fdc635e028817`, 99974029 bytes). The AppImage was not downloaded. The hip-halo engine tarball was not kept, so its release digest was not re-hashed. SHA256SUMS lists `strata-engine-0.1.58-linux-x86_64-hip-halo.tar.gz` as `1ce376c443ef662c72cd1fc4f828e093f78f83498c946837ca22cc250eda8861`. The installed entrypoint matches `engine-component.json`: 52350928 bytes, sha256 `1f22831cc4b017d4fa8e4662537e54125387abd829cacd939f9a3796b6a88e05`, build `7be42963e6be+rocm`, arch gfx1151.

Ollama's `qwen3.6:35b` blob (`sha256-d372de8e934898a59e6ccfabc3368474711384d8f1fd4d22d87a3f0a45400cdc`) was left read-only. Strata refused it. The raw blob plan said model import needs a GGUF file or directory. A symlink named `qwen3.6-35b-q4_k_m.gguf` was refused as a model type the engine does not support. The trial then used Unsloth `qwen36` / `UD-Q4_K_XL` (22.9 GB class, the closest documented 4-bit pack). The file is 22853663008 bytes. Its sha256 is `55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1`, matching the `.done` sidecar.

`eval/catchup-1107/strata/bench.py` sent the same six prompts, three runs each, temperature 0, streaming, to both OpenAI-compatible servers. Ollama ran first with `keep_alive` `2m` because that model was not already loaded. Strata then served on `127.0.0.1:18158` (`--access local`, context 8k, vision off, parallel 1, MTP on, tune skip). The two engines were not loaded together. A non-tool run is valid when the reply text is non-empty. Tool validity means the first tool call is `get_weather` and its arguments parse as a JSON object. The tool request set `tool_choice` to `required`.

Five of the six prompts stopped at `max_tokens` while the text head was still the thinking trace. Code and chat caps are 128 or 64. The long prompt cap is 64. The tool prompt finished under its 256 cap. The saved benches stay 18/18 because each run had non-empty text. Both engines used the same caps, so the decode ratio still compares them.

`plan-qwen36-ud-q4.json` is the plan from before the gfx1151 engine was installed. That plan names port 8080 and `engine_missing` true. The benched server was `127.0.0.1:18158` after the engine and the GGUF were on disk. `models-list.json` is the local-run list from before the pack existed. Its `model_count` is 0. The bench used the GGUF under gitignored `tmp/strata/models`.

`./pfy launch --headless` then smoked that server with a fresh `PFY_STATE_DIR` under `tmp/`, and with `HOME`, `GROK_HOME`, and `XDG_*` under `tmp/pfy-strata-home`. The pin was the existing `LOCAL_OPENAI_BASE_URL` plus `PFY_LOCAL_RUNTIME=strata`. There is no `PFY_ENGINE=strata` and no `PFY_STRATA_BASE`. The session was stopped with `./pfy launch stop` on that same state dir. Strata was then stopped with `strata launch --stop` under the same `STRATA_*` env. Port 18158 was closed afterward. `ollama ps` was empty.

Optional plan only: `strata launch --plan --family qwen --model q2_0` for Qwen3.8-Flash-Next ISTA Q2_0. Nothing was downloaded.

## Numbers

Decode tok/s is `(completion_tokens - 1) / time from first token to stream end`. Prompt tok/s is `prompt_tokens / TTFT`. The engine median is the median of every run.

| Engine | Valid | Decode tok/s | Prompt tok/s | TTFT s | Wall s |
| --- | --- | --- | --- | --- | --- |
| Ollama `qwen3.6:35b` | 18/18 | 61.71 | 92.83 | 0.334 | 2.433 |
| Strata UD-Q4_K_XL | 18/18 | 51.86 | 211.85 | 0.151 | 2.599 |

Decode ratio 51.86056934668894 / 61.70660442016066 = 0.840. The promote bar is 0.90 (55.54 tok/s). Every prompt is under 0.90: code-1 0.835, code-2 0.859, chat-1 0.798, chat-2 0.798, tool-1 0.886, long-4k 0.665.

The tool prompt returned `get_weather` with arguments `{"city":"Lisbon"}` on all three runs of both engines. That prompt counted 290 tokens on Ollama and 282 on Strata. The user text and the tool schema were the same. Each server wraps them in its own chat template.

Ollama's long-prompt median (4027 tokens, about 13699 tok/s, TTFT 0.294 s) is a warm prefix cache. Run 1 was 518 tok/s and TTFT 7.77 s. Runs 2 and 3 were about 13700 tok/s. Strata's three long runs stayed about 848 to 862 tok/s with TTFT about 4.7 s. Short-prompt Strata prompt speed and TTFT beat Ollama. The promote gate is decode only, and decode fails on the short prompts as well.

Ollama's first request loaded the model. `code-1` run 1 had TTFT 21.98 s and prompt speed 1.36 tok/s. Decode on that run was 59.35 tok/s. The load sits outside the decode span. The published figures are medians, so that one load does not set the decode number.

pfy launch JSON: `ok` true, `smoke_ok` true, `smoke_field` `content`, `models_ok` true, `usable` true, model `qwen3.6-35b-a3b-ud-q4_k_xl`, base `http://127.0.0.1:18158/v1`, session `pfy-grok-cbe7a3`, pid 110677. Stop JSON: `stopped` true, live `STOPPED`, same pid. That pid was the grok this launch spawned. Operator state under `/home/mark/.pfy-mentat` was not used.

Qwen3.8 plan: profile `launch-q2_0-128k`, context 131072, vision gpu, engine already usable. Download would be 68.5 GB (weights 66.4, picture reader 0.9, DFlash2 drafter 1.2). `downloaded` is false. Upstream lists that pack at 37.6 GB RAM+VRAM, which is the resident figure, not the download.

## Verdict

`STAY I2 median decode 51.86 tok/s is 0.84x Ollama 61.71 tok/s on the same prompts (bar 0.90x)`

The server ran on nimo, so the stage is I2. Tool calls were valid and the pfy smoke passed. Decode missed the bar, so step 6 (opt-in `PFY_ENGINE=strata`, status detection, tests, `docs/ops/strata-engine.md`) was not built. No TOOLS.md row.

## Risks

Upstream warns that UD-Q4_K_XL on a Ryzen AI Max can stop on the first request after a start. This server survived warmup, 18 bench requests, and the pfy smoke. A later start can still hang. UD-IQ4_XS is the upstream stable pick and was not the pack under test.

pfy found this server only because `LOCAL_OPENAI_BASE_URL` was set and FreeToken, llama-swap, and llama-server were not answering. `PFY_LOCAL_RUNTIME=strata` alone does not select port 18158. pfy never starts or stops Strata.

The hip-halo tarball digest was not re-checked after install. The installed entrypoint hash was checked against the component manifest.

Prompt-speed medians are not comparable on the long prompt, because Ollama cached the prefix after run 1.

## Next gate

Stay I2 until a later same-prompt trial on this host reaches at least 0.9x Ollama decode. A pass can then add an opt-in that detects a server the operator already started (`PFY_STRATA_BASE`, and `strata --status` when the binary is on `PATH`). pfy must not start, stop, download, or update Strata. Ollama stays the default. Do not download Qwen3.8 or DeepSeek on this host for that gate. Do not commit weights.
