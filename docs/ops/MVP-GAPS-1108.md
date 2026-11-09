# MVP gaps 1108

Lane `mvp-gaps-1108`. Walk on 2026-11-08 from a shallow clone of `origin/main` at `02ad875edaebc285baaff0f6be0084afaf681f69` under `tmp/mvp-gaps-1108/tmp/fresh-clone`. No GPU, no model pull, no live catalog loop. Model calls were a stub `grok` against a local bare, or skipped. LIVE_HARD_OFF stays. Catalog HOLD 70-75 stays. Not a Feature GO.

The product surface `./pfy` does onboard, stage, and ship. The catalog lifecycle is five skills and their scripts: `catalog-intake-dedupe`, `catalog-eval-lane`, `catalog-integrate-lane`, `catalog-apply-and-ceiling`, `catalog-loop-operator`.

## Closed in this pass

- Browse joins a parenthetical TOOLS.md name to the stage card. `adr-tools (optional)` showed a blank stage because the slug was `adr-tools-optional` and the card is `adr-tools`. The bold name is an alias, not a second row.
- Browse shows the stage card when `data/tools.json` lags. `codebase-memory-mcp` was I2 in the json file and I3 on the card. The json file is still I2. Browse now shows I3. Do not hand-edit `integration_stage`.
- `scripts/test_select.py` treats `VERDICT.json` and `receipt.json` as one file per tool. A test that names the full path still runs. A new artifact that nobody names stays structural and does not force the full suite. Before this, a stub eval of `gum` selected 22 modules (`tmp/mvp-gaps-1108/tmp/sandbox-eval/evalstate/gum-select.json`) and parked with `run_tests failed`.
- Integrate dispatch checks that the card is I2, the slug is not excluded, and no park file exists before it writes `tmp/integrate/<slug>.dispatched`. Closed in `0dee24d93ba1ac865fc876ef6dd4bc66313f0224`.
- Supersede candidacy compares coverage levels on the four suite parts (track, catalog, evaluate, integrate). Integrate is the local-first part. A part counts only at partial or full. none does not count. A bare part-name list exits 2. recheck_days and the watchlist shape are unchanged. Closed in `1cd339ed0093f9a76dfa00c32da8c401565ba34b`.
- Intake `--write-card` records evidence from the source: the repo URL, a license when a local tree states one, a pin SHA when the source or a local git HEAD has one, and one README claim. No network. `integration_stage` stays I0. `tier_ceiling` is I1 when that list is non-empty, so `catalog_apply_verdict.py` can allow I1. A bare name stays `evidence: []` and `tier_ceiling: I0`. Apply does not invent evidence. Empty source, duplicate, and `./pfy catalog nosuch` are unchanged. Closed in `d0312047a1150aa7b0d78be4fa36631bc7fa1673`.
- Browse lists a stage card that is not an Active Catalog row. Intake still does not write `TOOLS.md`, `data/tools.json`, or `sources/`. Documented rows keep their table name, category, and github. The card's `integration_stage` is shown and not written. An I0 card stays incomplete, so ask still SKIPs. Auto-Company (other heading) and LiveKit (no table row) are listed. A stage file that is not valid JSON hides card stages until that file is removed; the table names stay. Empty source, duplicate, and `./pfy catalog nosuch` are unchanged. Closed in `cdf64e46b1890699fd627bf0e0820363fcbad4dc`.
- README "Using the catalog" names the five commands. `./pfy help` says `pfy eval` is the product structural gate and names `scripts/eval_lane.sh` and `scripts/catalog_intake_dedupe.py`. The command name `pfy eval` is unchanged.
- `./pfy eval` stays the product structural gate (`make eval-integration-change`). It writes `pipelines/eval`. It does not call Grok and does not push `main`. Catalog verdicts stay `scripts/eval_lane.sh` (Grok, then a fast-forward of `main`). Help, the operator docs, the eval-lane skill, and `tests/test_cli.py` say that. One test runs `./pfy eval` with a stub `make` and checks the receipt was not written. The command was not renamed. Closed in `ed9616cc4338cdfb6b404ad004fa4835518c3ca6`.

While this walk was open, `origin/main` also landed `cec3b3de` (excluded slugs refused before a ceiling check; lane test selection is `origin/main...HEAD`; taste-skill, repowise, and opencode-mem tests expect the I3 cap the loop already wrote) and `5683af53` (I1 static eval for LocalHarness and Cartographer, value gate fail, both stay I1). This lane did not re-raise ATG. `atomic-task-graph-atg` stays on `eval/catalog-queue/exclusions.tsv`.

