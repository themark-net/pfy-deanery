---
name: catalog-eval-lane
description: Drive one catalog tool from I0 toward I2. The lane script writes the verdict files and applies them. The Build does not hand-edit the stage card.
---

# Catalog eval lane

Use this when a card needs an eval verdict. The driver is `scripts/eval_lane.sh`. Follow that script. Do not reimplement the land, the apply, or the card guard.

## Inputs

- `--slug <slug>`
- Optional `--date MMDD` (four digits). Default is UTC month and day.
- Optional `--root`, `--state`, and `--ticket`.
- Ticket file `tmp/TICKET-<slug>.md` in the lane worktree.
- Grok binary: `PFY_GROK_BIN`, default `grok`, wrapped by `scripts/model_lock.sh`.

## Outputs

- `eval/evals/<slug>/VERDICT.json` matching `docs/ops/VERDICT.schema.json`
- `eval/evals/<slug>/REPORT.md`
- The driver, not the Build, runs `scripts/catalog_apply_verdict.py` before land.
- A missing card is created at I0 by `pfylib.stage_registry.write_tool`.

## Markers

Under the eval state dir (`--state`, or `$PFY_LOOP_STATE/eval`):

- `<slug>.dispatched` created with noclobber before work
- `<slug>.parked` on failure
- `<slug>.done` and `LANDED_<slug>` after a fast-forward land
- `progress.md` with a line `skill=catalog-eval-lane sha=<git hash-object of this file>`

Worktree: `<state>/wt/<slug>`. Branch: `bot/eval-<slug>-<date>`.

## Duplicate-run guard

The noclobber `.dispatched` file is the guard. A second start exits 2 when `PFY_LANE_FROM_LOOP` is not `1`. When the catalog loop already created the marker, it sets `PFY_LANE_FROM_LOOP=1` and the lane continues. Do not add another lock.

## Stop rules

- `STOP` under the loop state dir, the repo `tmp/STOP`, the state dir, or the worktree `tmp/STOP`: park and exit 0.
- Grok implement or review fails three times: park.
- Dirty worktree after Grok: park.
- Missing verdict: park.
- Apply refusal that changes card bytes: park. A refusal that leaves the card bytes unchanged is recorded and is not a hand edit.
- Do not push with force. Do not open a pull request.

## Card guard

`scripts/catalog_card_guard.py` compares to current `origin/main` after the rebase, using `git diff origin/main...HEAD`. It may revert only this lane's own disallowed edits to `tier_ceiling`, `integration_stage`, and `ceiling_history`. It must not rewrite a card this lane did not change. Never restore those fields from the lane's base snapshot.

## Commands

```bash
scripts/eval_lane.sh --slug <slug> [--date MMDD]
```

The Build writes the verdict and the report. It does not hand-edit `integration_stage` or `tier_ceiling`.
