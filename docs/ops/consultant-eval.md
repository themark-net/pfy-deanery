# Consultant evaluation pack

Read this first if you are evaluating **code against documentation**. Docs below match shipped `scripts/pfy`, `data/harnesses.json`, and `scripts/detect-local-runtime.sh` on main. Do not treat catalog rows or queued adapter issues as live product.

## Map (every link is in-repo)

| What | Path |
|------|------|
| Design (why / G1–G8) | [docs/DESIGN.md](../DESIGN.md) |
| Architecture snapshot | [docs/ARCHITECTURE.md](../ARCHITECTURE.md) |
| ADR index (incl. 0014, 0015) | [docs/adr/README.md](../adr/README.md) |
| Simple launch | [docs/ops/simple-launch.md](simple-launch.md) |
| Local inference | [docs/ops/local-runtime.md](local-runtime.md) |
| Product levers | [docs/ops/product-operator-surface.md](product-operator-surface.md) |
| Eval gates | [docs/ops/eval-gates-and-ux-uat.md](eval-gates-and-ux-uat.md) |
| Harness registry | [data/harnesses.json](../../data/harnesses.json) |
| Module maps | [docs/modules/README.md](../modules/README.md) |
| Work queue | [docs/TODO.md](../TODO.md) |

## Operator loop (no tribal knowledge)

```bash
git clone https://github.com/themark-net/pfy-mentat.git
cd pfy-mentat
./pfy setup                 # or: ./pfy setup local-only
./pfy status                # live column is authority, not json "status"
./pfy                       # inference → env-stage → native operator window
./pfy board                 # same native window; chips must equal the live column
./pfy start grok            # named harness exec after inference/stage
./pfy up                    # same as bare ./pfy
./pfy models                # inspect-only (tag list is not success)
make eval-structural        # G0, no LLM, no cage required
```

Bare `./pfy` / `./pfy start` / `./pfy up` (no harness name) = local inference (if any) + `scripts/env-stage.sh` (honest skip) + **native operator window**. They do **not** exec the active harness into that process. Named `./pfy start <id>` still execs that harness. `./pfy models` never means the stack is ready. `./pfy eval` is catalog self-mod (`make eval-integration-change`), not the consultant G0 lane.

Public CLI must agree: README Simple path, this file, [simple-launch.md](simple-launch.md), and `scripts/pfy` `usage()`.

## Operator board (`./pfy` / `./pfy board`)

Native operator window **is** the main interface. Tauri 2 when `gui/operator/src-tauri/target/{release,debug}/pfy-operator` exists; else already-on-box webkit (`scripts/pfy-gui.py`) with the same frontend (`gui/operator/frontend/`); else stdlib tk with live chips from `./pfy status`. pywebview is PFY_GUI_DEV=1 only. Independent poller of detector JSON (`bash scripts/detect-local-runtime.sh --json`), `./pfy status` stdout, and the process table. **No pfy daemon** beyond the native window. Optional `./pfy board --open` is a browser hatch (honest skip if it fails), not the main path. In-window attach for grok/opencode = sidecar subprocess, not exec into the GUI. Board is not a supervisor for arbitrary harnesses. No SaaS, no git console, no credential capture. Do not invent `pfy status --json` unless a real flag exists. Window always opens; not install-tips-as-UI.

**Consultant check:** every honesty-rail chip must equal the **live** column from `./pfy status` on the same host (Ollama-only host and a host with no harness binary). Unparsed live is **missing**, not unknown. Ignore json `status`. Split **LOCAL WORKER** vs **CLOUD MONITOR**. Live tape **READY | SKIP | FAIL**. Agent lane one line `no org loop` unless org messages exist. Grok chip is PATH-only (no invented auth column; no Grok usage). Continue is never detected-stub. Docker on PATH is cage detected-stub, not startable. nimo banner **only** if hostname contains `nimo`. Empty `ollama ps` is OK. `DEPLOY_PROFILE=local-only` never auto-calls cloud. Models drawer is inspect-only (tag list is not success). Three honest states: all-local-ready; Ollama-only; missing harness.

Active continue or agent-cage: FAIL with **no** grok/opencode fallback. Blocked copy: `pfy harness use grok`. Lab is `./pfy stage --lab`.

## Real vs stub vs catalog-only

| Kind | Meaning |
|------|---------|
| **Live harness** | `./pfy start <id>` execs a binary (grok, opencode, hermes, claude-code, codex, gemini, exo.sh) |
| **Inference adapter** | Detector / `ensure_inference`; `./pfy start <engine>` is not a coding agent |
| **Honest stub** | `STUB harness: <id>` + issue URL, **exit 2**. Binary on PATH is `detected-stub`, still not ready |
| **Catalog-only** | Scored in `TOOLS.md` / slim `data/tools.json` ([ADR-0015](../adr/0015-catalog-json-slim-subset.md)). A catalog row is not an installer |

