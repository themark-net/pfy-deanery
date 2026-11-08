# continue-dev evq1107

STAY I1 reference: frozen Apache-2.0 IDE client. It does not serve a model, so it does not close gap L. pfy already writes a config and does not exec the IDE.

## What it is

Continue (continuedev/continue) is a coding agent shipped as a VS Code extension, a JetBrains plugin, and `@continuedev/cli`. The README at the pin says the repository is no longer actively maintained and is read-only, and that 2.0.0 was the final release (anonymous telemetry and sign-in removed). License is Apache-2.0: the LICENSE file is the Apache 2.0 text, the README footer says Apache 2.0 2023-2026 Continue Dev, Inc., and the GitHub API `license.spdx_id` is Apache-2.0.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `5522c6f44ca0ac3528b37244818fbfa39b5af470` |
| Commit | 2026-07-20 21:00:09 -0700, `docs: remove Sign in link (login flow retired) (#13005)` |
| ls-remote HEAD | same SHA on 2026-11-07 |
| Latest GitHub release | `v2.0.0-vscode`, published 2026-06-19, tag `03b05ef60c378ff06f9e39ada2e22c95fe9ef6ad`. This lane read main, not that tag. |
| Time | fetch plus checkout 13 s. No upstream script ran, so there is no probe time. |
| Size | worktree `du -sb --exclude=.git` 283463694 bytes. `.git` 189709184. cache src `du -sb` 473172878. |
| Cache | `~/.cache/pfy/tools/continue-dev/src`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` were under that cache. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. In `$CACHE/src`: `git init && git remote add origin https://github.com/continuedev/continue.git && git fetch --depth 1 --filter=blob:none origin 5522c6f44ca0ac3528b37244818fbfa39b5af470 && git checkout --detach FETCH_HEAD`.

No `sources/entries` file (the ticket entry was `-`). Status is the card.

## Ideas, and the pfy file each would touch

1. `config.yaml` schema v1 (`provider: llama.cpp` or an OpenAI-compatible provider, plus `apiBase`) replaces deprecated `config.json`. Touch `bootstrap/continue/config.json` and `docs/modules/continue-recipe.md`. The stub still writes JSON.
2. Model roles chat, autocomplete, edit, apply, and embed share one local base. Same two files. The recipe has one model, `local-coder`.
3. Plan mode sends read-only tools. Agent mode can edit files and run a terminal command. Touch `docs/ops/loop-engineering.md` and `harness/write-guard-mcp`. Those already split read and write. Do not import the tool list.
4. An air-gap note is a local vsix, telemetry off, and a local provider. The 2.0.0 README says telemetry and auth were removed. Touch `bootstrap/continue/README.md`. Do not borrow the CLI, the JetBrains plugin, or the tree.

## What we already have

Same job: an editor or chat surface on a local OpenAI base. Gap L in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is a second inference engine. Continue is a client of that engine.

| Card | Stage | What it covers | How Continue compares |
| --- | --- | --- | --- |
| Ollama | I2 | Local OpenAI server. `./pfy start ollama`. | The engine. Continue would call it. |
| llama.cpp server mode | I1 | GGUF server already in the pfy up order. | Docs show `provider: llama.cpp` and `apiBase` `http://localhost:8080`. Still a client. |
| LiteLLM | I2 | One proxy for Grok and local models. | Continue is not a proxy. |
| Strata | I2 | Second engine trial on gfx1151. Slower than Ollama. | Also an engine. Continue does not close L. |
| Grok CLI bootstrap | I3 | Operator env. ADR-0002 rejected Continue as primary. | The operator path. |
| Aider | I1 | Headless git editor. The 2026-11-07 probe stayed I1. | A CLI. The IDE is not that path. |
| Open WebUI | I1 | Chat UI. The product window is pfy's. | Another UI on the same base URL. |
| codebase-memory-mcp | I2 | Primary code graph. | The embed role overlaps it. Grok already uses the MCP. |
| AgenC | I0 | Daemon agent. Not the operator. | Another coding surface. ADR-0010 rejects it. |

`SUBTREES.md` already excludes full IDE agents. T-0108 (the Continue recipe) is done. `./pfy start continue` is STUB exit 2 and writes `$PFY_STATE_DIR/continue-config.json` from `LOCAL_OPENAI_BASE_URL`. It does not exec the IDE.

## Gates

Value (3 of 4 for I3): gap fill no, operator leverage no (the recipe already shipped; this lane did not use it), evidence no (docs read only; the IDE was not started), blast radius yes (Apache-2.0, no weights, not the primary runtime). Score 1 of 4.

Modularity (all 4 for a local copy): the README and config docs were enough, the unit is a monorepo (extension, JetBrains, CLI, core, gui), the cache copy is isolatable, and deleting it leaves the pin. 2 of 4. 283463694 bytes exceeds the 50 MB I2 limit. Potential is low.

`uses` and `features` do not name a CI, test, or review role. No `self_pipeline` field. No gate wiring. TOOLS.md already has the row. This lane did not edit it.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Stale JSON recipe | An operator pastes `config.json`. Upstream marks that format deprecated. | Stay I1. A later ticket can emit `config.yaml` only if someone uses the file. |
| Unmaintained tree | The July 2026 pin is treated as a live product. | The README says read-only. Do not install. |
| Size | The monorepo lands in git. | Cache only. `SUBTREES.md` already forbids the embed. |
| Gap L false pass | A client is counted as a second engine. | Engines stay Ollama, llama-server, and Strata. |

## Next gate

Stay I1 reference. I3 only if an operator uses the generated config on a real edit. Not a Feature GO.

## Pipeline questions

This lane does not put Continue on a pipeline.

1. Trigger, if adopted later: a person installs the extension and opens the generated config. Not the evq scheduler.
2. It would read `apiBase` and send chat or autocomplete to the local engine. It would not serve the model. This lane called no model and used no account.
3. Next: nothing in pfy. The session stays in the IDE.
4. A human re-enters before any install, any exec of the IDE, or any I3 claim.
5. One worktree per slug already keeps this card private. Do not start a second trial against the same config home.
