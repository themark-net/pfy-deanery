# Model choice audit

Standing asks checked here:

1. Every Deanery task offers a local or cloud choice at setup, on the operator screen, or on the CLI.
2. An opt-in compare of a past local result against Grok and GPT shows an estimate from real token counts and `data/model-prices.json` first, then waits for yes.
3. Default local model is `qwen3.6:35b`, with `qwen2.5:14b` when that default cannot load.
4. No paid call without that shown estimate and an explicit yes. Off a TTY the yes is a flag. The choice is remembered outside the repo.

This pass did not edit `scripts/catalog_loop.sh` or the lane scripts it launches. Production catalog loop internals are listed so they are not forgotten. They are not changed.

Shared rules already in `pfylib/model_choice.py`:

- User override: `$XDG_CONFIG_HOME/pfy/model-choice.json` (default `~/.config/pfy/`). Compare state: `$XDG_STATE_HOME/pfy/model-compare.json`.
- `--yes` without a covering `--max-usd` or `--max-cost` does not run. A covering cap alone is approval. Off a TTY, with neither a covering cap nor `--yes` plus a cap, the call does not start.
- A fresh `call_model` cloud quote counts the prompt, then adds a 512 completion-token allowance. That allowance is also `max_tokens` on that one request. It is not a measured completion. `./pfy compare` still prices the recorded local completion text and passes `paid_ok`, so it does not ask twice and does not add that cap.
- Prices older than 45 days block this new gate. Compare still has `--accept-stale-price`.
- Committed cloud defaults are ignored. A cloud backend is only an explicit operator choice.

Status words: MET (closed, including this pass), ALREADY-FIXED (true on main before this pass), GAP (still open, not parked), PARKED (left because the fix would touch the loop timer, invent a price, or fight a pin).

## Gap table

| Entry point | Local or cloud choice | Compare, cost first | Default and fallback | Paid gate | Choice outside the repo | Status |
|-------------|----------------------|---------------------|----------------------|-----------|--------------------------|--------|
| `./pfy model-choice` show, set, prompt | CLI per task | Not this verb | Shows the committed row | No model call | Writes the user file | ALREADY-FIXED |
| `./pfy setup` on a TTY | Prompts each task. Enter keeps the row | Not this verb | Shows the committed row | No model call | Save writes the user file | ALREADY-FIXED |
| `./pfy setup` off a TTY | Prints `./pfy model-choice set <task> <local:model\|cloud:model>` and says the committed default stays local | Not this verb | Does not switch the row | No model call | The set command writes the user file | MET |
| Operator Loop and Engine task rows | Local and cloud buttons, prefilled from `resolve` | Separate row below | Same committed defaults | Choice does not spend | Same user file | ALREADY-FIXED |
| Operator "Compare last local catalog-fit run" | Against `grok-4.7` only | First click returns the price line. "Run it" sends that cost. The server recomputes | Local side is the recorded catalog-fit run | Refuses when the cap is under the estimate | Compare state file | GAP |
| `./pfy compare catalog-fit` and `./pfy compare decision-route` | `--against grok-4.7` or `gpt-6.1-sol` | Estimate from counted tokens and the price table, then `y` or a cap | Local side is the recorded run, not a new local call | Off a TTY needs the flag. Unknown model and stale price do not send | Compare state file | ALREADY-FIXED |
| `./pfy status` compare reminder | Names the command | Prints only. Does not price a send | Catalog-fit only | No spend | Reads the compare state file | ALREADY-FIXED |
| `./pfy build` cloud route and `./pfy build -p` | The route is the choice. Local is the other command | Not a past-result compare | Cloud model is the build route's model | Estimate, then yes. Off a TTY needs the flag. Local prints `$0` and does not ask | Not a model-choice row | ALREADY-FIXED |
| `./pfy build --local` | A cloud choice is refused. The committed local tag is kept | Local `$0`, no ask | `qwen3.6:35b`. If that default is missing from tags and `qwen2.5:14b` is listed, the run switches. `--model` and `PFY_LOCAL_BUILD_MODEL` do not switch. A down Ollama stays no-model | No paid call | User file, then the flag and env above it | MET |
| `catalog_fit_triage.py` triage, pending, replay | `resolve`, plus a `cloud:` model | Use `./pfy compare` for a past run | `qwen3.6:35b`, then `qwen2.5:14b` on a missing tag or a load error. An explicit model does not retry | Cloud prints the estimate and does not call until the yes rules above | User file. `PFY_MODEL_CATALOG_FIT` wins | MET |
| Catalog loop `pending` tick | Default stays local | Reminder only, at the end of the script | Same triage fallback | A saved cloud choice is not given `--yes`. Pending logs FitBroken for that slug and continues. Nothing is spent | User file still applies | PARKED |
| `make eval-suite` and `examples/eval-harness/run_scored_task.py` | Cloud choice refused. Stays Ollama. A public base names the local default at $0 | No labeled replay, so no compare | Pinned `qwen2.5:14b`. No fallback key | Local host (loopback, private, `host.docker.internal`, the default) sends with no ask. A public `OPENAI_BASE_URL` prints the estimate and does not send until the yes rules. A local-priced tag on that host is refused. The default host was not retargeted | User file applies, then the refusal | GAP |
| Matrix gate (`EVAL_MODE=matrix`) | Cloud choice refused | No compare. `EVAL_MODELS` stays the column list | Pinned `qwen2.5:14b`. No fallback | Same host gate as eval-suite | User file applies, then the refusal | GAP |
| `laya_shadow_model()` in `scripts/pfy_jev_230.py` | Cloud choice refused. Posts to local laya-serve | `./pfy compare decision-route` covers the trial file, not this process | Config says `qwen3.6:35b` with fallback `qwen2.5:14b`. This runner does not call `call_model` and does not retry a load error | No paid call on this path | User file, then `PFY_JEV_MODEL` | GAP |
| `typesafe_evaluate()` | Stderr names cloud TypeSafe and local CUA-S1-FORMS at $0 | No past-result compare. The cloud POST prints a TypeSafe price, then the yes rules | Not the qwen default. `typesafe_model()` is not model-choice | No POST to the cloud URL until a price row with provider TypeSafe exists and the yes rules pass. A local URL still posts. No price was invented. `PFY_MODEL_NO_PAID=1` blocks the socket | Not the model-choice file | MET |
| `scripts/egm_review.py` | `--local` is Ollama `qwen3.6:35b` at $0 and does not start grok. Omit `--local` for grok-4.7 | Not a past-result compare | `PFY_EGM_LOCAL_MODEL`, default `qwen3.6:35b`. Not a model-choice row | Grok ceiling unchanged. `--local` refuses a non-local `PFY_EGM_LOCAL_URL` and does not connect | Not a model-choice row | MET |
| `scripts/eval_lane.sh` | Grok via `model_lock.sh --always-approve`. No local choice | No | No model flag | No estimate | No | PARKED |
| `scripts/integrate_lane.sh` | Same grok launch | No | No model flag | No estimate | No | PARKED |
| `scripts/supersede_recheck_lane.sh` | Same grok launch | No | No model flag | No estimate | No | PARKED |
| `scripts/grill_ticket.py` `call_grok` | Grok. The lanes above call it | No | No | No estimate in this function | No | PARKED |
| `./pfy smoke` and `./pfy board` live eval | Local runtime prove | No | The live engine's model, not the qwen default | Local chat. Not a priced cloud call | No | ALREADY-FIXED |
| `./pfy hedge decide` | Picks local or cloud for a task class | No USD quote | Not the qwen default | Integer credits (`PFY_CLOUD_BUDGET`). It does not POST a model. The design keeps this ledger separate | Hedge state, not model-choice | ALREADY-FIXED |
| Price refresh inside the catalog loop | No | No | No | GET of the public price pages. No model POST | Stamp lives under the loop state dir | PARKED |

