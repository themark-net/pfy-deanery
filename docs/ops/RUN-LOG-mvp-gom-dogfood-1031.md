# RUN-LOG mvp-gom-dogfood-1031

Branch `bot/mvp-gom-dogfood-1031`. Base `origin/bot/mvp-integrate-1031` (`86fcfba` includes the lane drop-in on top of integrate `0338b67`). Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-gom-dogfood-1031`. Gom worktree `~/DEVELOP/jobbar-master/tmp/gom-dogfood-1031` on `bot/gom-dogfood-1031`. No rebase, no force-push, no PR, no merge to main. No local model. Never pass `--local` to a real run. Mark's checkouts `~/DEVELOP/pfy-mentat` and `~/DEVELOP/jobbar-master/current` stay untouched.

Launch: 2026-10-31T21:15:13Z (grok pid 2167101 start). Wall cap: 2026-11-01T05:15:13Z (8 hours), or 2026-11-02T02:00Z (Sunday 2026-11-01 18:00 PT), whichever comes first. Stop new items by 2026-11-01T04:55:13Z so the handoff has 20 minutes. Binding cap is the 8 hour mark.

Overview: Prove `./pfy build` on a second real repo, Gom Jabbar (`themark-net/gom-jabbar-grok4`). Six or more small tasks from that repo's TODO and handoffs run through the cloud runner against throwaway clones. PASS plus a human accept is cherry-picked onto `bot/gom-dogfood-1031` with a Built-by trailer, tested, and pushed. Receipts, diffs, and a report land in `eval/gom-dogfood-1031/`. A behavior test checks that report rows match receipts and that a planted mismatch fails.

Phases:
- exits | `docs/ops/RUN-LOG-mvp-gom-dogfood-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-gom-dogfood-1031.md` | exit card and phase plan are in this file before any gom command or build | none | lead
- worktree | `~/DEVELOP/jobbar-master/tmp/gom-dogfood-1031` only, via the drop-in `git -C current fetch` and `worktree add` | branch `bot/gom-dogfood-1031` exists at `origin/main`; Mark's current HEAD and journal are unchanged | exits | lead
- select | gom `AGENTS.md`, `docs/DECISIONS.md`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md` (read only) | six or more small task briefs in this log, each with a test command that does not fetch jobs or touch a real journal | worktree | lead
- builds | `eval/gom-dogfood-1031/<n>-<slug>/` | each task has command, wall time, exit, attempts, review verdict, human verdict, redacted receipt, and diff | select | lead
- land | gom `bot/gom-dogfood-1031` and `docs/PENDING-HANDOFF.md` there | each PASS and human-accept commit is cherry-picked with the Built-by trailer, tests run, branch pushed; no PR and no merge to gom main | builds | lead
- report | `eval/gom-dogfood-1031/REPORT.md`, `tests/test_gom_dogfood_1031_report.py` | rows match receipts; a planted mismatch fails the checker | builds | lead
- handoff | `docs/ops/HANDOFF-mvp-gom-dogfood-1031.md`, this log | SHAs, skips, fail/recover, cross-lane requests, gate, next step | report and land | lead

Risks: cloud quota, so builds stay serial and never use `--local`. A throwaway clone keeps the runner worktree out of Mark's gom checkout. Human accept is a diff read against gom decisions (Decision 0006: no auto-submit, `submitted` stays false). Scratch and `TMPDIR` stay under this worktree `tmp/` except the drop-in gom scratch. No scrapers, Playwright, network job fetches, or real journal.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     six or more real ./pfy build runs on throwaway clones of Gom Jabbar; each recorded under eval/gom-dogfood-1031/<n>-<slug>/; PASS and human-accept commits cherry-picked to bot/gom-dogfood-1031 with Built-by trailer, tests run, branch pushed; REPORT.md rows match receipts; tests.test_gom_dogfood_1031_report fails a planted mismatch
1 Goal met:                  tests.test_gom_dogfood_1031_report plus the recorded receipt fields (exit, attempts, review verdict, human verdict) for each run
2 Turn cap:                  8 build tasks, then report, land notes, and handoff (stop new builds at 8 even if the wall clock remains)
3 Budget cap:                cloud Grok only; no --local; no second model; stop new builds if two runs return rate-limit
4 Wall clock:                2026-11-01T05:15:13Z or 2026-11-02T02:00Z, whichever comes first; handoff starts 20 minutes earlier
5 No-progress:               same failure twice with no new information, or 3 items skipped in a row
6 Human interrupt:           user stop; do not ask; conservative decision goes in the decisions file
7 Error threshold:           3 consecutive same failures, then stop
8 External event:            lane empty when no further gom TODO item fits these rules; or the task is already done on origin/main
Loop type:                   goal
Human gate:                  lead reads each PASS diff before cherry-pick; no merge, no PR; push bot/mvp-gom-dogfood-1031 and gom bot/gom-dogfood-1031 only
```

Drop-in exits, checked before every item:

1. Wall cap above. Leave 20 minutes for the handoff.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this change. Record them and skip that area. Do not stop the lane.

Launch host: MemAvailable 59.6 GiB (62515772 kB), 32 cores, load 4.98. Under the pressure line.

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-gom-dogfood-1031.md` are the binding.

