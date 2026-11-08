# bumblebee integrate notes

`scripts/catalog_apply_verdict.py` refused proposed I3. The card bytes stayed the same.

```
refused: above-ceiling: proposed I3 is above allowed I1 (evidence I1: notes, pin, report, VERDICT, script; tier_ceiling I1 agrees)
```

`data/stages/bumblebee.json` stays I2. `tier_ceiling` stays I1. No `receipt:` evidence line was added. The lane stops there. It does not demote the card.

The 2026-11-08 run on `6f5591a50fb09f80876299af97d9d5f98d9ff9b5` wrote `eval/integrate/bumblebee/receipt.json`. `scripts/pfy_mcp_scan.py` returned `CLEAN` with 0 findings on `tmp/bumblebee-fixture`. Tool version `bumblebee v0.1.2`. Apply was run again after that receipt and refused with the same above-ceiling line. The ceiling stays I1.

`eval/integrate/bumblebee/run-on-main.sh` writes `eval/integrate/bumblebee/receipt.json` only after this commit is an ancestor of `origin/main` and `scripts/pfy_mcp_scan.py` finishes clean on `tmp/bumblebee-fixture`. A missing binary, a scan error, or a timeout writes nothing. This worktree does not push.
