# hal0 evq1107

STAY I0 reference: system install needs root, and Ollama plus llama-server already cover the OpenAI path. This lane did not install, download a release, or run upstream code.

## What it is

hal0 (https://github.com/Hal0ai/hal0, Apache-2.0) is a Linux inference appliance. `hal0-api` is the control plane. Chat, embeddings, rerank, speech-to-text, TTS, and image generation each run as a podman container under a `hal0-slot@<name>` unit, and one `:8080/v1` surface dispatches to them. The README targets a Ryzen AI Max+ 395 / Radeon 8060S / 128 GB box, the same class as nimo. It wraps llama.cpp (ROCm, Vulkan, experimental CUDA), plus Kokoro, Qwen3-TTS, ComfyUI, and FastFlowLM on the XDNA NPU. It is not a new engine. PyPI name `hal0ai` 1.4.0. `requires-python` is `>=3.12`. The README install list names 3.12 to 3.14, systemd, and podman (docker accepted if already present).

## Pin and commands

Cache `~/.cache/pfy/tools/hal0/src`, not committed. Tag `v1.4.0` is `60bcf6f77dc81c5e13692e4fde712db5eb3285ea` (2026-10-16 02:07:52 -0400). hal0 `origin/main` at this read was `0867e1243cca26fd0813f43360705326d646e56f` (2026-11-07), 426 commits ahead of this pin. Abbreviated `60bcf6f77dc8` is not a remote ref. Doc-only sparse checkout: 107 files, 5874979 bytes. `.git` 11523149 bytes. `src/`, `ui/`, and `installer/` were not materialized. Checkout of those doc paths returned in under 1s. The initial clone wall time was not recorded. No script ran. No model lock.

```bash
CACHE=~/.cache/pfy/tools/hal0
mkdir -p "$CACHE"/{home,xdg/config,xdg/cache,tmp}
export HOME="$CACHE/home" XDG_CONFIG_HOME="$CACHE/xdg/config" XDG_CACHE_HOME="$CACHE/xdg/cache" TMPDIR="$CACHE/tmp" GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_TERMINAL_PROMPT=0
git clone --filter=blob:none --no-checkout https://github.com/Hal0ai/hal0.git "$CACHE/src"
git -C "$CACHE/src" sparse-checkout init --cone
git -C "$CACHE/src" sparse-checkout set README.md LICENSE ARCHITECTURE.md CHANGELOG.md pyproject.toml docs
git -C "$CACHE/src" checkout --detach 60bcf6f77dc81c5e13692e4fde712db5eb3285ea
```

## Ideas, and the pfy file each would touch

1. One `/v1` in front of named capability slots, each pinned to a device. Touch `docs/adr/0014-pluggable-local-inference-spine.md`. That ADR already picks one OpenAI base URL: FreeToken, then llama-swap or llama-server, then Ollama.
2. Their leaderboard cites `qwen3.6-35b-a3b-crown` at 84.4 tok/s decode and 873 tok/s prefill (f16, ROCm 7.2.4, their box) and NPU `gemma3:1b` at about 38.6 tok/s in about 2 GB. Our ROCm 7.1 llama.cpp row is 57.2 tok/s decode in `docs/dogfood/LOCAL-BENCH-5-RUNTIMES.md`. Re-measure with `examples/local-bench/bench.py` before a host decision. Their claim, not reproduced here.
3. The README presents bare `hal0 doctor` as a pre-flight. `perms --fix` and `ports --fix` write. `./pfy status` already reports ready, partial, stub, or missing (`docs/design/pfy-launcher.md`). Their Strix Halo doc says a Vulkan lane can emit invalid tokens while `hal0 doctor` stays green. This lane ran no doctor command.
4. Live model steps already take `scripts/model_lock.sh`. Leave the installer, systemd units, FastFlowLM `.deb`, Hermes bundle, and OpenWebUI on `:3001` unused.

## Catalog comparison

Gap L in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is a second local engine beside Ollama for models that need llama-server. The picked trial is Strata. Searched `data/stages/*.json` uses, features, and tags for an OpenAI-compatible local server.

| Tool | Stage | How hal0 compares |
| --- | --- | --- |
| Ollama | I2 | Host OpenAI server and the ADR-0014 adapter. |
| llama.cpp (server mode) | I1 | GGUF server already in the pfy up order. hal0 runs llama.cpp inside slots. |
| LiteLLM | I2 | One proxy for Grok and local models. hal0 would add another control plane on `:8080`. |
| Strata | I2 | gfx1151 engine trial, 0.84x Ollama decode. hal0 wraps llama.cpp. It is not that engine. |
| colibri | I1 | MoE server, 0.497x Ollama on the same prompts. |
| llama.cpp ngram-mod | I2 | A llama-server flag. Not an appliance. |
| Open WebUI | I1 | Chat UI. hal0 ships it on `:3001` with auth off. The operator window stays the product UI. |
| HarnessRouter | I0 | One self-hosted API. The 2026-11-07 probe added 0 local engines. |
| MLX + MLX-LM | I1 | Apple Silicon. This lab is Linux. |
| Antigravity-Manager | I1 | Tag `#openai-shim`, and the job is an account-pool proxy. LiteLLM stays the proxy. |

## Gates

Value, 3 of 4 for I3: gap fill no, operator leverage no (`curl` piped to `sudo bash`), evidence no (entry 130 records no smoke; this lane did not run it), blast radius no (systemd, `/etc/hal0`, `/usr/lib/hal0`, `/var/lib/hal0`, podman, LAN bind). Apache-2.0 is fine to read. The install is still a primary-runtime takeover. Score 0 of 4.

Modularity, all 4 for a local copy: the README was enough to stay, the unit is an appliance monorepo, the doc cache is isolatable, and deleting it leaves the pin. A real install is not reversed by deleting that cache. 2 of 4. Doc checkout is 5874979 bytes. Potential is low, so I2 does not apply. No `self_pipeline`. No TOOLS.md row. No `data/tools.json` row. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| System install | Units, podman, a FastFlowLM `.deb`, and a brain-model pull (README: `lfm2.5-2.6b`, about 2.87 GB) land on nimo | Do not run the installer. This lane ran nothing. |
| LAN-open API | The installer seeds `HAL0_BIND_HOST=0.0.0.0`. Auth stays off until `hal0 auth require on`. OpenWebUI `:3001` uses `WEBUI_AUTH=False` and sits outside that switch. | Do not install. A later ticket would bind loopback first. |
| Port and memory | `:8080` and GTT contend with llama-server and Ollama | Keep both. `scripts/model_lock.sh` stays the live-model lock. |
| Leaderboard optimism | 84.4 tok/s is their ROCm 7.2.4 table, not a nimo receipt | Re-measure with `examples/local-bench/bench.py`. |
| Pin drift | hal0 `main` is 426 commits past v1.4.0 | The card pins `60bcf6f77dc81c5e13692e4fde712db5eb3285ea`. |

## Next gate

Stay I0 reference. Re-open only if Mark approves a separate ticket. Not a Feature GO. A ROCm userspace question is a host decision and is not a hal0 install. The install doc also describes `--dev` (a tree under `$PWD/.hal0ai`, no systemd). That path is still an install, and this lane does not run it.

## Pipeline questions

This lane writes the card, the entry Status line, and this directory. It does not add a pipeline step.

1. Trigger, if a later ticket adopted it: a person runs the installer. The evq scheduler is not that trigger.
2. It would read host devices and write `/etc/hal0`, systemd units, and model files under `/var/lib/hal0`. This lane called no model and used no account.
3. Next would be `hal0 doctor` and `GET /v1/models`. Nothing here starts that.
4. A human re-enters before any install, any sudo, any port bind, and any model pull.
5. One worktree per slug already stops two lanes editing this card. Two appliances on `:8080` would collide. This lane started none.