## Closed this pass

- `call_model` cloud path, and catalog-fit when it uses that path: estimate, then the yes rules. `run_compare` sets `paid_ok` so a compare does not prompt twice.
- `egm_review.py`: same yes rules, fake grok in tests, before any reviewer process.
- `build-lane` and `decision-route` fallback keys in `config/model-choice.json`. `pfy build --local` applies the fallback only for the default tag, against a fake tag list. `call_model` retries once when the committed default tag is missing. An explicit other tag does not switch. eval-suite and matrix stay on `qwen2.5:14b` with no fallback key.
- Off-TTY `./pfy setup` prints the set command. That hint is not covered by a test, because `cmd_setup` runs `make env-init`.

## Closed after the gap table

- `typesafe_evaluate` cloud URL: local CUA-S1-FORMS at $0, then no POST unless the price row provider is TypeSafe and the yes rules pass. The repo price table was not given a TypeSafe row.
- `examples/eval-harness/run_scored_task.py`: a public `OPENAI_BASE_URL` prints the estimate and does not send until `y` on a TTY, or the yes rules off a TTY. Local hosts do not ask.
- `scripts/egm_review.py --local`: Ollama at $0, no grok process. A non-local `PFY_EGM_LOCAL_URL` does not connect.

## Left open

- The operator screen compare button is catalog-fit against `grok-4.7` only. The CLI already accepts `gpt-6.1-sol` and `decision-route`. The screen was not changed: this pass had no browser check.
- eval-suite and matrix stay on `qwen2.5:14b`. The Makefile and `tests/test_model_choice_runners.py` pin that tag. Moving them to `qwen3.6:35b` is a separate change.
- `laya_shadow_model()` does not load through `call_model`, so the new fallback key does not rescue a missing laya tag.
- `run_suite.py` does not grow yes flags. A public base fails that cell closed. The failure text is the refusal, and the suite does not send. The single-task CLI is what accepts the estimate.

## Parked on purpose

`eval_lane.sh`, `integrate_lane.sh`, `supersede_recheck_lane.sh`, and `grill_ticket.py` call grok with `--always-approve` and no estimate. `scripts/catalog_loop.sh` launches those lanes, the catalog-fit pending tick, and the price refresh. A yes gate on a lane would stop an unattended tick unless the timer passed a flag. The timer was not edited. Giving the pending tick `--yes` would be the same kind of edit. A saved cloud catalog-fit therefore does not spend from the loop: the slug is logged and pending continues.

## Next

Default if nobody picks: leave the screen button on catalog-fit versus `grok-4.7`, and leave the lane scripts parked.

If the next change is chosen: teach the Loop and Engine compare control to offer `gpt-6.1-sol` and `decision-route`, then verify that confirm path in a browser. Second, teach `laya_shadow_model()` to retry `qwen2.5:14b` on a fake load error without pointing `typesafe_model()` at model-choice.
