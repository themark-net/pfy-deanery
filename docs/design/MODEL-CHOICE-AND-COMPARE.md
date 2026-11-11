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
| Jev (`scripts/pfy_jev_230.py`) | Decision layer for Choice / confidence. | Stays the gate. `PFY_JEV_MODEL` is the runner override for the Laya shadow model, not an alias inside `resolve()`. `typesafe_model()` stays `PFY_JEV_MODEL` or `jev-1.13.0` and posts to TypeSafe, not LiteLLM. |
| Hedge (`pfylib/hedge.py`) | Local-first session lane and integer credits. | Stays. Compare is USD from `data/model-prices.json`, not a second ledger. |

Nothing new was adopted. No second router, no second GUI page.

## Software factory

1. **Trigger.** Operator, in setup, on the Loop or Engine view, or `./pfy model-choice set`. Compare: `./pfy compare catalog-fit --against <model>` or `./pfy compare decision-route --against <model>`, or the Loop / Engine "Compare last local catalog-fit run" button. Reminder: `./pfy status` and one call at the end of `scripts/catalog_loop.sh`, only when the last compare is older than 14 days and a newer `eval/catalog-fit/*.json` exists. The reminder stays on catalog-fit. Price refresh: the online half of that same loop, at most once per 7 days. `PFY_CATALOG_OFFLINE=1` skips it.
2. **Reads / writes.** Reads committed `config/model-choice.json`, user override `XDG_CONFIG_HOME/pfy/model-choice.json` (default `~/.config/pfy/`), `PFY_MODEL_<TASK>`, LiteLLM yaml model names, Ollama `GET /api/tags` (no pull), `data/model-prices.json`, the public `source` URLs in that file (GET, no auth), catalog-fit goldens and `eval/catalog-fit/`, and `data/decision-gates/laya-trial.cases.v0.json`. Writes the user override, `XDG_STATE_HOME/pfy/model-compare.json`, `./tmp/compare-*.json`, and, when a price parse is confident, `in` / `out` / existing `cached_in` or `long_context` plus `fetched` in `data/model-prices.json`. The 7-day stamp lives under the loop STATE dir (`model-prices-refresh.json`), outside the repo. Cloud POST goes to the LiteLLM proxy only after a yes. The price job never POSTs.
3. **Triggers next.** A saved choice is what `resolve(task)` returns. catalog-fit triage and the runners below call it (or `runner_choice`). Compare writes a verdict diff. Nothing starts a lane, a pull, or another compare.
4. **Human re-enters.** Every cloud backend is an explicit config or `cloud:` value. Compare prints the price line and waits for `y` / `yes` on a TTY, or `--yes` plus `--max-usd`. The reminder only prints a command.
5. **One run.** A lock file beside the compare state (`O_CREAT|O_EXCL`). A second compare exits with "compare already running". A lock older than one hour is removed and the new run proceeds. The reminder never takes the lock. Price refresh stamps the attempt, including a failed fetch or parse, and skips until 7 days later. A not-due skip does not fetch and does not rewrite the stamp. `|| true` keeps a refresh failure from failing the tick.

## Grill (decided here)

