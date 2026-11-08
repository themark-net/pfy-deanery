# colibri evq1107

Host nimo (AMD Strix Halo, gfx1151, Radeon 8060S). Branch `bot/evq-colibri-1107`. No account, no API key, no hosted model. The binary and the import stay under `~/.cache/pfy/tools/colibri/`. Nothing from that cache is committed.

## Catalog comparison

Same job: a local OpenAI-compatible inference server, especially a second engine next to Ollama for gap L in `docs/eval/TOOLSET-RANKING.md` (2026-11-07). Gap L is that local inference has one engine, and the strongest models that fit this machine need more memory than the Ollama lane allows.

| Tool | Stage | How colibri compares |
| --- | --- | --- |
| Ollama | I2 | Already serves this exact GGUF. Same prompts, same script: Ollama 45.28 tok/s, colibri 22.49 tok/s. |
| llama.cpp (server mode) | I1 | Already in the pfy up order. The 2026-10-06 rank puts `llama-server --no-mmap` first for models Ollama cannot hold. Not re-measured here. |
| Strata | I2 | Same host, same model family. That trial was 51.86 vs Ollama 61.71 tok/s (0.84x) on longer prompts, and stayed I2. This probe is 0.497x on short prompts. |
| LiteLLM | I2 | Proxy in front of an engine. colibri speaks `/v1/chat/completions`. No glue until the engine is faster or serves a model we cannot already serve. |
| llama.cpp ngram-mod | I1 | A speed patch on llama.cpp, not a second server. |
| MLX + MLX-LM | I1 | Apple Silicon. This lab is Linux. |
| Laguna S 2.1 | I1 | Weights, not an engine. No GGUF smoke on this machine. |
| Kolibri-1 | I0 | A different MoE. Needs a patched llama.cpp. Not this binary. |
| DeepSeek-V4.1-Flash-1017 GGUF | I0 | Does not fit nimo. colibri's own v2.1.0 notes list that GGUF at 233 GB. Not pulled. |
| HiRoute | I2 | Routes cheap turns to the local engine. It does not replace the engine. |
| llm-router | I0 | Same. The hook chain still named Ollama first. |
| harness2 | I1 | Used its own llama-server. Not an engine. |

colibri does not beat Ollama on the model both can run. It does not serve a model Ollama cannot hold. The entry's GLM-5.2 pack is 381230481274 bytes (Hugging Face `usedStorage` for `jlnsrk/GLM-5.2-colibri-int4`, sha `cce7e760eab7eeba0a93b7074b64651ff3830928`). That is over the 25 GB pull cap and over the 250 GB pool. Download SKIPPED.

## Pins

Entry 003 in `sources/x-posts.md` names the GitHub repo and the Hugging Face weights. It records no commit and no checksum. The pin used here is the latest release as of this run, v2.1.0.

| Item | Value |
| --- | --- |
| Tag object | `8579957378ca922ad4340a6392513485cbc50c2c` |
| Tag commit | `704a3f68184b78367a04cb5526e428dc2f90f05b` (2026-10-31) |
| `coli --version` | colibri 2.1.0 |
| Linux archive | `colibri-v2.1.0-linux-x86_64.tar.gz`, 14233828 bytes |
| sha256 | `d54b4c57c12417fc9e784b649249ac1aa3480eec44ece2777d4cbc639a25e66a` (matches `SHA256SUMS.txt` and the GitHub release digest) |
| qwen36 build id | `6b007fb7ac6ef16ab14abf094cc1d2253f0df875` |
| License | Apache-2.0 (`LICENSE` in the archive) |
| App tree | 39041865 bytes on disk after the run (archive members plus Python bytecode), not in git |
| Linked GGUF | Ollama blob `sha256-d372de8e934898a59e6ccfabc3368474711384d8f1fd4d22d87a3f0a45400cdc`, 21718480960 bytes, magic `GGUF`, arch `qwen35moe`, 40 layers. Import mode `link`. No copy. No write under `/usr/share/ollama`. |

