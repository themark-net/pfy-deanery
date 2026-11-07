# Handoff: stages split 1107

Branch `bot/stages-split-1107`. Not pushed. Not a Feature GO.

## Done

Integration stage cards moved off `data/tool_integration_stages.json` onto one file per tool, `data/stages/<slug>.json`. Shared fields are `data/stages/_registry.json`. `last_updated` is not stored. `pfylib.stage_registry.load_stages` computes it from a per-tool date field or from `git log`.

Readers and writers use that loader: `scripts/catalog_check.py`, `scripts/catalog_stage_eval.py`, `scripts/pfy_catalog_ask_queue_209.py`, `scripts/pfy_ix_198.py`, `scripts/pfy_live_org_queue_214.py`, and the stage tests. `catalog_check` rejects a returned monolith and checks each card (JSON, name, slug, stage I0-I4). `make stages-json` prints the assembled document.

Layout and how to add a tool: `docs/ops/integration-stages.md` (Stage files). `docs/ops/MODULAR-CI.md` was not in this worktree, so that section is the modular-CI note for this lane.

## Checks

`python3 -m unittest` on the stage modules (18 tests) passed. `python3 scripts/catalog_check.py` passed (53 stage cards). `python3 scripts/pfy_catalog_ask_queue_209.py --selftest` passed. `python3 scripts/pfy_ix_198.py` passed. `python3 examples/eval-harness/run_structural.py` passed (1639 tests, 18 skipped). `pfy_live_org_queue_214.py --selftest` still fails on two pre-existing GUI strings (`id=loop-queue`, `queue      `) that this lane did not touch.

## Next

None for this lane. Do not recreate the monolith.
