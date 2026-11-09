# MVP gaps 1108

Lane `mvp-gaps-1108`. Walk on 2026-11-08 from a shallow clone of `origin/main` at `02ad875edaebc285baaff0f6be0084afaf681f69` under `tmp/mvp-gaps-1108/tmp/fresh-clone`. No GPU, no model pull, no live catalog loop. Model calls were a stub `grok` against a local bare, or skipped. LIVE_HARD_OFF stays. Catalog HOLD 70-75 stays. Not a Feature GO.

The product surface `./pfy` does onboard, stage, and ship. The catalog lifecycle is five skills and their scripts: `catalog-intake-dedupe`, `catalog-eval-lane`, `catalog-integrate-lane`, `catalog-apply-and-ceiling`, `catalog-loop-operator`.

## Closed in this pass

- Browse joins a parenthetical TOOLS.md name to the stage card. `adr-tools (optional)` showed a blank stage because the slug was `adr-tools-optional` and the card is `adr-tools`. The bold name is an alias, not a second row.
- Browse shows the stage card when `data/tools.json` lags. `codebase-memory-mcp` was I2 in the json file and I3 on the card. The json file is still I2. Browse now shows I3. Do not hand-edit `integration_stage`.
- `scripts/test_select.py` treats `VERDICT.json` and `receipt.json` as one file per tool. A test that names the full path still runs. A new artifact that nobody names stays structural and does not force the full suite. Before this, a stub eval of `gum` selected 22 modules (`tmp/mvp-gaps-1108/tmp/sandbox-eval/evalstate/gum-select.json`) and parked with `run_tests failed`.
- README "Using the catalog" names the five commands. `./pfy help` says `pfy eval` is the product structural gate and names `scripts/eval_lane.sh` and `scripts/catalog_intake_dedupe.py`. The command name `pfy eval` is unchanged.

While this walk was open, `origin/main` also landed `cec3b3de` (excluded slugs refused before a ceiling check; lane test selection is `origin/main...HEAD`; taste-skill, repowise, and opencode-mem tests expect the I3 cap the loop already wrote) and `5683af53` (I1 static eval for LocalHarness and Cartographer, value gate fail, both stay I1). This lane did not re-raise ATG. `atomic-task-graph-atg` stays on `eval/catalog-queue/exclusions.tsv`.

## Still open, highest impact first

### 1. Promote: a new card cannot leave I0 in one pass

Intake writes `evidence: []` and `tier_ceiling: I0` (`scripts/catalog_intake_dedupe.py` `_i0_card`). On the fresh clone, apply of a proposed I1 verdict printed `refused: above-ceiling: proposed I1 is above allowed I0 (evidence I0: no evidence listed; tier_ceiling I0 agrees)`. `catalog_auto_raise.py --slug gum` printed `skip gum gates` because no `eval/**/gum/VERDICT.json` was in the tree.

The ceiling rule in `scripts/catalog_apply_verdict.py` ranks an empty list at I0, a `verdict.json` path at I1, and `make:` / `path:` / `probe:` / a receipt file name at I2. A valid main-run receipt lifts evidence to I3 (I4 with `submodule:` or `subtree:`). A higher `tier_ceiling` does not raise evidence. Auto-raise writes `tier_ceiling` only, and only when both gates pass and `risk_class` is none. It never demotes. `scripts/eval_lane.sh` applies the verdict and does not call auto-raise, and it does not append an evidence string.

Nothing in the documented user path writes that evidence string. A user who follows the README table still cannot promote a brand-new card. Do not teach apply to invent evidence. `tests/test_eval_lane.py` expects an I1 proposal on an empty-evidence I0 card to be refused and still land.

I3 still needs a receipt from a run on main (`docs/ops/INTEGRATE.md`). This lane did not invent one.

### 2. Catalog: a new card is invisible in `./pfy catalog`

At `02ad875`, `./pfy catalog` printed `PASS catalog · 54 tools`. `catalog_check.py` printed `tools_md=55 stage_cards=55 stage_only=74`. After `--write-card` for `https://github.com/charmbracelet/gum`, check still passed and `stage_only=75`, including gum. Browse still did not list gum. The parser keeps the Active Catalog table and drops stage-only cards. Auto-Company sits under another heading, so browse never sees that row either.

Intake does not triple-write. It does not touch `TOOLS.md`, `data/tools.json`, or `sources/`. `/catalog-docs` is a separate step. A new user who catalogs a tool and then runs `./pfy catalog` will not see it.

`python3 scripts/catalog_intake_dedupe.py` on litellm printed `duplicate litellm data/stages/litellm.json`. An empty source prints `empty slug` and exits 1. `./pfy catalog nosuch` exits 2. Those are by design.

### 3. Find: `./pfy eval` is still the product gate

`./pfy help` now says that line is the product structural gate, and it names `scripts/eval_lane.sh` and `scripts/catalog_intake_dedupe.py`. Renaming `./pfy eval` is not a small fix. The command still runs `make eval-integration-change`.

`python3 scripts/supersede_check.py --parts track,catalog,evaluate,integrate` printed `supersede_candidate: true`. The check counts parts. It does not read the source. Two or more parts are enough. A one-part list is not a candidate.

### 4. Eval: the lane has no dry run and it fast-forwards main

`scripts/eval_lane.sh` fetches `origin`, cuts a worktree from `origin/main`, calls Grok through `scripts/model_lock.sh`, selects tests, applies, and pushes `refs/heads/main`. Tests must pass `--root` and `--state`. A walk must set `PFY_GROK_BIN` to a stub and `PFY_MODEL_LOCK` to a private file. This walk did that. It did not take `~/.cache/pfy/locks/local-model.lock`. The destructive-command guard stayed on. A missing guard binary falls open.

The stub lane against a local bare (not GitHub) reached `test_select mode=affected modules=22` and parked `run_tests failed`. Origin was not updated. The selector fix above is the small part. `--dry-run --state DIR` now exits before the dispatch marker, Grok, and the push. It does not walk apply. The default path still fast-forwards `main`. Do not point a real lane at GitHub from a test.

`./pfy eval` (the product gate) was not run. It writes under `pipelines/eval` and is a different command.

### 5. Integrate: not walked, and the driver will push

The new gum card stayed I0, so integrate was not the next user step. `scripts/integrate_lane.sh` was not executed, not even against the local bare. The script creates `tmp/integrate/<slug>.dispatched` with noclobber before fetch, and it does not check that the card is I2 before that marker. A second start exits 2. It calls Grok and fast-forwards `main`. There is no dry run.

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
