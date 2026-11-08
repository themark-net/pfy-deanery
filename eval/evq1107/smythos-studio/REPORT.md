# SmythOS Studio evq1107

STAY I1 reference: the visual builder is a second product runtime, and gap B is still the pfy build timeout.

## What it is

SmythOS Studio (README title SmythOS UI) is a drag-and-drop agent workspace. The monorepo has three packages: `smyth-builder` 1.54.185 (canvas), `middleware` 1.4.281 (Prisma and MySQL), and `runtime-server` 2.0.0 (runner, debugger, embodiments). The runtime package depends on `@smythos/sre` `^1.7.16`. The README sends code-first users to https://github.com/SmythOS/sre. This lane did not clone that repo. The canvas includes API call, logic gates, key-value memory, an MCP client, a GenAI LLM node, and Zapier. Embodiment modals cover API, chatbot, MCP, voice, Alexa, a form, GPT, and Lovable. LLM param keys include openai, anthropic, groq, xai, and ollama. The README and Docker guide never name Ollama. The param file does, with default temperature 0.8 and default max tokens 128.

Root `LICENSE` is MIT, copyright 2025, INK Content, Inc. Root `package.json` says ISC. `runtime` and `middleware` also say ISC. The app license field is empty. The grant is the LICENSE file. Copy no source.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `3e1ea87e6718fdfdb24365b2184fbd1daa9f94f8` on `main` |
| Commit | 2026-03-31 10:27:15 -0700. Merge pull request #499 from SmythOS/dev. |
| Other tip | `origin/dev` `0a3e68548398b47944c800edd7fb5186d6e8a724`, 2026-04-01 02:40:59 -0700, pull request #477. Not the pin. |
| Fetch | 3.00 s. `git clone --depth 1 --filter=blob:none`. No upstream script. |
| Tree | 1699 files. Worktree 42305389 bytes. `.git` 11843678 bytes. Combined 54149067 bytes, over 50 MB. |
| Cache | `~/.cache/pfy/tools/smythos-studio/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` sat under `~/.cache/pfy/tools/smythos-studio`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. pnpm is pinned `10.12.2` in the repo. This lane did not run pnpm, Docker, or any script.

Compose runs image `smythos/smythos-studio:alpha`, not this commit. `.env.compose.example` sets `EXPOSE_TRAEFIK_PORT` to 6060 and `EXPOSE_HTTPS_TRAEFIK_PORT` to 6062, so the README URL is Traefik. The app listens on 5050 and the runtime on 5053 inside the network. The guide still says ports 80, 443, 5050, 5053, and 8080 must be free. Unset expose vars fall back to 80, 443, and dashboard 8089. The example `RUNTIME_DOMAIN` is a smyth.ai host, not localhost. A git-sync sidecar (`registry.k8s.io/git-sync/git-sync:v4.2.4`, user `0:0`) defaults to cloning `SmythOS/sre-models-pub` onto a path under the real home. Traefik is started with `--api.insecure=true` and a docker.sock mount.

## Ideas, and the pfy file each would touch

1. A flowchart of components as the authoring unit. pfy loops stay text in `docs/ops/loop-engineering.md`. The product surface stays onboard, stage, and ship in `docs/ops/product-operator-surface.md`.
2. One agent, many deploy targets. Ship in that same operator doc is verify and push of product code. Leave agent hosting out.
3. An Ollama block beside hosted providers. Already `docs/adr/0014-pluggable-local-inference-spine.md` (FreeToken, then llama-server, then Ollama). Do not add a second connector list.
4. A builder process and a runner process on different ports. Already the monitor and worker split in `docs/ops/local-cloud-split.md`, with Grok CLI as the interface in `docs/adr/0002-grok-cli-primary-interface.md`.

## Catalog comparison

Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is the unproven `./pfy build` path. That section says no entry from 137 to 167 closes it. Entry 081 is older and does not close it either. This lane builds no pipeline step. Searched `data/stages/*.json` uses, features, and tags for a visual agent builder. `docs/ops/smythos-studio-entry-081.md` is an old row sketch. This lane adds no TOOLS.md row.

| Tool | Stage | How SmythOS Studio compares |
| --- | --- | --- |
| LangGraph | I1 | Code graphs. Our loops already cover the operator path. No canvas. |
| Atomic Task Graph | I2 | Typed DAG compile and repair. Not a drag-and-drop studio. |
| Moira | I1 | A condition node on fields the agent already sent. Not a workspace. |
| multi-agent-generator | I0 | Emits CrewAI, LangGraph, ReAct, or Agno source from one sentence. Not this UI. |
| Open WebUI | I1 | Chat UI. The operator window is the product UI. |
| kanbots | I1 | Kanban for coding CLIs. The probe left the build timeout in place. |
| Emdash | I0 | Desktop that runs coding-agent CLIs, one worktree per task. |
| Pi-Harness | I0 | Desktop control plane for runs and replay. Not a builder. |
| Muxin | I0 | Fleet desktop. Off the pfy build path. |
| Continue.dev | I1 | IDE config that points at a local OpenAI base. pfy does not exec the IDE. |

## Gates

Value, 3 of 4 for I3: gap fill no, operator leverage no (root Docker, MySQL, Redis, Traefik, Logto, an unpinned alpha image), evidence no (this lane did not start compose, and compose runs the alpha image rather than this pin), blast radius no (docker.sock, git-sync as root onto a home path, insecure Traefik API). The MIT file is fine to read. Score 0 of 4.

Modularity, all 4: the README, compose file, and param file were enough to decide. The unit is a three-package monorepo plus an SRE dependency. The cache clone is isolatable, and deleting it leaves the pin. 2 of 4. The worktree is under 50 MB. The clone with `.git` is over 50 MB. Potential is low, so I2 stays closed. No `self_pipeline`. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Compose writes the host | git-sync runs as root and bind-mounts a models dir under the real home | Do not run compose. This lane ran nothing. |
| Unpinned image | `smythos/smythos-studio:alpha` is not commit `3e1ea87e` | Keep the card pin. Do not treat the image as this tree. |
| License field drift | package.json says ISC while LICENSE is MIT | Cite the LICENSE file. Copy no source. |
| Port story | README says 6060. The guide also demands 80 and 443. The example HTTPS expose is 6062, and RUNTIME_DOMAIN is not localhost. | Leave the ports unused. |
| Second product UI | A canvas replaces onboard, stage, and ship | Stay on `docs/ops/product-operator-surface.md`. |

## Next gate

Stay I1 reference. Re-open only if a later ticket asks for a visual authoring note, and that ticket still leaves this stack out. No install. No Feature GO. Gap B stays the pfy build timeout.

## Pipeline questions

This lane writes the card, the entry Status line, and this directory.

1. Trigger, if a later ticket adopted it: a person runs Docker Compose. The evq scheduler is not that trigger.
2. It would read `.env` and write MySQL, Redis, Traefik certs, and a models directory on the host. This lane called no model and used no account.
3. Next would be the canvas on the Traefik port and the runtime health URL on port 5053. Nothing here starts that.
4. A human re-enters before any Docker start, any home bind mount, and any image pull.
5. One worktree per slug keeps this card private. Two studios on port 6060 would collide. This lane started none.