## Items

Format: `item | commit | tests | result`

- exits | 86639b759ad3a9724df6da71a5e997c9d852e5ba | none (docs only, before code) | written

Host before worktree: 2026-10-31T21:16:30Z MemAvailable 59.6 GiB, load 4.98, 32 cores. Under the pressure line.

- worktree | none on this branch (gom worktree only) | Mark's `current` stayed `2d26630915783ada9f6631fed125b6c1b566da6c` on `main` with the same three dirty paths and the same journal mtime `1790360353` size `1744896`. New worktree `bot/gom-dogfood-1031` at `d097e7ee65e56d626c612b360ea663780988d262` (`origin/main`). | pass

## Task list (T-0034 only)

Other open TODO rows are skipped. Reasons are in the decisions file. Each task gets a red test on the throwaway base, then `./pfy build` with `--retries 1 --timeout 900`. No `--local`.

| n | slug | behavior the red test requires |
|---|------|--------------------------------|
| 01 | catch-view-thread | `catch --view` prints `in_reply_to:` and `references:` only when stored values are non-empty |
| 02 | catch-view-meta | `catch --view` prints stored `has_attachments` and `size` |
| 03 | catch-view-index | a window of the last 20 catches uses journal indexes, not 0..19 |
| 04 | catch-view-parties | `catch --view` prints stored `from` and `reply_to` when non-empty, and does not print `raw_source` |
| 05 | land-thread-provenance | landing a catch copies `in_reply_to` and `references` onto capture provenance and does not copy `raw_source` |
| 06 | capture-list-thread | `format_item_line` shows `message_id` and `in_reply_to` when provenance has them |

## Items continued

Host before 01: 2026-10-31T21:27:52Z MemAvailable 59.8 GiB, load 3.57, 32 cores. Under the pressure line.

- 01-catch-view-thread | cloud ddb8e75693394b05e2a18880d68a6e309b1bb573 landed 69d99ceb5c6016bd4b5330596dd9b1094fa45f92 (test 38cacafe4a1b416b165d9ac0acec5bd024bab896) | gate before exit 1, after 1 passed in 0.18s; land pytest 1 passed | PASS review accept human accept wall 122s

Host before 02: 2026-10-31T21:31:47Z MemAvailable 58.7 GiB, load 4.48, 32 cores. Under the pressure line.

- 02-catch-view-meta | cloud 86b67cae44e9a85eb7d3959040435fc78eddb919 landed 63ee84be73eb3d38d5e0cfdd7a657bf8455f41c0 (test ca1a8fad130b1fba72663c214158079b138ca3f5) | gate before exit 1, after exit 0; land pytest 2 passed | PASS review accept human accept wall 101s

Host before 03: 2026-10-31T21:34:42Z MemAvailable 57.7 GiB, load 4.30, 32 cores. Under the pressure line.

- 03-catch-view-index | cloud 3960757fce438fe83adadafe0dc8ecba38160fba landed 038e18cf69d0a2cc086c7a0e679ff27668b04e53 (test 4b2f29e72cd826b0da13363faa0a0c93c8113d7e) | gate before exit 1, after exit 0; land pytest 3 passed | PASS review accept human accept wall 106s

Host before 04: 2026-10-31T21:37:38Z MemAvailable 59.3 GiB, load 4.50, 32 cores. Under the pressure line.

- 04-catch-view-parties | cloud 26a6d07230c962068491ce7ffa6b6ace14f3bcc3 landed 760a163f67c2ea236442b9e6a4261de089e0b2e6 (test bb69b6460f5489ed61cbf37294d3655593decb52) | gate before exit 1, after exit 0; land pytest 4 passed | PASS review accept human accept wall 84s

Host before 05: 2026-10-31T21:41:15Z MemAvailable 57.0 GiB, load 4.20, 32 cores. Under the pressure line.

