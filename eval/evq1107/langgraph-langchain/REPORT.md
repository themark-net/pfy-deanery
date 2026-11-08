# langgraph-langchain evq1107

STAY I1 reference: a second graph runtime does not close the pfy build timeout. MIT. Docs only. Gap B stays open.

## What it is

LangGraph (langchain-ai/langgraph) is a low-level orchestration framework for long-running stateful agents. The root README says it is inspired by Pregel and Apache Beam, the public interface draws on NetworkX, and it can be used without the LangChain product. `libs/langgraph/pyproject.toml` still depends on `langchain-core>=1.4.7,<2`. License is MIT (root LICENSE, copyright 2024 LangChain, Inc.; GitHub `license.spdx_id` is MIT). Packages at the pin: langgraph 1.2.20, langgraph-checkpoint 4.3.1, langgraph-prebuilt 1.1.1. `langgraph-cli` `__version__` is 0.4.42 in `libs/cli/langgraph_cli/__init__.py` (file read, not executed). Prebuilt ships `create_react_agent`. The CLI creates projects and runs them locally or in Docker. Checkpointers save state at every superstep and keep pending writes from nodes that already finished. The checkpoint README shows `InMemorySaver`. The SQLite README is the local saver (`SqliteSaver`). The Postgres README is the durable saver (`PostgresSaver`). The default serializer allows any Python type unless `LANGGRAPH_STRICT_MSGPACK=true`. The overview page linked from the pin README says human-in-the-loop pauses a run, then inspects or edits state and continues. The persistence page splits a thread checkpointer from a cross-thread store. LangSmith, Studio, and Agent Server are hosted. No `sources/entries` file (the ticket entry was `-`). Status is the card.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `e5e37b5d70dbfd93c7006bd90a658c6179a95946` |
| Commit | 2026-11-06 16:08:12 +0000. `fix(langgraph): match whole namespace segments in get_subgraphs (#9615)` |
| ls-remote HEAD | same SHA on this read |
| Latest GitHub release | `sdk==0.4.14`, published 2026-11-06. That tag is the SDK. This lane pinned main HEAD. |
| Time | fetch plus checkout 0.74 s. No upstream script ran. |
| Size | GitHub API `size` 531827 KB. Sparse worktree `du -sb --exclude=.git` 121221 bytes. With `.git`, 310327. |
| Cache | `~/.cache/pfy/tools/langgraph-langchain/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` were under that cache. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. Command: `git init`, remote `https://github.com/langchain-ai/langgraph.git`, sparse-checkout patterns `README.md`, `LICENSE`, `docs`, and the library pyproject paths (`README.md` also matched other READMEs), `git fetch --depth 1 --filter=blob:none origin e5e37b5d70dbfd93c7006bd90a658c6179a95946`, `git checkout --detach FETCH_HEAD`.

## Ideas, and the pfy file each would touch

1. Save a superstep and skip nodes that already wrote. Touch `docs/ops/loop-engineering.md`. The eight exits and `/agent-loops` already stop a loop. Leave the checkpointer out.
2. Pause, edit state, and resume on a thread id. Touch `docs/ops/human-decision-inventory.md`. Decisions already batch into an OQ or a default. Cage session resume is T-0047, a harness session.
3. Pending writes skip finished nodes in one superstep. ATG freeze is the same family. Touch `docs/eval/ATG-FRAMEWORK-EVAL.md` item 9, which already says skip LangGraph adapters. `docs/build-dropins/atg-framework.md` keeps the core free of LangGraph.
4. A strict deserializer allow-list. Touch `harness/write-guard-mcp` only as a reminder. Leave `JsonPlusSerializer` out.

## Catalog comparison

Same job: stateful multi-actor graphs. The scheduler queued this slug under gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07). That section says nothing in entries 137 to 167 closes B, and B is a bug in `./pfy build`. This lane builds no pipeline and no gate.

| Tool | Stage | What it covers | How LangGraph compares |
| --- | --- | --- | --- |
| Atomic Task Graph (ATG) | I2 | Compile, waves, freeze, repair. The card says LangGraph overlaps run-a-DAG. | Same job. The ATG eval skips the adapter. |
| Finn Loop | I1 | Exit cards and loop types, already the orchestration toolset. | The operator loop. LangGraph is a library runtime. |
| DSPy | I1 | Compile a prompt program. Advisory only. | TOOLS.md already calls LangGraph more boilerplate for simple cases. Gom Jobbar uses DSPy. |
| multi-agent-generator | I0 | Emits LangGraph source. Reference read only. | A generator of this runtime. |
| Multica | I1 | Multi-agent board. Not our orchestrator. | A board. |
| gstack | I1 | Role patterns already ported. The card says do not clone the repo. | Docs patterns. |
| kanbots | I1 | Kanban fan-out. The probe did not move the pfy build timeout. | Same gap B. A board. |
| MCO | I1 | Parallel raw-answer review. The probe did not move the pfy build timeout. | Same gap B. |
| mattpocock/skills | I1 | Planning and review skills already on the skill path. | Skills on the path. |
| Hermes Agent | I1 | Feedback-loop pattern ported as a skill. The card leaves the Hermes runtime out. | The same pattern-only choice. |
| agent-cage (PNNL) | I3 | Isolated lab for Grok. | The harness. |

CrewAI, AutoGen, and Haystack have no catalog row.

## Gates

Value (3 of 4 for I3): gap fill no (B is the build timeout; loops and ATG cover graphs). Operator leverage no (langchain-core, a checkpointer, and a hosted LangSmith path). Evidence no (docs only; nothing ran). Blast radius no (MIT and no weights, and making it the loop runtime would be a takeover with no ADR). Score 0 of 4.

Modularity (all 4 for a local copy): the README and checkpoint docs were enough, the unit is a monorepo (langgraph, checkpoint, prebuilt, cli, sdk, postgres, sqlite), the cache copy is isolatable, and deleting it leaves the pin. 2 of 4. GitHub size 531827 KB is over the 50 MB I2 bar. Potential is low, so the I2 shelf does not apply. Uses, features, and tags name no pipeline role. No `self_pipeline`. TOOLS.md already has the row. This lane did not edit it. No `data/tools.json` row for this name. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Runtime takeover | `./pfy build` is rewritten as a StateGraph | Stay I1. Loops stay `/agent-loops`. |
| Deserialization | A checkpoint loads arbitrary types | Do not install. The checkpoint README names `LANGGRAPH_STRICT_MSGPACK`. |
| Hosted LangSmith | Studio or Agent Server needs an account | No account. This lane called no API. |
| Size | The monorepo lands in git | Cache only. GitHub size 531827 KB. |
| Gap B false pass | A graph library is counted as the build-timeout fix | Verdict stays I1. |

## Next gate

Stay I1 reference. Re-open only to copy one pattern name into `docs/ops/loop-engineering.md`, with no install and no code copy. Not a Feature GO.

## Pipeline questions

This lane does not put LangGraph on a pipeline. The scheduler started the read. It writes this directory and the card. No model and no account.

1. Trigger, if adopted later: a person installs `langgraph` and compiles a StateGraph. The evq scheduler stays out of that.
2. It would read thread state and write checkpoints, or call LangSmith. This lane only read docs.
3. Next: nothing in `./pfy`. The build timeout stays in pfy's own code.
4. A human re-enters before any install, any LangSmith account, or any I2 copy.
5. One worktree per slug (`bot/evq-langgraph-langchain-1107`) keeps this card private.
