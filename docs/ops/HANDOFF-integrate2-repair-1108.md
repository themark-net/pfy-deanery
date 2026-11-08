# Integrate2 repair, 2026-11-08

Product fix: `3c21028610674ac6e4f65dc8d7c5fd2c9ef802d4` (`F5: ceiling does not promote a stage card`).

## Eval-structural

Run 42511737320 on `428c6fae` failed G0 self-hosted nimo and ubuntu shard 1. Both failures were `tests.test_catalog_stage_eval.CatalogStageEvalTests.test_posture_and_ceiling_are_not_promotions`. Line 49 expected `codebase-memory-mcp` `integration_stage` `I2`. The card was `I3`. `985aedc0` passed because the card was still `I2`.

Root cause: the test pinned the live stage. The I3 value is the main-run receipt promotion, not `evaluations()` copying `tier_ceiling` onto the stage. Replacing the literal with `I3` would stay green if that copy were added later.

Fix: the live card is only checked against itself. A temp catalog sets the same card to stage `I2` with ceiling `I3`. `evaluations()` and `--apply` must leave the stage at `I2`. The real stage files are compared before and after.

Verification: `python3 -m unittest tests.test_catalog_stage_eval` OK (4 tests). `python3 scripts/catalog_check.py` PASS. `python3 scripts/grill_ticket.py tmp/TICKET.md --paths tests/test_catalog_stage_eval.py` printed `no grill needed`. This change does not touch a workflow, a gate script, or `pipelines/`. No new pipeline step, so the software-factory five questions are not a new gate. `eval-structural` still runs this test.

## Card guard

`scripts/integrate_lane.sh` fetches before the worktree and again inside `land()` before rebase. It does not snapshot stage cards and does not rewrite another lane's stage. That defect is not in the script. No change there.

The integrate2 driver under `tmp/integrate2/` did rewrite cards before rebase. A stale lane then tried to commit `F5: <slug> restore ceilings and stages`. dcg rule `core.git:restore-worktree` denied it because the word `restore` is in the command. The three lanes parked. dcg stays on. The driver now rebases onto current `origin/main` before the enforcing guard, and the commit text does not contain `restore`. A card this lane did not change is left for rebase, so another lane's promotion is not copied onto the stale branch and is not put back to an old stage after rebase. Regression: `tmp/integrate2/test_guard_cards.py` and `tmp/integrate2/test_lane_rebase.sh`.
