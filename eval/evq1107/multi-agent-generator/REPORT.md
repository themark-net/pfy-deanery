# multi-agent-generator evq1107

STAY I0 reference: team-source emitter does not move the pfy build timeout

## What it is

multi-agent-generator (aakriti1318/multi-agent-generator) is a Python library and CLI that turns one sentence into CrewAI, CrewAI Flow, LangGraph, Agno, ReAct, or ReAct LCEL source, or into JSON. License is MIT. `LICENSE` copyright 2025 Aakriti Aggarwal. `pyproject.toml` says version `1.0.0`, Python >= 3.8, and console script `multi-agent-generator`. Declared dependencies: litellm, streamlit, langchain>=0.3.0,<0.4.0, langchain-core>=0.3.0,<0.4.0, langchain-openai>=0.2.0,<0.4.0, langgraph>=0.2.0, python-dotenv, pydantic, agno==2.3.24. WatsonX is optional. `requirements.txt` also lists crewai, openai, and ibm-watsonx-ai, and it does not list litellm. CrewAI is not imported by the package. The name appears in emitted strings and in `docs/tools.md`. The default CLI framework is crewai and the default provider is openai.

`AgentGenerator.analyze_prompt` calls LiteLLM. Hardcoded defaults: openai `gpt-4o-mini`, ollama `ollama/llama3.2:3b`, temperature 0.7, max_tokens 1000, overridable with `DEFAULT_MODEL`. Pattern pick in `Orchestrator.suggest_pattern` is a keyword list with no model. The five classes (supervisor, debate, voting, pipeline, map_reduce) emit string templates. Enum names round_robin, hierarchical, and broadcast raise `ValueError`. The debate template tells the speaker to be fair and to acknowledge a compelling opposing argument. It does not require a critique. The tool registry templates include `shell_command` (`shell=True`) and `python_executor` (write a temp file, run python).

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `2bf55b5a665340295ab8d3fc28e684cbc9256c06` (GitHub HEAD at fetch) |
| Commit | 2026-04-10 14:27:28 +0530. Merge pull request #19, dependabot agno-2.3.24. |
| Version | pyproject `1.0.0`. No tag object was fetched. |
| Fetch | same clock second (elapsed 0 s). `git init`, `git fetch --depth 1 origin 2bf55b5a665340295ab8d3fc28e684cbc9256c06`, `git checkout --detach FETCH_HEAD`. No upstream script. |
| Bytes | worktree 1717242. `.git` 1477645. |
| Cache | `~/.cache/pfy/tools/multi-agent-generator/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` sat under `~/.cache/pfy/tools/multi-agent-generator`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. This lane did not install the package and did not run the CLI.

## Ideas, and the pfy file each would touch

1. A closed pattern name (supervisor, debate, voting, pipeline, map-reduce) chosen before spawn. Touch `docs/ops/loop-engineering.md` beside the four loop types. Loop type already says when a run stops.
2. Keyword pattern pick with no model, then a template. Touch `bootstrap/grok-cli/skills/agent-loops/SKILL.md`. The loop card is already written before the run.
3. A debate seat that must disagree. This pin's template allows agreement. Touch `docs/ops/gstack-role-recipes.md`. The code-review skill already splits standards and spec.

## Catalog comparison

Gap B in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is `./pfy build`: the 3 hour timeout and two parked pregate FAILs. Entry 079 is outside that ranking's 137 to 167 table. This lane builds no pipeline step. Tags on this card (`#orchestration`, `#codegen`, `#crewai`, `#langgraph`) match the emit job. Same job, already covered:

| Tool | Stage | Cover |
| --- | --- | --- |
| Finn Loop / 8-exits | I1 | `orchestration` toolset. Uses: exit cards and loop types. |
| LangGraph (LangChain) | I1 | Tag `#orchestration`. Uses: graph orchestration. Our loops cover the operator path. |
| gstack | I1 | Tag `#multi-agent`. Uses: role patterns already ported. |
| Auto-Company | I1 | Tag `#multi-agent-org`. Uses: persona patterns, not a runtime. |
| kanbots | I1 | Tag `#multi-agent`. Probe did not move the timeout. |
| Multica | I1 | Tags `#multi-agent` `#orchestration`. Uses: board, not our orchestrator. |
| squadra | I1 | Manual seats on one task. |
| Festival | I1 | Filesystem plan for a long goal. Did not close the timeout. |
| Rulora | I1 | Loop counters. The host still stops the lane. |
| DSPy | I1 | Tag `#litellm-ready`. Compile a prompt program. |
| LiteLLM | I2 | Tag `#litellm-ready`. The proxy we already smoke. |
| project-process bootstrap | I3 | Scaffolds process docs, not an agent team. |

## Gates

Value (3 of 4 for I3): gap fill no. Operator leverage no. Evidence no: this lane did not run the one-liner, and the default provider is openai. Blast radius yes: MIT, no weights, worktree 1717242 bytes. Score 1 of 4.

Modularity (all 4 for a local copy): the README, `docs/orchestration.md`, and `pyproject.toml` were enough, so local code was not required. One console script. The cache copy is isolatable, and deleting it leaves the pin. 3 of 4. Potential is low, so I2 does not open. `TOOLS.md` says `(I0)`, so the ceiling stays I0.

`uses` and `features` do not name a CI, test, or review role token. No `self_pipeline` field. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Hosted default | CLI default provider openai calls `gpt-4o-mini` | Do not run the CLI. This lane did not. |
| Emitted shell | `shell_command` uses `shell=True`. `python_executor` runs a temp file | Do not install, and do not run emitted code. |
| Two dependency lists | `requirements.txt` and `pyproject.toml` disagree on crewai, openai, watsonx, and litellm | Stay on the pin. Do not install. |
| Agreeable debate | The template tells the speaker to acknowledge a strong opposing point | Keep critique in `docs/ops/gstack-role-recipes.md`. |
| Dead enum names | round_robin, hierarchical, broadcast raise `ValueError` | Treat the five classes as the whole set. |
| Pin drift | Entry text said a 2026-08-01 push. This HEAD is 2026-04-10 | Keep `2bf55b5`. |

## Next gate

Stay I0 reference. Reopen only if a later ticket adds a pattern name to `/agent-loops` and still does not install this package. Gap B stays the pfy build timeout. No gate. Not a Feature GO.

## Pipeline questions

This lane does not put the tool on a pipeline. The scheduler started a read. The lane writes this directory, the card, and the entry Status line.
1. Trigger, if adopted later: a person asks for a throwaway team sketch. Not this scheduler and not a gate.
2. It would read one sentence and write Python or JSON for another framework. The roster path calls LiteLLM. Default provider is openai. This lane called no model and used no account.
3. Next: a person reads the sketch. Nothing in pfy starts from it.
4. A human re-enters before any install, any CLI run, any copy of emitted code, or any I1 move.
5. One worktree per slug keeps this card private. Two runs must not share a real home or an API key.
