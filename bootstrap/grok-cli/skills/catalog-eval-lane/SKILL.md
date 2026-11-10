---
name: catalog-eval-lane
description: Drive one catalog tool from I0 toward I2. The lane script writes the verdict files and applies them. The Build does not hand-edit the stage card.
---

# Catalog eval lane

Use this when a card needs an eval verdict. The driver is `scripts/eval_lane.sh`. Follow that script. Do not reimplement the land, the apply, or the card guard.

This driver is not `./pfy eval`. `./pfy eval` is the product structural gate (`make eval-integration-change`). It writes `pipelines/eval`. It does not call Grok and does not push `main`.

## Inputs

- `--slug <slug>`
- Optional `--date MMDD` (four digits). Default is UTC month and day.
- Optional `--root`, `--state`, and `--ticket`.
- Ticket file `tmp/TICKET-<slug>.md` in the lane worktree.
- Grok binary: `PFY_GROK_BIN`, default `grok`, wrapped by `scripts/model_lock.sh`.

## Outputs

- `eval/evals/<slug>/VERDICT.json` matching `docs/ops/VERDICT.schema.json`
- `eval/evals/<slug>/REPORT.md` is not public. Write it, traces, and raw logs under `tmp/ops/eval/evals/<slug>/`. `scripts/lane_ops_sync.py` copies them to `$PFY_OPS_ROOT` and commits them there, moves any committed record out, scrubs home paths and names from public outputs, and parks the lane if `scripts/check_public_paths.py` still fails.
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

## Security tools

When `PFY_LANE_SANDBOX=sandlock` is set (the loop sets it for a security scanner or guard), the ticket gains a Sandbox section: every install and tool run goes through `scripts/integrations/sandlock/wrap.py` with `PFY_SANDLOCK=all`. Record `"sandbox": "sandlock"` in VERDICT.json only when no run logged `sandlock: unsandboxed`. Write `eval/integrate/<slug>/sandbox-trial.json` with `scripts/integrations/sandlock/trial.py` so it carries the profile. I3 is decided by `data/promotion-rules.json` (security track: clean trial, read-only profile, advisory or deny-only wiring, main-run receipt, eval-structural green). Nobody signs off (see catalog-apply-and-ceiling).

A rule refusal writes only a `promotion_history` entry on the card. The lane commits that entry ("record the rule refusal") and lands it; any other card change after a refusal still parks.

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
scripts/eval_lane.sh --dry-run --slug <slug> --state DIR
```

`--dry-run` requires `--state` and prints one line, `skip-marker skip-fetch skip-grok skip-apply skip-push`, then exits before those steps. It does not walk apply. It does not take the model lock. The default path still fast-forwards `main`.

The Build writes the verdict and the report. It does not hand-edit `integration_stage` or `tier_ceiling`.

The driver prompt names all five catalog skills: `catalog-intake-dedupe`, `catalog-eval-lane`, `catalog-integrate-lane`, `catalog-apply-and-ceiling`, and `catalog-loop-operator`. Read each `bootstrap/grok-cli/skills/<name>/SKILL.md`. Grok is wrapped in `scripts/model_lock.sh`.