## Still open, highest impact first

Item 1 (intake evidence, a new card cannot leave I0) is closed. See Closed in this pass.

Item 2 (a new stage card is invisible in `./pfy catalog`) is closed. See Closed in this pass.

Item 3 (`./pfy eval` versus `scripts/eval_lane.sh`) is closed. See Closed in this pass. The command name is unchanged.

The supersede parts-count finding is closed. See Closed in this pass. Closed in `1cd339ed0093f9a76dfa00c32da8c401565ba34b`.

### 4. Eval: the lane has no dry run and it fast-forwards main

`scripts/eval_lane.sh` fetches `origin`, cuts a worktree from `origin/main`, calls Grok through `scripts/model_lock.sh`, selects tests, applies, and pushes `refs/heads/main`. Tests must pass `--root` and `--state`. A walk must set `PFY_GROK_BIN` to a stub and `PFY_MODEL_LOCK` to a private file. This walk did that. It did not take `~/.cache/pfy/locks/local-model.lock`. The destructive-command guard stayed on. A missing guard binary falls open.

The stub lane against a local bare (not GitHub) reached `test_select mode=affected modules=22` and parked `run_tests failed`. Origin was not updated. The selector fix above is the small part. `--dry-run --state DIR` now exits before the dispatch marker, Grok, and the push. It does not walk apply. The default path still fast-forwards `main`. Do not point a real lane at GitHub from a test.

`./pfy eval` (the product gate) was not run in the walk. It writes under `pipelines/eval` and is a different command. Help and `tests/test_cli.py` lock that split. Closed in `ed9616cc4338cdfb6b404ad004fa4835518c3ca6`.

### 5. Integrate: I2 guard closed, and the driver still pushes

The new gum card stayed I0, so integrate was not the next user step. `scripts/integrate_lane.sh` was not executed against a real origin. Closed in `0dee24d93ba1ac865fc876ef6dd4bc66313f0224`: the driver reads the stage card, `eval/catalog-queue/exclusions.tsv`, and park files before `tmp/integrate/<slug>.dispatched`. A card that is not I2, an excluded slug, or an existing `<slug>.parked` file exits before that marker. When `PFY_LOOP_STATE` is set, `$PFY_LOOP_STATE/integrate/<slug>.parked` counts. A refusal writes nothing and deletes nothing. A second start still exits 2. `--dry-run` still exits before the check, the marker, Grok, and the push. The default path still calls Grok and fast-forwards `main`.

`python3 scripts/integrate_intake.py` at the walk commit listed eight I2 cards already at ceiling I3, with no flag: headson, hiroute, neatroots, opencode-mem, repowise, sponsio, strata, taste-skill. bumblebee was flagged `tier_ceiling below I3: needs Mark`. This lane did not launch any of them. Do not launch them from a gap pass. Parked loop slugs stay parked. Do not start `catalog-loop.timer`. Do not remove another unit's markers.

### 6. Track: no product ticket

This lane's tracker is the lane ticket plus this file and the link in `docs/TODO.md`. No GitHub issue was filed. Trading, release, deploy, and secrets were not touched.

## What the walk ran

| Step | Result |
|------|--------|
| `./pfy doctor --json` | exit 0 |
| `./pfy catalog` | 54 tools, state dir under the lane tmp |
| `./pfy catalog status` | 0 queued |
| intake litellm | `duplicate litellm data/stages/litellm.json` |
| intake gum, then `--write-card` | `new gum`, I0 card, then removed from the clone |
| `catalog_check.py` | PASS before and after the gum card |
| supersede `--parts track,catalog` and with evaluate,integrate | `supersede_candidate` true both times |
| apply on the new card | refused, card not promoted |
| auto-raise dry run | `skip gum gates` |
| eval lane, local bare, stub grok | parked `run_tests failed` before the selector fix |
| integrate lane | not run |
| `./pfy ship` | not run (needs `PRODUCT_REMOTE`) |

## Do not do next

- Do not hand-edit `integration_stage` or `tier_ceiling`.
- Do not weaken the ceiling tests so a raise they forbid would pass.
- Do not re-raise ATG.
- Do not start the catalog loop or take its lock.
- Do not demote a card the loop already raised.