- 05-land-thread-provenance | cloud 0c06365b9afbe7012f02cdd351d589e1c6502db6 landed b1288bc98421ecacd30b3359f13d32d31ff1f7fd (test 48644529f172ed8fac7822963dd1161be1fe9c54) | gate before exit 1, after exit 0; land pytest 5 passed | PASS review accept human accept wall 85s

Host before 06: 2026-10-31T21:46:18Z MemAvailable 58.6 GiB, load 4.18, 32 cores. Under the pressure line.

- 06-capture-list-thread | cloud 7600d6cf88477251bd80b56dca59dd8ef82d49c5 landed 3d9aac7b434e02d93ecab45a97457f5b2069dcb3 (test 213344387c16f3cfbdaaccebd60bd8e36c40fe41) | gate before exit 1, after exit 0; land pytest 6 passed | PASS review accept human accept wall 141s

Host before report: 2026-10-31T21:54:47Z MemAvailable 57.8 GiB, load 4.53, 32 cores. Under the pressure line. Runner.Worker pid 2631906 is running.

- report | 0597d274755aef04a0347607504e84e930b2e0de | tests.test_gom_dogfood_1031_report 2 tests OK | rows match receipts; a planted exit and a planted attempt count fail the checker
- gom handoff | 02e421de4cc1a7beca16846b2ac18acc1c28df5b on bot/gom-dogfood-1031 | six landed tests already green | dated section lists the cherry-picked commits

prior-state: goal met 2026-10-31T21:54:47Z. Six cloud builds PASS and human-accept. Gom tip 02e421de4cc1a7beca16846b2ac18acc1c28df5b. Report checker green. pregate not run: host busy. No merge.

## Resume 2026-10-31T22:07Z

Host: MemAvailable 59.2 GiB, load 3.18, 32 cores. Under the pressure line. `Runner.Worker` was idle. The heavy lock was not.

- resume check | none | tests.test_gom_dogfood_1031_report 2 tests OK; six gom tests 6 passed in 0.90s | receipts match the report; journal mtime 1790360353 size 1744896 unchanged; no builds 07 or 08
- pregate | not run | stopped before lock acquire at 2026-10-31T22:43:21Z | host busy: Runner.Worker pid 3199955, other pregates queued on the heavy lock

prior-state: goal met 2026-10-31T22:44:05Z. Six cloud builds remain PASS. Pregate not run: host busy. No merge.

## Resume 2026-10-31T22:52Z

Host: MemAvailable 45.5 GiB, load 4.81, 32 cores. Under the pressure line (2x cores is 64). `Runner.Worker` pid 3199955 is running. No new build. Turn cap stays at the six landed tasks. Further gom TODO rows stay skipped (parked, open question, scraper, or operator-ask).

- resume check | none | tests.test_gom_dogfood_1031_report 2 tests OK; six gom tests 6 passed in 1.06s | HEAD matches origin on both bot branches; journal mtime 1790360353 size 1744896 unchanged; receipt scan has no AKIA, private-key, sk-, or ghp_ markers
- pregate | not run | not queued | host busy: Runner.Worker pid 3199955

prior-state: goal met 2026-10-31T22:52:50Z. Lane empty. Pregate not run: host busy. No merge.

## Wave 5 (2026-10-31T23:30Z)

The drop-in addendum supersedes the earlier goal-met lines. Same worktree and branch rules. No rebase, no force-push, no PR, no merge to main. No `--local`.

Overview: Merge `origin/bot/mvp-integrate-1031` so this branch uses the latest cloud runner, then run six more real `./pfy build` tasks on Gom Jabbar. The six are T-0034 slices that are not 01 through 06: view `to`, view `cc`, view stored Date header, land `from` and `reply_to`, land `to` and `cc`, list `references`. PASS plus human accept is cherry-picked onto `bot/gom-dogfood-1031`. Rejected diffs stay off that branch. Receipts and a Wave 5 section land in `eval/gom-dogfood-1031/REPORT.md`. Runner friction is a cross-lane request for mvp-cloudfix-1031.

