---
name: catalog-integrate-lane
description: Drive one I2 card to I3 with a receipt from a run on main. The integrate script applies the verdict. The Build does not hand-edit the stage card.
---

# Catalog integrate lane

Use this for an I2 card whose ceiling is already I3 or I4 and which has no receipt yet. The driver is `scripts/integrate_lane.sh`. The operator doc is `docs/ops/INTEGRATE.md`. Follow those. Do not reimplement the land or the card guard.

## Inputs

- `--slug <slug>`
- Optional `--date MMDD`. Default is UTC month and day.
- Optional `--root` and `--ticket`.
- Ticket: `tmp/TICKET-<slug>.md`, or `docs/ops/integrate/tickets/<slug>.md` when the tmp file is absent.
- The catalog loop writes the ticket from `docs/ops/integrate/TEMPLATE.md` plus the card fields.

## Outputs

- Wiring committed on a fast-forward of the worktree SHA to `origin/main`.
- A receipt at `eval/integrate/<slug>/receipt.json` from a run on main.
- The driver runs `scripts/catalog_apply_verdict.py`. A refusal is recorded. The card is not hand-edited.
- This lane does not raise `tier_ceiling` and does not demote `integration_stage`.

## Markers

Under `<root>/tmp/integrate/`:

- `<slug>.dispatched` with noclobber. Content starts as `pid`. A second start exits 2 before git or Grok.
- `<slug>.parked`, `<slug>.done`, `LANDED_<slug>`
- `progress.md` with `skill=catalog-integrate-lane sha=<git hash-object of this file>`

Worktree: `tmp/integrate/wt/<slug>`. Branch: `bot/integrate-<slug>-<date>`.

The loop's own marker is `$PFY_LOOP_STATE/integrate/<slug>.dispatched`. That file is not this lane's marker. Do not treat them as the same path.

## Duplicate-run guard

Noclobber on `tmp/integrate/<slug>.dispatched` is the guard. Exit 2 on a second start. Do not add a second scheduler.

## Stop rules

- `<root>/tmp/STOP` before git: park and exit 0.
- `STOP` during implement or review, in the repo tmp or the worktree tmp: park before push.
- Grok fails three times, or the worktree is dirty after Grok: park.
- Apply refusal: record it and do not hand-edit the card.
- Do not force-push. Do not open a pull request.

## Card guard

Any restore of `tier_ceiling` or `integration_stage` compares to current `origin/main` after the rebase. The diff is `git diff origin/main...HEAD`. Revert only this lane's own disallowed edits. Never rewrite a card this lane did not change. Never restore from the lane's base snapshot. On a rebase conflict in `scripts/integrate_lane.sh`, keep main's guard and re-apply only the skill prompt.

## Commands

```bash
scripts/integrate_lane.sh --slug <slug> [--date MMDD] [--ticket FILE]
```