`--gpu 0` exited immediately: `--gpu needs the CUDA build: the engine binary is CPU-only`. That flag is the CUDA switch. Vulkan is `COLI_VULKAN=1`. The RADV ICD is `/usr/share/vulkan/icd.d/radeon_icd.json`.

## Commands

Home, XDG, and TMPDIR for the tool were under `~/.cache/pfy/tools/colibri/`. The model lock was held only around each live serve. `ollama ps` was empty before each live step. MemAvailable_kB was 71054336 before the Vulkan serve and 71380960 before the Ollama step (about 68 GiB). The file is 20.23 GiB, so the headroom rule (file plus 25 GiB) passed. No `ollama stop`. Ollama was not loaded, so the Ollama step sent `keep_alive` `2m`.

```bash
CACHE=~/.cache/pfy/tools/colibri
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,tmp,dist,models,app}
curl -fsSL -o "$CACHE/dist/SHA256SUMS.txt" \
  https://github.com/JustVugg/colibri/releases/download/v2.1.0/SHA256SUMS.txt
curl -fL -o "$CACHE/dist/colibri-v2.1.0-linux-x86_64.tar.gz" \
  https://github.com/JustVugg/colibri/releases/download/v2.1.0/colibri-v2.1.0-linux-x86_64.tar.gz
sha256sum "$CACHE/dist/colibri-v2.1.0-linux-x86_64.tar.gz"
tar -xzf "$CACHE/dist/colibri-v2.1.0-linux-x86_64.tar.gz" -C "$CACHE/app"
# then, with HOME/XDG/TMPDIR under $CACHE:
"$CACHE/app/coli" import --mode link --out "$CACHE/models/qwen36.colibri" \
  "$CACHE/models/qwen3.6-35b.gguf"
scripts/model_lock.sh bash eval/evq1107/colibri/run_colibri.sh vulkan
scripts/model_lock.sh python3 eval/evq1107/colibri/probe.py \
  --api ollama --url http://127.0.0.1:11434/api/chat \
  --model qwen3.6:35b --keep-alive 2m \
  --out eval/evq1107/colibri/ollama.json --runs 2
```

The serve was `coli serve` on `127.0.0.1:18112`, model id `qwen36-colibri`, `--auto-tier --ram 48 --ctx 2048 --no-think --temp 0 --no-tune-profile --policy quality`, with `COLI_VULKAN=1` and `COLI_VK_SHADERS` pointed at the archive's `shaders/`. Port 8000 was already taken and was not used. `coli stop` in the runner passes `--port 18112` so it does not target 8000.

Two prompts from this repo, two scored runs each, plus one warmup that is not in the median. Temperature 0. A run is exact when the first line is `I2` or `PFY_MODEL_LOCK_HELD`. Decode tok/s is `(completion_tokens - 1) / seconds from the first content byte to the last content byte`. Prompt tok/s is `prompt_tokens / TTFT`.

## Numbers

| Engine | Exact | Decode tok/s | Prompt tok/s | TTFT s | Wall s |
| --- | --- | --- | --- | --- | --- |
| colibri Vulkan, qwen3.6 GGUF | 4/4 | 22.49 | 148.44 | 0.516 | 0.677 |
| Ollama `qwen3.6:35b` (same file) | 4/4 | 45.28 | 306.95 | 0.235 | 0.391 |

Decode ratio 22.49353747625693 / 45.27771732662394 = 0.496790 (0.497 in the headline). Prompt ratio 148.43857327070612 / 306.9506509695857 = 0.483591 (0.484 rounded). The promote bar used on this host for a second engine is 0.90.

Scored colibri decode runs: stage 23.90 and 26.43 (2 completion tokens), lock 12.77 and 21.08 (6 tokens). Ollama: stage 44.49 and 46.07 (3 tokens), lock 63.30 and 5.97 (7 tokens). The median is the middle pair, so the one slow Ollama lock run does not set it. Ollama's own `eval_count / eval_duration` median is 67.92 tok/s. colibri does not print that counter. The paired number is the stream formula.