- User override is config (`~/.config/pfy/`), compare history is state (`~/.local/state/pfy/`), same family as the setup ledger. Not in the repo.
- Unprefixed model names stay local. Only `backend: cloud` or a `cloud:` prefix selects cloud. Nothing silently switches.
- catalog-fit default is local `qwen3.6:35b`, fallback local `qwen2.5:14b` when detected tags omit the preferred tag, or when Ollama says the tag is missing. Fallback never goes to cloud.
- `PFY_CATFIT_MODEL` is an alias under `PFY_MODEL_CATALOG_FIT`. `PFY_JEV_MODEL` is not an alias.
- Golden replay does not take a model (`requires_llm` false). Selectable classes: catalog-fit, eval-suite, matrix, decision-route, build-lane. eval-lane was removed: `scripts/eval_lane.sh` calls grok with no model flag, and the catalog loop, `loop_worktree`, and `scripts/pfy_build_p.py` do not take a model.
- Compare tasks plug in through one adapter each (cases, prompt, verdict parser): catalog-fit and decision-route. eval-lane is not replayable. `eval/` and `eval/catalog-verdicts` store probe verdicts, not the prompts the lane sent. eval-suite, matrix, and build-lane have no labeled replay set here.
- decision-route replays `laya-trial.cases.v0.json` (the push_hold cases are in that file). The local side is `decide_choice` (token overlap, no second model call). The cloud side is one LiteLLM call per case. The user message is `decision_prompt()` from `examples/typed-decisions-local/trial.py` plus the fields `typesafe_evaluate` posts (`state`, `questions` with instructions and criteria). The label is not in the prompt. `--run` and `--last` do not filter this set. The same price gate, stale check, lock, and reminder rules apply. The reminder still only prints, and only for catalog-fit.
- Token counts: LiteLLM `token_counter` if importable, else tiktoken `o200k_base`, else chars/4. The estimate line always names the method: `(litellm)`, `(tiktoken o200k_base)`, or `(approx)`. tiktoken is an approximation for non-OpenAI tokenizers, including xAI. `make tokens-venv` creates `<repo>/.venv` and installs pinned `tiktoken` there only. `model_choice` adds that venv's `site-packages` when the import fails, and sets `TIKTOKEN_CACHE_DIR` to `<repo>/.venv/tiktoken-cache` so the BPE file is a read-only fetch into the venv. Prompt tokens come from the prompts. Completion tokens for the estimate come from the local output length.
- Prices live in `data/model-prices.json` with source URL and fetched date. Older than 45 days requires `--accept-stale-price`. Unknown model raises `UnknownModelPrice`. `scripts/model_prices_refresh.py` re-reads the xAI and OpenAI pages already listed. It updates numbers and `fetched` only when every HTTP model on that page parsed and every number is finite, positive, and at most $1000 per 1M. A missing model or a garbage number leaves the whole file untouched. It never adds or removes models or keys. `ollama:*` (`source: local`) is not fetched. xAI rows are input, cached, output. OpenAI Standard rows are input, output, cached. Batch rows are ignored. A long-context row updates `long_context` only when that object is already on the model.
- `--yes` without `--max-usd` does not run. Estimate above `--max-usd` does not run. No TTY and no `--yes` does not run.
- GUI controls sit on Loop step "where work runs" and repeat on Engine. No new sidebar item. Prefill is the resolved choice. Options are detected local tags plus LiteLLM cloud aliases and priced cloud models. The page does not ask for a model the config or the proxy already has.
- JS posts the server payload. It does not price a run.

## Information architecture

Sidebar stays Loop / Engine / Stage / Attach.

Loop, under "1. Where work runs" (local compute | cloud orchestration): one row per task class. Local and cloud are buttons. The select lists models. The current choice is selected. "Compare last local catalog-fit run" sits on that step because that is the work being checked. The first click returns the price line from `./pfy compare`. "Run it" sends that cost back with confirm. The server recomputes and refuses if the cap is below the estimate.

Engine shows the same rows. The local model and the per-task choice are the same subject.

Setup prints the same rows, prefilled, with detected local tags and configured cloud names. Enter keeps the row. `--model-choice task=backend:model --yes` writes the user file and does not prompt.

## Runners

Shared helper for shell and Make: `python3 -m pfylib.model_choice resolve <task> --field model|backend|spec`. `--transport ollama|litellm` and `--explicit` use `runner_choice`. Without either flag the command prints `resolve()` so `PFY_MODEL_<TASK>` still beats the alias env.

Runner-facing order: explicit flag or runner env, then `PFY_MODEL_<TASK>`, then the saved user file, then the committed default. Inside `resolve()` alone the order stays `PFY_MODEL_<TASK>`, then the alias env (`PFY_CATFIT_MODEL`, `EVAL_MODEL`, `PFY_LOCAL_BUILD_MODEL`), then the user file, then the default. Runners check their own flag or env before calling `resolve()`, so that flag wins.

A cloud choice takes effect only on a LiteLLM transport. catalog-fit already switches Ollama vs the proxy. The other four tasks are Ollama-only. `runner_choice` prints one line, `model-choice: <task> is Ollama-only; cloud:<model> refused; keeping <local>`, and returns the committed local model. The loop does not crash and nothing is spent.

