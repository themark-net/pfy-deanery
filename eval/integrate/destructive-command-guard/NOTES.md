# destructive-command-guard integrate notes

Probe and pin stay in `eval/evq1107/destructive-command-guard/`. The binary is the cache file `~/.cache/pfy/tools/destructive-command-guard/unpack/dcg` (v0.16.0, commit `665fcd8fc62cb5941e0484ddab012419f146523d`). It is not vendored.

The lane calls `scripts/integrations/dcg/guard.sh` before git and grok. The wrapper does not execute argv. Exit 126 denies. `PFY_DCG_DISABLE=1` is the only opt-out. This lane did not re-run the 12 destructive commands. The probe did.

`run-on-main.sh` writes a receipt only when `HEAD` is an ancestor of `origin/main`. This worktree does not push, so it does not leave `receipt.json` on main. `tier_ceiling` is I1. `catalog_apply_verdict.py` refuses I3. The card is unchanged.