Warmup is outside the table. colibri warmup TTFT was 5.26 s (load). Ollama warmup TTFT was 24.05 s (load). `ollama ps` was empty before that load.

The Vulkan log shows RADV STRIX_HALO, the chain placing 40 of 40 layers on the device, and an expert tier of 10.66 GiB. The planner's CUDA VRAM line still says the binary has no GPU backend. That line is the CUDA check. `--gpu` is CUDA, and this archive has no CUDA build. The measured path is the Vulkan chain, not a CPU-only run.

GLM-5.2 serve: SKIPPED. 381230481274 bytes. Qwen3.8-Flash-Next in the upstream table is a 186 GB download. Not pulled. `qwen3-coder-next` is already in Ollama at 51 GB. File plus 25 GiB was above MemAvailable (about 68 GiB free), so it was not loaded.

## Verdict

`STAY I1 decode 22.49 tok/s is 0.497x Ollama 45.28 tok/s on the same qwen3.6 prompts`

Value (3 of 4 for I3):

1. Gap fill: no. The model both engines can run is slower on colibri. The model that would be new (GLM-5.2) does not fit the pull cap or the pool.
2. Operator leverage: no. The OpenAI shim answered, and it is not faster than the server pfy already uses.
3. Evidence: yes. The commands above ran on this host.
4. Blast radius: yes for this probe. Apache-2.0, 14 MB archive, link to an existing GGUF, no runtime takeover, no weights in git. The 381 GB pack was not downloaded.

Score 2 of 4.

Modularity (all 4): the speed on this GPU is not in the docs (we had to run it), the unit we ran is the release archive rather than the full tree, it sits in the cache, and deleting the cache leaves the pin and this report. The install is about 39 MB, under the 50 MB I2 copy limit. The promote rule still wants a measured gain. There is none. `tier_ceiling` stays I1. No `self_pipeline` field. No gate wiring. No TOOLS.md edit. The row was already there.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Short answers | Two tokens make one interval. One Ollama run was 5.97 tok/s. | Median of four scored runs. Warmup excluded. |
| Context mismatch | colibri ran at 2048 tokens. Ollama loaded context 262144. | colibri had the smaller cache and still lost. A matched short context would not turn 0.497x into 0.90x. |
| CUDA flag | `--gpu` exits before listen on this archive. | `COLI_VULKAN=1`. That is the path measured. |
| `coli stop` default port | The helper defaults to port 8000, which was already in use. | The runner passes `--port 18112` and kills only its own pid. |
| Linked blob | Ollama replaces the blob and the link dangles. | Re-import. Do not copy the GGUF into git. |
| GLM download | 381 GB fills the pool and breaks the pull cap. | Do not download. This lane did not. |
| Stage apply | `catalog_stage_eval.py --apply` rewrites `uses` and `next_gate` from the shared handoff. | `notes_doc` points at this report. `potential` low stays, because apply does not replace a potential that is already set. This lane did not edit the handoff. |

## Next gate

Stay I1. Re-open only for a same-prompt trial that reaches at least 0.9x Ollama decode on this host, or for a model Ollama cannot hold whose pack is under 25 GB and under the 250 GB pool. Do not download GLM-5.2 for that gate. Do not make colibri the default engine. Do not wire it into pregate, CI, or LiteLLM in this lane.

## Pipeline questions

How colibri would run if a later ticket adopted it. This lane did not add that path.

1. What triggers it? An operator starts `coli serve` against a GGUF already on disk, after a trial that clears the 0.90 bar. Not the evq scheduler, and not `./pfy start`.
2. What does it do, and which services does it read and write? It reads a local GGUF and writes a small model directory (link mode). It serves `127.0.0.1` OpenAI. It does not use an account. It does not write the catalog.
3. What does it trigger next? A client that already speaks an OpenAI base URL could point at that port. Ollama stays the default until a trial says otherwise.
4. Where does a human re-enter? Any download over 25 GB, any change of the default engine, and any gate wiring.
5. What stops two runs doing the same work? One worktree per slug, the model lock around each live serve, and one port per server. Do not start colibri while Ollama holds the same weights.