| Task | Where the model is read | Explicit override | Cloud choice |
|------|-------------------------|-------------------|--------------|
| eval-suite | Host `make eval-suite` and `examples/eval-harness/run_scored_task.py` / `run-in-cage.sh` | `EVAL_MODEL`, then `LITELLM_SMOKE_MODEL` | Refused. Keeps `qwen2.5:14b` (or the committed local tag). The cage copy does not include `pfylib`, so the host Makefile resolves and passes `EVAL_MODEL`. An empty value is not passed. |
| matrix | Same harness, `EVAL_MODE=matrix` | `EVAL_MODEL` sets the gate only. `EVAL_MODELS` stays the column list. | Same refusal. Gate falls back to `qwen2.5:14b`. |
| decision-route | `laya_shadow_model()` in `scripts/pfy_jev_230.py` | `PFY_JEV_MODEL` | Refused. Keeps `qwen3.6:35b`. The shadow posts to local laya-serve. `typesafe_model()` is not wired. `examples/typed-decisions-local/trial.py` still pins `PFY_JEV_MODEL=english` when unset. |
| build-lane | `scripts/pfy_build_local.py` `_pick_build_model` and `scripts/pfy_local_build_eval.py` | `--model`, then `PFY_LOCAL_BUILD_MODEL` | Refused. Keeps `qwen3.6:35b`. Endpoint stays the local Ollama base. `scripts/pfy_build_p.py` has no model argument. |

`data/eval-lanes.json` defaults are unchanged. `EVAL_MODEL` on the Make command line or in the environment is `$(EVAL_MODEL)` and wins before `model_choice`.

## Primary journey

1. Operator opens Loop or runs `./pfy setup`. Each task shows `local` and the committed model.
2. They set catalog-fit to `cloud:grok-4.7` or leave it local.
3. Later, status prints: it will cost about a few cents to check the last local catalog-fit run.
4. They run `./pfy compare catalog-fit --against grok-4.7` or `./pfy compare decision-route --against grok-4.7`. The process prints the token line (with the counter name), the provider, the source, and the fetched date, then waits.
5. `y` or `--yes --max-usd <limit>` runs one cloud call per case through LiteLLM. The diff lands in `./tmp`. `n`, a closed stdin, a stale price, an unknown model, or a cap below the estimate runs nothing. A second compare while the lock is held does not run.

## Deferred

- eval-lane as a task class or a compare. No runner takes a model, and the stored verdict files are not the prompts the lane sent.
- Compare for eval-suite, matrix, and build-lane until a labeled replay set exists. Matrix model choice sets the gate only. `EVAL_MODELS` stays the column list.
- `typesafe_model()` stays `PFY_JEV_MODEL` or `jev-1.13.0`. TypeSafe is not LiteLLM.
- `scripts/pfy_build_p.py` has no model argument.
- `make tokens-venv` is the install path for tiktoken. This slice does not run it.
- The price job is not pointed at the live docs from tests or from this change. Fixtures cover the parser. A loop tick online will GET the pages, at most weekly, and leave the file alone if the parse is not confident.

## Non-goals

- Wiring HiRoute, llm-router, or HarnessRouter.
- A new provider SDK, a new window, or a settings page.
- Silent cloud, automatic compare, pulling an Ollama model, or putting keys in the repo, logs, or tests.
- Replacing Jev or the hedge credit ledger.
- Compare for eval-suite, matrix, or build-lane. Those runners take a model, but this repo has no labeled replay set for them.
- Treating eval-lane as a model-choice task or a compare task. It has no model-taking runner. Stored probe verdicts under `eval/` and `eval/catalog-verdicts` are not replayable prompts.
- Changing `scripts/catalog_fit_triage.py` beyond the resolve and call handoff. The loop calls the reminder and, online only, the price refresh.
- Adding models to the price table automatically, or refreshing from a page that did not list every model already in the file.
- Pointing `typesafe_model()` or `scripts/pfy_build_p.py` at model choice. TypeSafe is not the LiteLLM proxy. The product build launcher does not take a model.
