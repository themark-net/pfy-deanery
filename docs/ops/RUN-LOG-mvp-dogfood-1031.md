# Run log: mvp-dogfood-1031

Lane: extra cloud dogfood of `./pfy build "<task>"`. Branch `bot/mvp-dogfood-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-dogfood-1031`. Base `origin/bot/mvp-cloud-1031`.

Launch: 2026-10-31T20:16:44Z. Wall cap: 2026-11-01T04:16:44Z (8 hours), or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Stop new items by 2026-11-01T03:56:44Z so the handoff has 20 minutes. The 8 hour cap binds first.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     eval/mvp-1031/dogfood/REPORT.md covers at least 5 real ./pfy build cloud runs (aim 10+), each with receipt.json, diff.patch, gate, review, and human verdict. check_reports.py exits 0 on that tree. tests.test_mvp_1031_dogfood_reports passes, including a planted mismatch that exits 1. No fabricated PASS.
1 Goal met:                  check_reports.py exit 0, unittest of tests.test_mvp_1031_dogfood_reports OK, and at least 5 run dirs. More runs continue until another exit fires. Aim is 10+.
2 Turn cap:                  16 items (checker plus dogfood runs plus handoff). Drop-in aim is 10+ runs, so the agent-loops default of 8 is not the cap.
3 Budget cap:                12 real grok ./pfy build invocations. Cloud spend is expected. No --local. A rate-limit receipt is an honest result, not a retry into local.
4 Wall clock:                2026-11-01T04:16:44Z, or 2026-11-02T02:00Z, whichever first. Handoff starts 20 minutes earlier.
5 No-progress:               the same failure twice with no new information, or 3 items skipped in a row.
6 Human interrupt:           user says stop. Do not ask questions. Do not merge to main. Push of this bot/ branch is pre-authorized.
7 Error threshold:           3 consecutive same failures, or 2 rate-limit or auth failures in a row with no new information (also exit 5).
8 External event:            stop if origin/bot/mvp-cloud-1031 drops the cloud runner or this lane's drop-in is superseded. Otherwise n/a.
Loop type:                   goal, with a wall clock
Human gate:                  no merge, no PR, no tag. Push this branch only.
```

Drop-in exits (checked before every item):

1. Wall cap above. Leave 20 minutes for the handoff.
2. Lane empty: no remaining small code, test, docs-plus-test, or under-50-line refactor task that fits the rules.
3. No progress: same failure twice with no new information, or 3 skips in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 (2 x 32 cores) for 5 minutes. Pause 10 minutes, then stop if it still holds.
5. Red base: record tests that fail before our change and skip that area. Do not stop the lane.

## Plan

Overview: Dogfood the real cloud runner on throwaway clones. The lead merges `origin/bot/mvp-cloud-1031` before each item, runs `./pfy build` (never `--local`), and commits only this lane's report, receipts, and the three ops docs. A runner bug is a finding plus a cross-lane request, not an edit to the runner.

Phases:

- exits | docs/ops/RUN-LOG-mvp-dogfood-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-dogfood-1031.md | exit card and plan are in the run log before any dogfood build | none | general
- checker | eval/mvp-1031/dogfood/check_reports.py, tests/test_mvp_1031_dogfood_reports.py, eval/mvp-1031/dogfood/REPORT.md | `nice -n 19 python3 -m unittest tests.test_mvp_1031_dogfood_reports` OK, and a planted mismatch makes the checker exit 1 | exits | general
- dogfood-runs | eval/mvp-1031/dogfood/<nn>-<slug>/** | at least 5 real cloud runs recorded, then more until an exit, rotating code fix, new test, docs plus test, refactor under 50 lines | checker | general (lead, sequential)
- handoff | docs/ops/HANDOFF-mvp-dogfood-1031.md, run log final state line | handoff written, run log closed, both pushed | dogfood-runs or any exit | general

Risks:

- Rate limit or auth failure: commit the receipt, do not fabricate PASS, do not start `--local`, continue later until exit 5 or 7.
- `tests_tampered` treats a new file under `tests/` as tampering (scripts/pfy_build_cloud.py `tests_tampered`). A "add a test" task may FAIL. Record it as a finding for mvp-cloud-1031. Do not edit the runner.
- Full `unittest discover` is a heavy job. Dogfood gates use a targeted `--test-cmd` so this lane does not take the host lock for every attempt.
- Shared branch: do not spawn an implementer into another worktree. User rule forbids other worktrees under `tmp/`.

## Host at launch

MemAvailable about 64 GiB. Load about 3.6 on 32 cores. Under the pressure line.

## Log

item | commit | tests | result
exits | 210e0fe | none, docs only | written before dogfood builds
merge-cloud | 0747fee | not this lane's tests | merged origin/bot/mvp-cloud-1031 before the checker
checker | 552147c | tests.test_mvp_1031_dogfood_reports 7 ok | green, planted mismatch exits 1
merge-cloud-2 | 73b5581 | cloud lane docs only, runner bytes unchanged | merged before run 01
