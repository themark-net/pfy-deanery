# Run log mvp-mutate-cloud-1031

Lane: mutation testing of the daily cloud runner.
Branch: `bot/mvp-mutate-cloud-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-mutate-cloud-1031`
Base: `origin/bot/mvp-cloudfix-1031`
Launch: 2026-10-31T21:15:42Z

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     eval/mutation-1031/cloud/run_mutants.py applies C1..Cn one at a time on a throwaway clone, records killed or survived, and every survivor is killed by tests/test_mut_cloud_*.py or filed as a cross-lane expectedFailure. REPORT.md has the table.
1 Goal met:                  harness test green, mutant table complete, survivor re-run shows killed (or expectedFailure noted)
2 Turn cap:                  8 items (harness, baseline, one killing-test commit per survivor batch, report re-run, one cloudfix re-run, handoff). Stop at 8.
3 Budget cap:                no local model, no paid API, cloud Grok session only
4 Wall clock:                2026-11-01T05:15:42Z (8h from launch). Sunday 2026-11-02T02:00Z is later, so the 8h cap binds. Stop new items at 2026-11-01T04:55:42Z (20 min handoff).
5 No-progress:               same failure twice with no new information, or 3 items skipped in a row
6 Human interrupt:           user stop. Do not ask questions. No merge, no PR, no force push.
7 Error threshold:           3 consecutive command failures, then stop
8 External event:            origin/bot/mvp-cloudfix-1031 moves the runner. Re-merge before each round. Anchors that no longer match are unapplicable, not survived.
Loop type:                   goal
Human gate:                  no merge. Push the bot branch only. Tester plus Reviewer is the gate named in the handoff.
```

Drop-in exits (these stop the run): wall cap, lane empty, no progress, host pressure, red base.

Host at launch: MemAvailable about 59 GiB, load 4.98, 32 cores. Pressure line is MemAvailable under 16 GiB, or load over 64 for 5 minutes.

Red base: `nice -n 19 python3 -m unittest tests.test_pfy_build_cloud` in a throwaway clone, 44 tests, OK, 9.5s (2026-10-31). Not red.

## Plan

Overview: Mutation-test `scripts/pfy_build_cloud.py` only inside throwaway clones under this worktree's `tmp/`. Record which of C1..C16 the current suite kills. Add behavior tests for survivors. Do not edit the runner or `tests/test_pfy_build_cloud*.py`.

Phases:
- exits | this file | exit card written before the harness | none | general
- harness | `eval/mutation-1031/cloud/run_mutants.py`, `tests/test_mut_cloud_harness.py` | harness test green and the worktree runner hash unchanged | exits | general
- baseline | `eval/mutation-1031/cloud/results/`, `REPORT.md` | one row per mutant from `tests.test_pfy_build_cloud*` | harness | general
- kills | `tests/test_mut_cloud_*.py` (not the harness test) | each baseline survivor is killed on re-run, or expectedFailure plus a cross-lane note | baseline | general
- handoff | `docs/ops/HANDOFF-mvp-mutate-cloud-1031.md` | handoff and final `state:` line pushed | kills | general

Risks:
- cloudfix keeps editing the runner. Re-merge before each round. An anchor that misses is `unapplicable`, and the run exits 2 rather than calling it survived.
- A mutant can hang a test. Per-mutant timeout, then kill only processes whose cwd is the clone this harness started.
- Shared files and the single-worktree rule. The lead runs the phases in order. No second worktree.

## Items

item | commit | tests | result
