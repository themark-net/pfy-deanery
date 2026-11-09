# Cartographer static eval (I0 to I1)

Pin `f96e5d9f7b0ae8506ce5470e35372546a70ea292` (committer date 2026-11-08). License Apache-2.0, from the LICENSE file at that pin. This pass shallow-fetched that commit into a throwaway directory. `du -sb` is 27908157 bytes including git. `du -h` reports 33M of disk usage. The worktree without `.git` is 20568768 bytes. No `.gguf`, `.safetensors`, `.onnx`, `.pt`, `.bin`, or `.wasm` files. The binary was not built. `cartographer setup` was not run. The public demo server was not contacted.

Intake: `duplicate cartographer data/stages/cartographer.json`. Stop. No second card. The card is already I1 and `tier_ceiling` is already I1. This pass does not edit `integration_stage` or `tier_ceiling`. The entry `sources/entries/172-cartographer.md` remains the narrative receipt. No TOOLS.md row and no `data/tools.json` row.

## What was confirmed in source

`docs/overview.md` describes one Go binary. Agents read and write a git repository of Markdown concepts only through MCP tools. The server validates, takes one commit per logical write, and can refuse a write. Search indexes are derived and can be rebuilt. `docs/control-plane.md` names the read path (`search`, `concept_read`, `graph_context`) and a write gate that runs before the commit. `internal/kb/kb.go` has `ReadConcept` and `WriteConcept`. `internal/search/index.go` searches that store.

`README.md` says `cartographer setup` installs a local service, creates a knowledge base, and connects every agent client it detects. `cartographer connect` writes MCP settings, instructions, skills, subagents, and hooks into each client's own files. That is the blast radius for any later trial: a throwaway `HOME` only.

This lane did not execute a health check, a write, or a client sync. Those remain README claims.

## Against the two memory tools already here

| Job | Cartographer at this pin | codebase-memory-mcp (I3) | opencode-mem (I2) |
| --- | --- | --- | --- |
| What is stored | Markdown concepts in a git repo the operator owns | A code graph of a repository | Session notes in a local vector store |
| Who writes | MCP tools. The server owns the files and the commit. | An indexer builds the graph. Agents query it. | The plugin's add and search calls |
| Shared across clients | One wiki for Claude Code, Codex, OpenCode, and other MCP clients, plus files it syncs into those clients | The Grok code-graph MCP | The OpenCode worker |
| What a static read can say | The job is a shared wiki with a write gate | It does not store a team wiki | It recalls stored notes. It does not version a wiki in git |

The three tools share the word memory. They do not share the job. Cartographer does not replace the code graph, and it does not replace stored-note recall. This pass did not measure either claim with a run. Keeping both neighbors is the point of the comparison.

## Supersede

Cartographer is not the suite in `docs/ops/supersede-watch.md`.

| Part | Level | Why |
| --- | --- | --- |
| track | none | It does not watch outside sources for new tools. |
| catalog | none | A knowledge base is not a deduped tool catalog. |
| evaluate | none | No rubric of improvement vectors and no I-stages. |
| integrate | partial | It is a local MCP server someone could attach. It is not wired here. |

`python3 scripts/supersede_check.py --parts integrate` prints `{"parts": ["integrate"], "supersede_candidate": false}`. One part is not a candidate. No watchlist row.

## Gates

Value gate fails. The gap (a git wiki none of the current memory tools are) is real on paper. There is no day of operator use, no smoke of our own, and `setup` rewrites detected agent clients, so the blast radius is not acceptable until a throwaway home is the only home it sees.

Modularity gate passes. The behavior that matters is the write gate and the client sync, which the README does not fully specify. The unit is one Go binary. Deleting a throwaway clone leaves the pin and the entry. The shallow fetch is under the 50 MB I2 size note (27908157 bytes apparent, 33M on disk) and there are no weight files. This verdict still proposes I1. `tier_ceiling` is I1, so a proposed I2 would be above the ceiling. This pass does not raise the ceiling.

The trial plan is `docs/ops/i2-trial-localharness-cartographer-1108.md`.

## How this fails and how we recover

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Treated as a second code graph | A session queries Cartographer for symbols | Keep codebase-memory-mcp for that job. The trial records a miss on a code question. |
| Treated as opencode-mem | A salt search is expected to hit | Different store. The trial plants a wiki fact, not a salt. |
| `setup` rewrites real clients | It connects every detected agent | Trial uses a throwaway `HOME` and `serve --kb` on a local repo. No public demo. |
| Pin drift | `main` moves | The card pin is this SHA. The entry smoke still checks it. |
