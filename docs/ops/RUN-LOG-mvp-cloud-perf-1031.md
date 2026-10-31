# RUN LOG mvp-cloud-perf-1031

Launch: 2026-10-31T23:39:44Z
Branch: bot/mvp-cloud-perf-1031
Worktree: ~/DEVELOP/pfy-mentat/tmp/mvp-cloud-perf-1031
Base: origin/bot/mvp-integrate-1031
HEAD at launch: ced61aebf6c32124d0c4c55b7201e500070ef9a4
Wall cap: 2026-11-01T07:39:44Z (8h from launch). Sunday 2026-11-01 18:00 PT is 2026-11-02T02:00Z, later than the 8h cap, so the 8h cap binds. Stop opening new items at 2026-11-01T07:19:44Z (20 min handoff reserve).
Host at launch: MemAvailable about 39 GiB (above 16 GiB). Load 6.95 on 32 cores (under 64). Runner.Worker was running, so pregate stays off unless a later check shows the runner idle.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria): daily ./pfy build keeps the same checks and is faster outside the model call. Receipt carries phase wall seconds (preflight, worktree, agent, gate, review, commit) or the survey proves they already exist. Top 2 non-model overheads are cut, each with a behavior test that fails if that check is skipped. eval/mvp-1031/perf/REPORT.md has before and after wall time for 3 real small tasks each, measured in throwaway clones under this worktree tmp/.
1 Goal met:                  report file plus green targeted tests for timing and for each cut. Lead evaluates. No model self-score.
2 Turn cap:                  8 items after this exit card. Survey, timing, cut A, cut B, measure, then at most 3 follow-on gaps.
3 Budget cap:                cloud Grok only for the 6 measurement builds (3 before, 3 after) plus at most 2 recovery reruns. No --local. No extra cloud builds for exploration.
4 Wall clock:                2026-11-01T07:39:44Z absolute. Handoff starts by 2026-11-01T07:19:44Z.
5 No-progress:               same failure twice with no new information, or 3 items skipped in a row. Hash = test output first line or the skip reason.
6 Human interrupt:           user stop. Do not ask. Conservative choice goes in the decisions file.
7 Error threshold:           3 consecutive failed items, or the same assertion twice. Then stop.
8 External event:            if origin/bot/mvp-integrate-1031 or origin/main already has the same phase timing and the same two cuts, record that and skip. Do not rewrite it.
Loop type:                   goal
Human gate:                  no merge, no PR. Push this bot/ branch only. Tester plus Reviewer for runtime changes.
```

Drop-in exits (also binding):

1. Wall cap: as above.
2. Lane empty: no remaining item that fits this lane and these rules.
3. No progress: same failure twice with no new information, or 3 items skipped in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this lane's change. Record and skip that area. Do not stop the lane.

## Overview

Make the daily `./pfy build` faster without dropping checks. Collect phase wall time from existing receipts. If those receipts lack phase times, add them first. Cut the top two overheads that are not the model call. Prove the same checks still run. Measure three real small tasks before and after in throwaway clones. Write `eval/mvp-1031/perf/REPORT.md`. Edits to `scripts/pfy_build_cloud.py` stay small and per-function because mvp-cloudfix-1031 is live on that file.

## Phases

- exits | docs/ops/RUN-LOG-mvp-cloud-perf-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-cloud-perf-1031.md | exit card and this plan are on the branch before product code | depends on none | general
- survey | read-only receipts under eval/mvp-1031, eval/selfhost-1031, and sixtask-int receipts on their remote branches | a phase-seconds table, or a written finding that phase keys are absent | depends on exits | general
- phase-timing | one function in scripts/pfy_build_cloud.py or a new helper this lane owns, plus one behavior test module this lane owns | receipt JSON includes the six phase seconds; the test fails if a phase is missing or a stalled phase is reported as instant | depends on survey | general
- cut-a | one function, disjoint from cloudfix's live edit if possible, plus a behavior test | the largest non-model overhead is smaller and the same check still runs | depends on phase-timing | general (performance-engineer notes in the prompt; lead implements because the file is shared)
- cut-b | a second function plus a behavior test | the second overhead is smaller and its check still runs | depends on cut-a when they share a file | general
- measure | eval/mvp-1031/perf/REPORT.md, throwaway clones under tmp/ | 3 tasks before (parent commit) and 3 after (this branch), same checks, wall times recorded, no invented numbers | depends on cut-a and cut-b | general
- next-gap | only files this lane already owns, or new files under eval/mvp-1031/perf/ and the timing helper | next perf gap that fits, or lane empty | depends on measure | general
- handoff | docs/ops/HANDOFF-mvp-cloud-perf-1031.md and the final state line in this log | handoff committed and pushed | depends on all earlier phases | general

## Risks

- Live edit collision on scripts/pfy_build_cloud.py with mvp-cloudfix-1031. Mitigation: re-read the file immediately before each edit, change one function, prefer a new helper module this lane owns, and record a cross-lane request instead of taking a file another lane owns.
- Real measurement builds call cloud Grok. Mitigation: budget cap of 6 builds plus 2 recovery reruns, throwaway clones only under this worktree tmp/, never --local, never Mark's main checkout.
- Before/after measured on the same code. Mitigation: before runs use a clone checked out at the pre-cut commit; after runs use this branch tip.
- Host pressure from parallel lanes. Mitigation: recheck MemAvailable and load before each item. Targeted tests only, niced. No unittest discover, no make eval-*, no docker, no pregate while Runner.Worker is up.
- Missing skills repo-handoff-doc-required and write-loop-exits-first. Mitigation: this card plus the drop-in handoff path stand in. Do not invent those skill files.
- Sub-agents on shared files. Mitigation: do not spawn implementation worktrees. This worktree is the only checkout this lane may touch. project-map may write only .project-map/.

## Survey

2026-10-31T23:50Z. 85 receipts with schema `pfy-cloud-build/1`. Zero have a `phases` object. `origin/main` and `origin/bot/mvp-integrate-1031` have no `phase_clock` in `scripts/pfy_build_cloud.py`.

Harness totals (not a phase split): `wall_seconds` n=18 median 172.2s, `wall_s` n=36 median 145.8s, `receipt_wall_seconds` n=6 median 392.8s. Combined median 167.4s (n=60, min 18.7s, max 2203.5s). The drop-in's "about 119s" sits in that range and below this median. sixtask-int Wall_s median of the 12 PASS rows is 168.9s.

Git bench on a throwaway shared clone of this repo (1672 files): worktree add 0.17s, `git archive | tar` 0.14s, status 0.06s, test-file hash walk 0.016s. Full `unittest discover` was not run: `flock -w 20` on `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` did not get the lock. One targeted module, `tests.test_pfy_build_cloud`, took 22.3s for 61 tests. The repeated full gate is the non-model cost. Git setup is not.

## Items

```text
item | commit | tests | result
exits | 11cf824 | none (docs before code) | pushed
survey | (recorded in the phase-timing commit) | read-only receipt scan plus git bench | no phase keys; git under 0.2s; discover skipped, lock busy
```
