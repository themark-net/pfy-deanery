---
name: catalog-loop-operator
description: Operate the catalog loop. Read loop.latest.json, stop with STOP or QUOTA_STOP, and retry a parked lane only after reading the parked reason.
---

# Catalog loop operator

Use this to run or stop one catalog tick, to read the status snapshot, or to retry a parked lane. The tick is `scripts/catalog_loop.sh`. Do not reimplement the queue walk, the caps, or the lock.

A Build lane does not install systemd units and does not start the real loop. The operator does that after the units land. Install steps are in `docs/ops/HANDOFF-catalog-loop-1108.md`.

## Inputs

- State dir: `$PFY_LOOP_STATE`. When unset, the script uses `$HOME/DEVELOP/pfy-mentat/tmp/loop`.
- Worktree: `$PFY_LOOP_WT`. Repo: `$PFY_LOOP_REPO`.
- Integrate markers also live under `$PFY_INTEGRATE_ROOT` and `$PFY_INTEGRATE2_ROOT`.
- Eval markers from the old queue also live under `$PFY_EVQ_ROOT`.
- `PFY_LOOP_NO_PUSH=1` and `--dry-run` push nothing. `--dry-run` does not launch. `PFY_LOOP_NO_PUSH=1` still launches.

## Outputs

- Generated catalog files, committed by author `catalog-loop` only when bytes changed, then a fast-forward push. Same three rebase retries as the counts publisher. Stray paths exit 3.
- Status source: `$PFY_LOOP_STATE/loop.latest.json`.
- Repo copy `pipelines/catalog/loop.latest.json` is gitignored. Do not commit it.
- Times are objects `{"utc","pt"}`. `cap` is `{"running":4,"daily":20}`.
- `status` is `ok`, `stopped`, `busy`, `quota`, or `error`.
- `ok` when the running cap is the only reason slots are 0. `quota` when the daily cap blocks launches.

## needs-mark.tsv

Path: `eval/catalog-queue/needs-mark.tsv`.

Columns: `slug`, `kind`, `reason`, `evidence`, `since`.

`kind` is one of: `ceiling`, `gpu`, `pull-over-25gb`, `excluded`, `demotion-flag`, `parked`, `risky-class`.

The loop skips every slug in that file. Do not launch them by hand from the loop.

## Markers

Taken, so the tick will not launch the slug:

- `.dispatched`, live `.pid`, `LANDED_<slug>`, `.done`, `.parked`
- Look in `$PFY_LOOP_STATE/eval`, `$PFY_LOOP_STATE/integrate`, `$PFY_INTEGRATE_ROOT`, `$PFY_INTEGRATE2_ROOT` for integrate, and `$PFY_EVQ_ROOT` for eval.

`integrate2` is another worker. Read its marker files only. Do not edit that directory and do not signal its processes. A live pid there counts toward the 4 running lanes.

## Duplicate-run guard

`flock -n` on `$PFY_LOOP_STATE/loop.lock`. A busy lock exits 0 with status `busy` and does not launch. Noclobber `.dispatched` plus the taken markers are the other guards. Do not add a global CI lock or a second scheduler.

## Stop rules

- `$PFY_LOOP_STATE/STOP` or `$PFY_LOOP_STATE/QUOTA_STOP`: the tick exits 0, status `stopped`, and launches nothing.
- Do not remove a human `QUOTA_STOP`.
- Daily cap 20 writes `QUOTA_STOP.auto` and stops launches. A later tick on a new America/Los_Angeles day removes `QUOTA_STOP.auto` when the day's counter is under 20. It does not remove a human `QUOTA_STOP`.
- On error: status `error`, nonzero exit, no further launches.
- Budget: at most 20 starts per PT calendar day and at most 4 lanes at once. The counter is `started-YYYYMMDD`.
- GPU, pulls over 25 GB, trading, release, deploy, and secrets are never launched.
- Hang check: `$PFY_LOOP_STATE/tails.json`. A repeated identical log tail sets `hang_same_tail` on that running row, with `pid_age_s`.

## Retry

1. Read `<dir>/<slug>.parked` and keep the reason.
2. After that read, remove `<dir>/<slug>.dispatched`.
3. A leftover `.parked` still counts as taken. Remove `.parked` in the same step only after the reason is read and the retry is intended.
4. Do not remove `LANDED_<slug>` or `.done` when the lane already landed.
5. A tick that fails in `systemd-run` writes `.dispatched` and no `.parked`. Read `errors` in `loop.latest.json`, then remove that `.dispatched` to retry.

## Counts timer

The loop regenerates counts. `ops/systemd/catalog-counts.service` and `catalog-counts.timer` stay on disk. Retire the timer with:

```bash
systemctl --user disable --now catalog-counts.timer
```

Do not delete those unit files.

## Commands

```bash
scripts/catalog_loop.sh --dry-run
PFY_LOOP_NO_PUSH=1 scripts/catalog_loop.sh
scripts/catalog_loop.sh
```

The five software-factory questions for this pipeline are answered in `docs/ops/HANDOFF-catalog-loop-1108.md`.
