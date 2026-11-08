# open-webui evq1107

STAY I1 reference: chat client of an existing engine, and clause 4 locks the Open WebUI brand

## What it is

Open WebUI (open-webui/open-webui) is a self-hosted chat app. The README says it runs offline and connects to local models through Ollama or to OpenAI-compatible APIs. `package.json` is 0.13.0. The UI is SvelteKit. `pyproject.toml` points `license` at `LICENSE` and depends on FastAPI and uvicorn. README install paths are `pip install open-webui` on Python 3.12, then `open-webui serve` on port 8080, or Docker publishing host port 3000 to container port 8080. Image tags are `:main`, `:slim`, `:cuda`, `:ollama` (Ollama bundled), and `:dev`. The README also links a separate desktop app. In-repo `docs/` is only `SECURITY.md`, which points at the public docs site. This lane did not open that site, install the package, pull an image, or run a script.

The current `LICENSE` is the Open WebUI License, copyright 2023- Open WebUI Inc. GitHub `license.spdx_id` is NOASSERTION. Clause 4 forbids removing the Open WebUI brand except when end users stay at or under 50 in any 30 days, or with written permission, or with an enterprise license. `LICENSE_HISTORY` at this pin keeps a 3-condition grant (retain the notice, reproduce it in binaries, no endorsement) for material before `60d84a3aae9802339705826e9095e272e3c83623`, and the MIT text for material before `a76068d69cd59568b920dfab85dc573dbbb8f131`. Cite only. Copy no source.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `c38885a1a737da4968f157092f304f3b5481d0bf` on `main` |
| Tag | `v0.13.0` is that SHA. Commit 2026-11-03 21:21:21 +0900, `0.13.0 (#33387)`. Changelog heading date is 2026-11-02. |
| Fetch | `git clone --depth 1 --filter=blob:none --sparse` in 1.16 s. Sparse checkout of README, LICENSE, LICENSE_HISTORY, CHANGELOG, package.json, pyproject.toml, and docs. No upstream script. |
| Tree | 5274 blobs. GitHub tree API sum 56112756 bytes (`truncated` false). GitHub repo `size` 545353 KB. Sparse worktree 1636676 bytes. `.git` 3939116 bytes. |
| Cache | `~/.cache/pfy/tools/open-webui/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` sat under `~/.cache/pfy/tools/open-webui`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. No `sources/entries` file (the ticket entry was `-`). Status is the card.

## Ideas, and the pfy file each would touch

1. One client, two backends (an Ollama base URL, or an OpenAI-compatible API). Already `docs/adr/0014-pluggable-local-inference-spine.md`. Workers use one `LOCAL_OPENAI_BASE_URL`. Leave this app uninstalled.
2. Chat beside files, a terminal, a browser, and a desktop (0.13.0 changelog tabs, through a separate Open Terminal). The operator window is Loop, Engine, Stage, and Attach in `gui/operator/README.md`. Levers stay onboard, stage, and ship in `docs/ops/product-operator-surface.md`.
3. A tool call waits until a person allows it (changelog: sidebar "Waiting for approval"; MCP apps confirm each call). Already `docs/adr/0007-write-guard-mcp-layer.md` and `harness/write-guard-mcp`. Do not import the 1024-round limit.
4. A side chat that stays out of the main thread (`/side` in the 0.13.0 changelog). The product UI stays `gui/operator/README.md`. Do not add a second chat.
5. `HF_HUB_OFFLINE=1` on the Docker line so the UI does not pull weights. `config/profiles/local-only.env` already keeps the lab local.

## Catalog comparison

Same job: a person chats with a local model. Gap L in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is a second inference engine. This README connects to an engine. The `:ollama` tag would bundle Ollama, which pfy already runs, and `:cuda` wants NVIDIA. nimo has no NVIDIA. This lane builds no pipeline step. Searched `data/stages/*.json` uses, features, and tags. kanbots is I1 and tagged `#ui`, and it is a kanban for coding CLIs, so that tag is a different job. TOOLS.md already has the row. This lane did not edit it.

| Tool | Stage | How Open WebUI compares |
| --- | --- | --- |
| Ollama | I2 | The engine the README points at. `./pfy start ollama` checks health. |
| llama.cpp (server mode) | I1 | GGUF server already in the pfy up order. This app would call it. |
| LiteLLM | I2 | The OpenAI-compatible proxy for Grok and local models. This app would call a URL. |
| Strata | I2 | Second engine trial on gfx1151. That is the gap L work. |
| Grok CLI bootstrap | I3 | Operator env (ADR-0002). The product surface is this path. |
| Continue.dev | I1 | IDE client of a local OpenAI base. pfy writes a config and does not exec the IDE. |
| Aider | I1 | Terminal git editor on the local build path. |
| hal0 | I0 | Inference appliance. Card non-goal `openwebui_companion`. Its report leaves Open WebUI on port 3001 with auth off unused. |
| SmythOS Studio | I1 | Visual builder with an Ollama block. A different product runtime. |

`SUBTREES.md` already excludes Open WebUI as a full UI.

## Gates

Value, 3 of 4 for I3: gap fill no (L is an engine, W is our window), operator leverage no (Docker or pip, and clause 4 blocks rebranding it as pfy), evidence no (docs only; the README quickstart was not run), blast radius no (it would take over the product UI, clause 4 blocks a rebrand, `:ollama` bundles an engine, and the 0.13.0 changelog says unlisted security fixes plus a schema change with no rolling update). Score 0 of 4.

Modularity, all 4: the README, LICENSE, and changelog were enough to decide. The unit is a SvelteKit app, a Python backend, Docker, and separate desktop and terminal repos. The cache clone is isolatable, and deleting it leaves the pin. 2 of 4. Potential is low. I2 stays closed. No `self_pipeline`. Tags stay `#ui #chat #local-first #docker #multi-model`. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Brand lock | The UI ships as pfy and clause 4 is breached. | Do not install. Do not copy source. |
| Bundled engine | The `:ollama` image becomes a second Ollama. | Engines stay Ollama, llama-server, and Strata. |
| Port 8080 | `open-webui serve` listens on 8080. Docker publishes container 8080 as host 3000. | Do not start it. |
| Auth off | A companion copy follows the hal0 pattern, auth off on a LAN port. | Leave that port unused. |
| Size | The tree lands in git. | Cache only. `SUBTREES.md` already forbids the embed. |

## Next gate

Stay I1 reference. No install. No Feature GO. Gap L stays open. Gap W stays the operator window.

## Pipeline questions

This lane writes the card and this directory. It does not put Open WebUI on a pipeline.

1. Trigger, if a later ticket adopted it: a person runs Docker or `open-webui serve`. The evq scheduler is not that trigger.
2. It would read an Ollama base URL or an OpenAI-compatible API and write chat data in its own volume. This lane called no model and used no account.
3. Next would be the browser on the published port. Nothing here starts that.
4. A human re-enters before any install, any image pull, any bind, and any I3 claim.
5. One worktree per slug keeps this card private. A second `open-webui serve` would also want port 8080. Docker would want host port 3000. This lane started none.
