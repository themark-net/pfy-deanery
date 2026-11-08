# bumblebee integrate notes

`scripts/catalog_apply_verdict.py` refused proposed I3. The card bytes stayed the same.

```
refused: above-ceiling: proposed I3 is above allowed I1 (evidence I1: notes, pin, report, VERDICT, script; tier_ceiling I1 agrees)
```

`data/stages/bumblebee.json` stays I2. `tier_ceiling` stays I1. No `receipt:` evidence line was added. The lane stops there. It does not demote the card.

`eval/integrate/bumblebee/run-on-main.sh` writes `eval/integrate/bumblebee/receipt.json` only after this commit is an ancestor of `origin/main` and `scripts/pfy_mcp_scan.py` finishes clean on `tmp/bumblebee-fixture`. A missing binary, a scan error, or a timeout writes nothing. This worktree does not push.
