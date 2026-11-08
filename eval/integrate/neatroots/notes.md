# neatroots integrate notes

Offline check: `eval/integrate/neatroots/run-on-main.sh` reads `eval/integrate/neatroots/fixtures/trace.json` and runs `neatroots check`. No network and no shared service. Callers that do not run the script stay as they are. This commit does not add `receipt.json`. The driver writes that file after the wiring commit is an ancestor of `origin/main`.

Stage apply stopped. `data/stages/neatroots.json` has `tier_ceiling` I2, so the card was not edited.

`scripts/catalog_apply_verdict.py --card data/stages/neatroots.json --verdict eval/integrate/neatroots/VERDICT.json` refused: `malformed-verdict: threshold must be a number`.

The same proposed stage with numeric threshold 0 refused: `above-ceiling: proposed I3 is above allowed I2 (evidence I2: entry, report, VERDICT, probe artifact; tier_ceiling I2 agrees)`.

`apply_stage` to I3 returned `tier_ceiling` and left the card bytes unchanged (`fcc8421aaa1f2f0dc7ef8721ff706e98229b0c55d0df0750dbfef552139bcbc4`). Do not demote. Proposed I3 stays in `VERDICT.json` beside the lane.
