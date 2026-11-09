# LocalHarness static eval (I1)

Pin `5af7511ce8f8f799f74de877698e4c4aec0dec45` (tag text in the commit subject: release 0.27.7). License MIT. Shallow clone under the lane tmp, 20M including git. Nothing was installed. `localharness start` was not run. No model fetch.

Intake: `duplicate localharness sources/entries/171-localharness.md`. The entry exists. The stage card did not, so this lane created it with `pfylib.stage_registry.write_tool` and then `scripts/catalog_apply_verdict.py`. No TOOLS.md row and no `data/tools.json` row.

## What was confirmed in source

Six features named in the ticket are present in this pin. None of them was executed.

| Feature | Where in this pin | What the code actually does |
| --- | --- | --- |
| GGUF llama.cpp launch sizing | `src/localharness/provider/gguf_header.py` (`read_tensor_table`, `kv_layers`), `src/localharness/provider/tuning.py` (`derive`, `launch_pricing`) | Reads the GGUF header and tensor table, then prices a llama.cpp launch (KV cache type, MTP draft share). Docs in `docs/runtimes/llamacpp.md` show `localharness` spawning `llama-server`. `start` can also offer a download. |
| Per-tool-call permission gate | `src/localharness/agent/gate.py`, `agent/permissions.py`, `agent/verdict.py`, `agent/shell_classify.py` (`classify_shell`), `tools/capabilities.py` (`assert_no_coresidence`) | One gate in front of tool calls. A channel that cannot ask denies the call. Deny patterns match tool name and arguments. The capability floor refuses a tool set that both ingests untrusted bytes and holds host-changing tools. |
| YAML agents | `src/localharness/config/loader.py` `discover_agents` | Loads `agents/*.yaml` from the project layer and the machine layer. The project file wins on the same stem. |
| SKILL.md skills | `src/localharness/config/skills.py` | Reads project `.localharness/skills` and `.agents/skills`, machine `skills`, and bundled `assets/skills`. Requires frontmatter `name` and `description`. Caps the list. A skill is text and grants no tool. |
| SQLite memory | `src/localharness/memory/sqlite.py`, `memory/consolidation.py` | Facts in SQLite with FTS5. Superseded rows stay out of the hot path. An idle consolidation pass updates standing. The memory plugin is on by default. The embeddings extra is a separate install and was not used. |
| Experiment loop | `src/localharness/autoresearch/`, `docs/plugins/autoresearch.md` | Proposes one change from failed bench traces, tests it on training scenarios and a holdout, and leaves adopt to a person. On by default. This grades the harness, not outside tools. |

`src/localharness/registry/catalogue.py` lists harness settings for `localharness components list`. It is not a catalog of outside tools.

Upstream claims this lane did not re-run: live validation on a DGX Spark, Ollama as a CPU round trip only, and the llama.cpp doc's ROCm and Vulkan build flags. Strix Halo was not measured.

## Against the local lanes in this repo

| Lane already here | What it covers | What LocalHarness adds on paper | Decision for this pass |
| --- | --- | --- | --- |
| Grok Build plus OpenCode (ADR-0011) and the pluggable runtime (ADR-0014, `scripts/detect-local-runtime.sh`) | Monitor on Grok. Worker on OpenCode. Attach to a server that is already up (FreeToken, llama-swap, llama-server, Ollama). | A full agent loop that can size and spawn llama.cpp itself. | Do not replace the operator surfaces. |
| `scripts/model_lock.sh` | `flock` so one local-model command runs at a time. | Nothing like that lock. Different job. | Keep the lock. |
| destructive_command_guard (I3) | Classifies one shell command. | A gate on every tool call, plus the capability floor, plus shell classification inside the harness. | Do not swap the guard out. The floor is the piece we do not have. |
| Sandlock (I3) | Rootless confinement of one fetched-skill install. | No landlock-style installer sandbox in the files read here. | Do not swap Sandlock out. |
| `bootstrap/grok-cli/skills/` | SKILL.md source of truth for Grok and OpenCode. | Another reader of the same Agent Skills shape, with its own directories and caps. | Do not add a second skill root. |
| codebase-memory-mcp (I3) and opencode-mem (I2) | Code graph, and session notes the repo does not contain. | A third store: SQLite facts for the harness. | Do not turn that store on beside the two we run. |
| Catalog eval lanes | Score outside tools and record I0 to I4. | Autoresearch scores changes to LocalHarness itself. | That loop is not our evaluate step. |

## Supersede

Parts, using `docs/ops/supersede-watch.md`:

| Part | Level | Why |
| --- | --- | --- |
| track | none | It does not watch X, GitHub, or feeds for new tools. |
| catalog | none | No deduped record per outside tool. The component catalogue is settings inside the harness. |
| evaluate | none | The bench and autoresearch grade this harness. They do not score outside tools on improvement vectors with staged evidence. |
| integrate | partial | It is a local harness someone could run. It does not wire catalog tools into this repo with a run on main. |

`python3 scripts/supersede_check.py --parts integrate` prints `{"parts": ["integrate"], "supersede_candidate": false}`. A row is added only when two or more parts are covered. No watchlist row.

Adopt it instead of building pfy-mentat: no. The product is the four-part suite. LocalHarness is a harness, in the same class as OpenCode, and ADR-0011 already picks the operator surfaces. The GGUF sizing and the capability floor are ahead of the glue we have. That is a reason for a later trial, not a reason to stop the catalog or to build a second copy of those two pieces before the trial.

## Gates

Value gate fails. Of the four I3 checks: a gap is only on paper, nobody used it for a day, this lane has no smoke of our own, and the blast radius is a whole agent runtime that can offer a model download and writes a home directory by default.

Modularity gate passes. Judging the floor and the launch pricing needs the code, not the README alone. The unit is one Python package with a CLI. A throwaway copy can be deleted without losing the pin or the entry. The shallow tree at this pin is 20M, under the 50 MB I2 size note, and it contains no weight files. This verdict still proposes I1. The trial plan is `docs/ops/i2-trial-localharness-cartographer-1108.md`.

## How this fails and how we recover

| Risk | How it fails | Recovery |
| --- | --- | --- |
| README treated as a run | A later card says the six features were measured | Evidence is this report and the pin. `runs` on the verdict is 0. |
| `start` fetches a model | The first launch offers a download | The trial attaches to a server that is already up and aborts on a fetch prompt. |
| Home directory writes | Default uv tool dir and `~/.localharness` | `UV_TOOL_DIR` and `HOME` stay under a throwaway directory. |
| Second harness becomes the product | Sessions move off Grok and OpenCode | Non-goal on the card. Needs a separate decision, not this verdict. |
| Watchlist false stop | Someone marks all four parts full | Checker output is in `VERDICT.json`. Re-read this table before adding a row. |
