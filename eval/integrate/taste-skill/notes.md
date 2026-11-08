# taste-skill integrate notes

`eval/integrate/taste-skill/run-on-main.sh` runs the pinned cache `lint.mjs` in app mode on `gui/operator/frontend/index.html`. It writes one receipt only when HEAD is an ancestor of `origin/main` and the lint exits 0 or 1. A missing binary, exit 2, or a timeout writes nothing. Callers that do not run the script stay as they are. This commit does not add `receipt.json`. The driver writes that file after the wiring commit is an ancestor of `origin/main`.

Stage apply stopped. `data/stages/taste-skill.json` has `tier_ceiling` I1, so the card was not edited.

`scripts/catalog_apply_verdict.py --card data/stages/taste-skill.json --verdict eval/integrate/taste-skill/VERDICT.json` refused: `above-ceiling: proposed I3 is above allowed I1 (evidence I2: entry, pin, record, report, VERDICT, probe artifact; tier_ceiling I1 caps the evidence)`.

`apply_stage` to I3 returned `tier_ceiling` and left the card bytes unchanged (`218c1b7a2f1c84eb2d88c45229a59c606f3f9b4e1e11ef37da76b29085c281ce`). Do not demote. Proposed I3 stays in `VERDICT.json` beside the lane.
