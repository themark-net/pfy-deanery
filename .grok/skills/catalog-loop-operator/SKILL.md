---
name: catalog-loop-operator
description: Operate the catalog loop. Read loop.latest.json, stop with STOP or QUOTA_STOP, and retry a parked lane only after reading the parked reason.
---

# Catalog loop operator

Use this to run or stop one catalog tick, to read the status snapshot, or to retry a parked lane. The tick is `scripts/catalog_loop.sh`. Do not reimplement the queue walk, the caps, or the lock.

A Build lane does not install systemd units and does not start the real loop. The operator does that after the units land. Install steps are in `ops/systemd/` (the unit files and their comments). Set `PFY_OPS_ROOT` for the loop unit, as `ops/systemd/catalog-loop.service` does.

## Inputs

- State dir: `$PFY_LOOP_STATE`. When unset, the script uses `$HOME/DEVELOP/pfy-mentat/tmp/loop`.
- Worktree: `$PFY_LOOP_WT`. Repo: `$PFY_LOOP_REPO`.
- Integrate markers also live under `$PFY_INTEGRATE_ROOT` and `$PFY_INTEGRATE2_ROOT`.
- Eval markers from the old queue also live under `$PFY_EVQ_ROOT`.
- `PFY_LOOP_NO_PUSH=1` and `--dry-run` push nothing. `--dry-run` does not launch. `PFY_LOOP_NO_PUSH=1` still launches.
- `PFY_CATALOG_STATE_DIR`, when set, is the state dir instead of `$PFY_LOOP_STATE`.
- `PFY_CATALOG_OFFLINE=1` skips fetch, regeneration writes, and push. Production leaves it unset.

## Outputs

- Generated catalog files, committed by author `catalog-loop` only when bytes changed, then a fast-forward push. Same three rebase retries as the counts publisher. Stray paths exit 3.
- Status source: `$PFY_LOOP_STATE/loop.latest.json`.
- Repo copy `pipelines/catalog/loop.latest.json` is gitignored. Do not commit it.
- Times are objects `{"utc","pt"}`. `cap` is `{"running":4,"daily":20}`.
- `status` is `ok`, `stopped`, `busy`, `quota`, or `error`.
- `ok` when the running cap is the only reason slots are 0. `quota` when the daily cap blocks launches.

## needs-mark.tsv

Path: `$PFY_OPS_ROOT/eval/catalog-queue/needs-mark.tsv`, in the private ops checkout. It is operator state and never goes in the public repo. The tick commits only that path there and pushes the ops repo. With `PFY_OPS_ROOT` unset, the tick writes `tmp/ops/eval/catalog-queue/needs-mark.tsv` in its worktree (gitignored) and commits nothing. `scripts/check_public_paths.py` fails a public commit that adds it.

Columns: `slug`, `kind`, `reason`, `evidence`, `since`.

`kind` is `hard-stop` (reason starts with the rule ID from `data/promotion-rules.json`: `HS-live-money`, `HS-release-deploy`, `HS-secrets`, `HS-runtime-takeover`, `HS-gpu-unapproved`, `HS-pull-over-25gb-unapproved`) or `supersede-stop`. Since the rules decision of 2026-11-10 nothing else is a row: ceiling flags, demotion flags, parked lanes, unknown risk, and exclusions are failed rules in the card's `promotion_history` (and park-history.tsv for parks), re-checked by the loop.

The loop skips every slug in that file. Do not launch them by hand from the loop.

## Rule retry

Each tick runs `catalog_apply_verdict.py --retry-refused` after the landed-lane applies. A card whose last stage ledger entry is a refusal with no hard stop and no failed verdict gate is re-applied once eval-structural is green on origin/main. `loop.latest.json` field `rule_retry` lists `promote`, `refuse`, or `hold` per card. `--launch-check` skips a card already above its rule-allowed stage and names the first failed rule; the scan re-checks it every tick.

## Markers

Taken, so the tick will not launch the slug:

- `.dispatched`, live `.pid`, `LANDED_<slug>`, `.done`, `.parked`
- Look in `$PFY_LOOP_STATE/eval`, `$PFY_LOOP_STATE/integrate`, `$PFY_INTEGRATE_ROOT`, and `$PFY_INTEGRATE2_ROOT` for every kind. `$PFY_EVQ_ROOT` is also checked for eval. An integrate2 marker skips that slug.

`integrate2` is another worker. Read its marker files only. Do not edit that directory and do not signal its processes. A pid file there counts toward the 4 running lanes only when `<slug>.dispatched` is beside it and the pid is alive. The same pid counts once. `scheduler.pid` and `scheduler.launch.pid` do not count.

`refused` lists each slug once. A slug this tick auto-raised is not in `refused`. That apply failure is in `apply_refused`.

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

## Supersede stop

The tick runs `python3 scripts/supersede_check.py` in the loop worktree after regeneration and before launch. The limit is 60 seconds. Tests set `PFY_SUPERSEDE_CHECK` to a stub executable. The checker reads the local watchlist only. It has no network mode and no offline flag. Do not invent one. An unknown flag makes it exit 2, and the tick then records status `error` and launches nothing.

- Exit 0: launch continues. Lines that start with `stale:` are copied in order to `loop.latest.json` field `supersede_stale`. They do not add a needs-mark row. When that list is non-empty and a slot is free, the tick starts one `scripts/supersede_recheck_lane.sh` unit that PT day (`pfy-lane-supersede-recheck`). It counts toward the 4 and the 20. It reads the five catalog skills, holds `scripts/model_lock.sh`, and may change only `data/supersede-watchlist.json` from public web, GitHub, and X reads. No installs, no GPU, no pulls. `STATE/supersede/tried-YYYYMMDD`, `recheck.dispatched`, or `recheck.parked` means that tick does not start another. To retry after a park, read `recheck.parked`, then remove `recheck.parked` and `recheck.dispatched`. The tried stamp still blocks that PT day.
- Exit 1: no-reinvention STOP. Append one `needs-mark.tsv` row with kind `supersede-stop`. The slug is the project id named in the checker output, or `supersede-watch` when it names none. Set `supersede` to `stop` and `status` to `stopped`. Launch nothing this tick, including the recheck. A later tick that still exits 1 does not append a second row for the same slug.
- Any other exit, including 124: `status` is `error`. Launch nothing. Do not write a supersede-stop row. The tick exits 0. Regeneration failures and a failed `systemd-run` still exit nonzero.

### How the operator clears it

1. Read the `supersede-stop` row and the checker output.
2. Decide adopt, adopt parts, or keep going. Record that on `data/supersede-watchlist.json`.
3. A project that covers all four parts in full stays exit 1 until its verdict is `replace_us`.
4. When the checker exits 0, the next tick rewrites the needs-mark queue and does not put the stop row back.
5. This is not the `STOP` file. Do not delete `STATE/STOP` to clear a supersede stop.

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

The five software-factory questions for this pipeline are answered in the private ops handoff for the catalog loop.

## GPU lanes

Approved GPU and over-25 GB slugs (`eval/catalog-queue/approvals.tsv`) are not launched by the loop. Start `scripts/gpu_lane_driver.sh --root <worktree>` detached (systemd-run --user). It runs one eval lane at a time, waits for GPU and RAM headroom, parks a pull with `no disk` when space is short, and keeps its markers in `$PFY_LOOP_STATE/gpu/` (driver.pid, progress.md, current, `<slug>.started`, `.finished`, `.parked`, ALL_DONE). Touch `$PFY_LOOP_STATE/gpu/STOP` to stop it between lanes.