Phases:
- wave5-exits | this log, `docs/ops/AUTONOMOUS-DECISIONS-mvp-gom-dogfood-1031.md` | this card is in the log before the merge and before any build | none | lead
- merge | this branch, runner from integrate | `origin/bot/mvp-integrate-1031` is merged with a merge commit, never a rebase; `./pfy build --help` is the post-merge runner | wave5-exits | lead
- select | task briefs under `eval/gom-dogfood-1031/07` through `12` | six briefs, each a different stored-header behavior, each with a red test that does not fetch jobs or touch a real journal | merge | lead
- builds | `eval/gom-dogfood-1031/07` through `12` | each task has command, wall time, exit, attempts, review verdict, human verdict, redacted receipt, and diff | select | lead
- land | gom `bot/gom-dogfood-1031` and its `docs/PENDING-HANDOFF.md` | only PASS and human-accept commits are cherry-picked with the Built-by trailer, tests run, branch pushed; no PR and no merge to gom main | builds | lead
- report | `eval/gom-dogfood-1031/REPORT.md`, `tests/test_gom_dogfood_1031_report.py` | Wave 5 rows match receipts; a planted mismatch still fails | builds | lead
- handoff | `docs/ops/HANDOFF-mvp-gom-dogfood-1031.md`, this log | SHAs, skips, fail/recover, cross-lane requests, gate, next step, final state line | report and land | lead

Risks: cloud quota, so the six builds stay serial and never use `--local`. A throwaway clone keeps the runner off Mark's gom checkout. Human accept is a diff read (no auto-submit, `submitted` stays false, no raw_source leak, no scraper). Scratch and `TMPDIR` stay under this worktree `tmp/` except the gom scratch at `~/DEVELOP/jobbar-master/tmp/gom-dogfood-1031-scratch/`. The merge can conflict; lane-owned docs stay this lane's text, and runner code stays the integrate side.

## WAVE 5 LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     merge origin/bot/mvp-integrate-1031 (merge, never rebase); six more real ./pfy build runs, different from 01-06, recorded under eval/gom-dogfood-1031/; human accept cherry-picked to bot/gom-dogfood-1031 with Built-by trailer; rejected diffs stay off that branch; REPORT.md Wave 5 rows match receipts; tests.test_gom_dogfood_1031_report fails a planted mismatch
1 Goal met:                  six new receipt directories plus the report checker green, whether each run was accepted or honestly rejected
2 Turn cap:                  six new builds (07 through 12), then report, land notes, and handoff. Do not redo 01-06. Do not start 13
3 Budget cap:                cloud Grok only; no --local; no second model; stop new builds if two runs return rate-limit
4 Wall clock:                original launch cap still binds: 2026-11-01T05:15:13Z or 2026-11-02T02:00Z, whichever comes first; handoff starts 20 minutes earlier (2026-11-01T04:55:13Z)
5 No-progress:               same failure twice with no new information, or 3 items skipped in a row
6 Human interrupt:           user stop; do not ask; conservative decision goes in the decisions file
7 Error threshold:           3 consecutive same failures, then stop
8 External event:            no further gom backlog item that fits these rules after the six; skip open OQs, scrapers, Playwright, secrets, and operator-ask items
Loop type:                   goal
Human gate:                  lead reads each PASS diff before cherry-pick; no merge, no PR; push bot/mvp-gom-dogfood-1031 and gom bot/gom-dogfood-1031 only
```

Drop-in exits, checked before every Wave 5 item:

1. Wall cap above. Leave 20 minutes for the handoff.
2. Lane empty: the six new slices are the items that fit. Parked rows stay skipped.
3. No progress: the same failure twice with no new information, or 3 items skipped in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this change. Record them and skip that area. Do not stop the lane.

Wave 5 host at 2026-10-31T23:30Z: MemAvailable 41.9 GiB (43960480 kB), load 6.32, 32 cores. Under the pressure line. `Runner.Worker` pid 3751002 is running. Pregate stays deferred until the end, and only if that process is gone.

## Wave 5 task list (T-0034, not the first six)

| n | slug | behavior the red test requires |
|---|------|--------------------------------|
| 07 | catch-view-to | `catch --view` prints `to:` only when the stored string is non-empty, and does not print `raw_source` |
| 08 | catch-view-cc | `catch --view` prints `cc:` only when the stored string is non-empty, and does not print `raw_source` |
| 09 | catch-view-date | `catch --view` prints `date:` from stored `headers.date` only when that string is non-empty, and does not print `raw_source` |
| 10 | land-mailbox-parties | landing a catch copies non-empty `from` and `reply_to` onto provenance and does not copy `raw_source` |
| 11 | land-recipients | landing a catch copies non-empty `to` and `cc` onto provenance and does not copy `raw_source` |
| 12 | capture-list-references | `format_item_line` shows `references` when provenance has a non-empty list, and omits the label when it does not |

Skipped again, with the same reasons as the decisions file: T-0022, T-0023, T-0027, scraper and Playwright slices, T-0030, T-0031, T-0032, T-0033, T-0050, T-0051, Streamlit walks, and `capture serve` (needs `GOMJOBBAR_LAND_TOKEN`). Create-once already passes. Do not invent a sticky.