Live path today: **Grok** (monitor, default) + **OpenCode** (host adapter) + **Hermes** (runtime, if binary on PATH) + **Claude Code** (if `claude` on PATH) + **Codex** (if `codex` on PATH) + **Gemini** (if binary on PATH) + **Exo** (optional lab if `exo.sh` present; not default) + **detected inference**. Remaining harness ids are stubs. Do not implement those adapters from this pack. `default_harness` stays grok. Docker on PATH is not ready.

## Honesty matrix (every `data/harnesses.json` id)

Live status comes from `detect_status` in `scripts/pfy` (and the detector for inference). The json `status` field can lag; trust `./pfy status`.

| Live | Meaning |
|------|---------|
| ready | Binary (or API) is usable for start |
| partial | Binary present, HTTP/API down (inference) |
| stub | Slot reserved; start is STUB exit 2 |
| detected-stub | Binary on PATH but adapter still stub |
| missing | No binary |

Detect order (ADR-0014, first live wins): **FreeToken :1919 → llama-swap :9292 → llama-server :8080 → Ollama :11434**. Shimmy is optional last. Override: `PFY_LOCAL_RUNTIME`, `LOCAL_OPENAI_BASE_URL`.

| id | Role | Live `./pfy status` | `./pfy start <id>` |
|----|------|---------------------|--------------------|
| freetoken | inference | Same (port **:1919**). **ready** only when `/v1/models` or `/health` responds; binary + API down = **partial**; no binary = **missing** | Detector-selected or `PFY_LOCAL_RUNTIME=freetoken`: start/up backgrounds `ft serve --model $model` (log under `$PFY_STATE_DIR`) if `:1919` is down, then wait for `/v1/models` or `/health` (12×0.5s). Model env: `PFY_FT_MODEL` then `LOCAL_CODER_MODEL` then `FREETOKEN_MODEL` then `$PFY_STATE_DIR/ft-model` (from `./pfy models pull <name>`). Missing binary or no model env: honest skip + `ft serve --model $PFY_FT_MODEL` one-liner, not fake ready. `./pfy models pull` does not invent `ft pull`: it records the name for the next `ft serve --model`. After start, re-detect; still down = partial. Named start exit 2 unless detector ready. Do not vendor or invent `ft` flags. |
| llama-swap | inference | Same (port **:9292**). **ready** only when `/v1/models` or `/health` responds; binary + API down = **partial**; no binary = **missing** | Detector-selected or `PFY_LOCAL_RUNTIME=llama-swap`: start/up backgrounds `llama-swap` (log under `$PFY_STATE_DIR`) if `:9292` is down, then wait for `/v1/models` or `/health`. Missing binary: honest skip + `llama-swap` one-liner, not fake ready. After start, re-detect; still down = partial. Named start exit 2 unless detector ready. Do not vendor. |
| llama.cpp | inference | Same as llama-server (port **:8080**). **ready** only when API responds; binary + API down = **partial**; no binary = **missing** | Detector-selected llama-server / llama.cpp (or `PFY_LOCAL_RUNTIME=llama-server`): if `llama-server` on PATH and `:8080` down, start in background with `-m` from `PFY_LLAMA_MODEL` then `LOCAL_CODER_MODEL` (existing GGUF file), `--port 8080 --host 127.0.0.1`. No path or missing binary: honest skip + one-liner. Wait for `/v1/models` or `/health`. Still down = partial. Named start exit 2 unless ready. Do not vendor or download weights. |
| ollama | inference | Same (port **:11434**). **ready** only when API responds (`GET /api/tags` or `/v1/models`); binary + API down = **partial**; no binary = **missing**. json may stay `partial` | Detector-selected or `PFY_LOCAL_RUNTIME=ollama`: start/up wait for real health (`GET /api/tags` or `/v1/models`). Default model `PFY_OLLAMA_MODEL` then `LOCAL_CODER_MODEL` then `OLLAMA_MODEL`; pull if that name is missing; honest skip if no name and none installed. `./pfy start ollama` runs that adapter even when another engine is already up, pins `LOCAL_OPENAI_BASE_URL` to `http://127.0.0.1:11434/v1`, and exits 2 unless `:11434` is healthy. `./pfy models pull <name>` still `ollama pull` when this engine is live |
| shimmy | inference | Optional last (port **:11435**). **ready** only when `/v1/models`, `/health`, or `/api/tags` responds; binary + API down = **partial**; no binary = **missing** | Detector-selected or `PFY_LOCAL_RUNTIME=shimmy`, and cold `./pfy up` only after FreeToken, llama-swap, llama-server, and Ollama are not healthy: backgrounds `shimmy serve --bind 127.0.0.1:11435` (add `--model-path` when `PFY_LLAMA_MODEL` or `SHIMMY_BASE_GGUF` is an existing file). Missing binary: STUB + that one-liner. Still down = partial, not fake ready. No pull. Do not prefer over FreeToken. |
| grok | harness | **ready** if `grok` on PATH; else **missing**. Attach also needs `grok login` / `XAI_API_KEY` | `exec grok` when authenticated. Missing/unauth: print install/login, **do not abort the env**; try next ready adapter (opencode) |
| opencode | harness | **ready** if `opencode` or `opencode-cli` on PATH; else **missing**. json may still say `partial` | Named start: `exec` binary, `OPENCODE_SKILLS` → `bootstrap/grok-cli/skills`, `OPENAI_BASE_URL` from `LOCAL_OPENAI_BASE_URL` when runtime ready. No binary: STUB + issue #55, exit 2 |
| hermes | harness | **ready** if `hermes` or `hermes-agent` on PATH; else **missing**. json may stay `partial` | Named start: `exec` binary; `OPENAI_BASE_URL` from `LOCAL_OPENAI_BASE_URL` when runtime ready. No binary: STUB + issue #56 + the registry installer (`setup` / `attach.next_install`), exit 2. Attach missing-binary `next_step` is that same line. Start does not run the installer. `/hermes-feedback` is process-only |
| claude-code | harness | **ready** if `claude` on PATH; else **missing**. json may stay `partial` | Named start: `exec claude`; `OPENAI_BASE_URL` from `LOCAL_OPENAI_BASE_URL` when runtime ready. No binary: FAIL + issue #57 + the registry installer (`setup` / `attach.next_install`), exit 2. Attach missing-binary `next_step` is that same line. Start does not run the installer. Login/credentials/2FA are owner-only |
| codex | harness | **ready** if `codex` on PATH or `~/.local/bin/codex`; else **missing**. json may stay `partial` | Named start: `exec codex`; `OPENAI_BASE_URL` from `LOCAL_OPENAI_BASE_URL` when runtime ready. No binary: FAIL + issue #58 + the registry installer (`setup` / `attach.next_install`), exit 2. Attach missing-binary `next_step` is that same line. Start does not run the installer. Login/credentials/2FA are owner-only |
| gemini | harness | **ready** if `gemini` or `gemini-cli` on PATH; else **missing**. json may stay `partial` | Named start: `exec` binary; `OPENAI_BASE_URL` from `LOCAL_OPENAI_BASE_URL` when runtime ready. No binary: STUB + issue #59 + the registry installer (`setup`), exit 2. Start does not run the installer. No Attach profile. Login/credentials/2FA are owner-only |
| exo | harness | **ready** if `$ROOT/exo.sh`, `$HOME/exo/exo.sh`, or `exo.sh` on PATH; else **missing**. json may stay `partial`. Docker on PATH is not ready. | Named start: `exec` that script; `OPENAI_BASE_URL` from `LOCAL_OPENAI_BASE_URL` when runtime ready. No invented Exo flags. Missing: STUB + issue #60 + official `setup.sh` one-liner, exit 2. Optional lab only — `./pfy harness use exo` does not change `default_harness` |
| continue | harness | **always stub** (empty detect; never detected-stub even if continue is on PATH). Recipe at bootstrap/continue/. | Always STUB exit 2 + issue #61. Do not exec the IDE. If this id is active, bare `./pfy` is FAIL with no grok/opencode fallback; copy `pfy harness use grok`. |
| agent-cage | lab | live **stub** / **detected-stub** (Docker on PATH is **not** ready / not startable) | Always STUB exit 2 + issue #62. If this id is active, bare `./pfy` is FAIL with no grok/opencode fallback; copy `pfy harness use grok`. Lab is `./pfy stage --lab` / `make cage-*` (doctor → setup → up-mcp). Missing Docker is honest skip, not product-ready. Do not sell cage. |

## Eval without assuming cage

| Command | Needs cage? | Needs LLM? | What green means |
|---------|-------------|------------|------------------|
| `make eval-structural` | No | No | G0 docs/schema scorers. Consultant default |
| `make eval-golden` | No | Replay fixtures | Deterministic golden lane |
| `make eval-deploy-ready` | Declared smokes | Mixed | G1 — skip if smoke needs lab you do not have; do not fake |
| `./pfy eval` | No (Make target may skip) | Catalog change gates | `eval-integration-change`, not G0 |
| `make cage-*` / in-cage smokes | **Yes** | Varies | Optional lab. Missing Docker is skip, not product-ready |

Do not call a lane green if it skipped. Point of truth: [eval-gates-and-ux-uat.md](eval-gates-and-ux-uat.md). Catalog scoring rubric: [evaluation-framework.md](../evaluation-framework.md).

## Out of scope for this pack

- Shipping remaining harness adapters
- Restoring a 1:1 dump of TOOLS.md into tools.json
- Treating agent-cage as a `./pfy start` harness
