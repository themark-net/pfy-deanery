# Model choice and cost-gated compare

Per-task local or cloud model, plus an explicit paid check of a local catalog-fit run. Design for the Loop / Engine surface. Code: `pfylib/model_choice.py`. Operator: `./pfy setup`, `./pfy model-choice`, `./pfy compare`.

UI: Design-in-loop. Pack in docs/design/ before product UI. Never ask what we know. Levers stay contextual to the current view.

## Catalog check

Read `docs/eval/TOOLSET-RANKING.md` and the stage cards before adding a path.

| Tool | Card | Decision |
|------|------|----------|
| LiteLLM | I3. One OpenAI-compatible proxy for Grok and local models. Non-goal: vendor the server. | Reuse. Cloud calls go to the existing proxy (`LITELLM_BASE_URL`, else `http://127.0.0.1:4000/v1`) using `config/litellm/*.yaml`. No new provider SDK. |
| HiRoute | next_gate: do not wire into `./pfy`. | Leave unwired. This slice is an operator choice per task, not a difficulty router. |
| llm-router | Stay I0. Do not wire. Value gate failed. | Leave unwired. A free-first classifier is a different job. |
| HarnessRouter | Stay I0. Do not wire a gate. | Leave unwired. One API in front of harnesses is not model choice. LiteLLM is already the model proxy. |
| Jev (`scripts/pfy_jev_230.py`) | Decision layer for Choice / confidence. | Stays the gate. Model choice only picks which model fills a rubric. `PFY_JEV_MODEL` is not aliased. |
| Hedge (`pfylib/hedge.py`) | Local-first session lane and integer credits. | Stays. Compare is USD from `data/model-prices.json`, not a second ledger. |

Nothing new was adopted. No second router, no second GUI page.

## Software factory

1. **Trigger.** Operator, in setup, on the Loop or Engine view, or `./pfy model-choice set`. Compare: `./pfy compare catalog-fit --against <model>`, or the Loop / Engine "Compare last local catalog-fit run" button. Reminder: `./pfy status` and one call at the end of `scripts/catalog_loop.sh`, only when the last compare is older than 14 days and a newer `eval/catalog-fit/*.json` exists.
2. **Reads / writes.** Reads committed `config/model-choice.json`, user override `XDG_CONFIG_HOME/pfy/model-choice.json` (default `~/.config/pfy/`), `PFY_MODEL_<TASK>`, LiteLLM yaml model names, Ollama `GET /api/tags` (no pull), `data/model-prices.json`, catalog-fit goldens and `eval/catalog-fit/`. Writes the user override, `XDG_STATE_HOME/pfy/model-compare.json`, and `./tmp/compare-*.json`. Cloud POST goes to the LiteLLM proxy only after a yes.
3. **Triggers next.** A saved choice is what `resolve(task)` returns. catalog-fit triage calls it. Compare writes a verdict diff. Nothing starts a lane, a pull, or another compare.
4. **Human re-enters.** Every cloud backend is an explicit config or `cloud:` value. Compare prints the price line and waits for `y` / `yes` on a TTY, or `--yes` plus `--max-usd`. The reminder only prints a command.
5. **One run.** A lock file beside the compare state (`O_CREAT|O_EXCL`). A second compare exits with "compare already running". A lock older than one hour is removed and the new run proceeds. The reminder never takes the lock.

## Grill (decided here)

- User override is config (`~/.config/pfy/`), compare history is state (`~/.local/state/pfy/`), same family as the setup ledger. Not in the repo.
- Unprefixed model names stay local. Only `backend: cloud` or a `cloud:` prefix selects cloud. Nothing silently switches.
- catalog-fit default is local `qwen3.6:35b`, fallback local `qwen2.5:14b` when detected tags omit the preferred tag, or when Ollama says the tag is missing. Fallback never goes to cloud.
- `PFY_CATFIT_MODEL` is an alias under `PFY_MODEL_CATALOG_FIT`. `PFY_JEV_MODEL` is not an alias.
- Golden replay does not take a model (`requires_llm` false). Selectable classes: catalog-fit, eval-lane, eval-suite, matrix, decision-route, build-lane. This slice wires the caller for catalog-fit only. The others are stored for `resolve()` and the same controls.
- Compare MVP task is catalog-fit. Other task names refuse.
- Token counts: tiktoken, else LiteLLM `token_counter`, else chars/4 labeled `(approx)`. Prompt tokens come from the prompts. Completion tokens for the estimate come from the local output length.
- Prices live in `data/model-prices.json` with source URL and fetched date. Older than 45 days requires `--accept-stale-price`. Unknown model raises `UnknownModelPrice`.
- `--yes` without `--max-usd` does not run. Estimate above `--max-usd` does not run. No TTY and no `--yes` does not run.
- GUI controls sit on Loop step "where work runs" and repeat on Engine. No new sidebar item. Prefill is the resolved choice. Options are detected local tags plus LiteLLM cloud aliases and priced cloud models. The page does not ask for a model the config or the proxy already has.
- JS posts the server payload. It does not price a run.

## Information architecture

Sidebar stays Loop / Engine / Stage / Attach.

Loop, under "1. Where work runs" (local compute | cloud orchestration): one row per task class. Local and cloud are buttons. The select lists models. The current choice is selected. "Compare last local catalog-fit run" sits on that step because that is the work being checked. The first click returns the price line from `./pfy compare`. "Run it" sends that cost back with confirm. The server recomputes and refuses if the cap is below the estimate.

Engine shows the same rows. The local model and the per-task choice are the same subject.

Setup prints the same rows, prefilled, with detected local tags and configured cloud names. Enter keeps the row. `--model-choice task=backend:model --yes` writes the user file and does not prompt.

## Primary journey

1. Operator opens Loop or runs `./pfy setup`. Each task shows `local` and the committed model.
2. They set catalog-fit to `cloud:grok-4.7` or leave it local.
3. Later, status prints: it will cost about a few cents to check the last local catalog-fit run.
4. They run `./pfy compare catalog-fit --against grok-4.7`. The process prints the token line, the provider, the source, and the fetched date, then waits.
5. `y` or `--yes --max-usd <limit>` runs one cloud call per case through LiteLLM. The diff lands in `./tmp`. `n`, a closed stdin, a stale price, an unknown model, or a cap below the estimate runs nothing.

## Non-goals

- Wiring HiRoute, llm-router, or HarnessRouter.
- A new provider SDK, a new window, or a settings page.
- Silent cloud, automatic compare, pulling an Ollama model, or putting keys in the repo, logs, or tests.
- Replacing Jev or the hedge credit ledger.
- Compare for tasks other than catalog-fit.
- Changing `scripts/catalog_fit_triage.py` beyond the resolve and call handoff, or `scripts/catalog_loop.sh` beyond the reminder call.
