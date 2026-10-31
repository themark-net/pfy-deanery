# RUN LOG mvp-realfail3-1031

Lane: real failure cases against the integration tip. Branch `bot/mvp-realfail3-1031`. Base `origin/bot/mvp-integrate-1031` at `0c3f133`. Launch `2026-10-31T22:38:29Z`.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     Nine real ./pfy build cases under eval/mvp-1031/realfail3/, each MATCH or FINDING against the MVP failure table. Receipts, REPORT.md, a behavior test that checks the report against the receipts, and a findings file with a suggested fix for every FINDING. The runner is not edited.
1 Goal met:                  tests/test_mvp_1031_realfail3_receipts.py passes, and the report has all nine cases with no pending row
2 Turn cap:                  9 cases, plus one harness commit and one handoff. A case may be repeated once when the first run did not reach the condition under test.
3 Budget cap:                Cloud Grok only. No --local. --retries 0. One implement call per run. Stop new cloud runs after two rate-limit receipts.
4 Wall clock:                8 hours from launch (2026-11-01T06:38:29Z) or 2026-11-02T02:00Z, whichever comes first. Stop new cases at 2026-11-01T06:18:29Z so the handoff has 20 minutes.
5 No-progress:               The same failure twice with no new information, or 3 items in a row skipped.
6 Human interrupt:           User stop. No question stops. Conservative choices go in the decisions file.
7 Error threshold:           3 consecutive case failures that add no new receipt evidence, then stop.
8 External event:            n/a until a later lane lands the same nine cases on this branch. Check origin before each case.
Loop type:                   goal
Human gate:                  No merge and no PR. Push this bot/ branch only. Gate at handoff: pregate plus Reviewer for eval and test-only changes. Tester plus Reviewer if a runtime file changes (it should not).
```

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-realfail3-1031.md` are the binding. Decision logged.

Drop-in exits, checked before every case:

1. Wall cap: launch plus 8 hours, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Handoff buffer 20 minutes.
2. Lane empty: the nine cases are done and no further real-failure gap fits this lane.
3. No progress: the same failure twice with no new information, or 3 skips in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores. Pause 10 minutes, then stop if it persists.
5. Red base: record tests that fail before this lane's change and skip that area. Do not stop the lane.

## Plan

Overview: Run nine new real `./pfy build` cases on throwaway clones under this worktree's `tmp/`. Judge each receipt against the Functional MVP failure table. Write `eval/mvp-1031/realfail3/REPORT.md`, keep the receipts, and add a behavior test. Do not edit the runner. A FINDING gets a short file with a suggested fix for mvp-cloudfix-1031.

Phases:

- exits | docs/ops/RUN-LOG-mvp-realfail3-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-realfail3-1031.md | exit card committed before any build | none | lead
- harness | eval/mvp-1031/realfail3/drive.py, gates, tests/test_mvp_1031_realfail3_receipts.py | targeted test green on an empty or partial report | exits | lead
- dirty-tree | eval/mvp-1031/realfail3/dirty-tree/ | receipt, report row, test green, pushed | harness | lead
- detached-head | eval/mvp-1031/realfail3/detached-head/ | same | harness | lead
- two-builds | eval/mvp-1031/realfail3/two-builds/ | same | harness | lead
- over-cap | eval/mvp-1031/realfail3/over-cap/ | same | harness | lead
- no-tests | eval/mvp-1031/realfail3/no-tests/ | same | harness | lead
- gate-hang | eval/mvp-1031/realfail3/gate-hang/ | same | harness | lead
- network-down | eval/mvp-1031/realfail3/network-down/ | same | harness | lead
- tmp-unwritable | eval/mvp-1031/realfail3/tmp-unwritable/ | same | harness | lead
- non-ascii | eval/mvp-1031/realfail3/non-ascii/ | same | harness | lead
- handoff | docs/ops/HANDOFF-mvp-realfail3-1031.md, this log's state line | pushed, no merge | cases or an exit | lead

The cases share `eval/mvp-1031/realfail3/` and one cloud budget. The user forbids extra worktrees. The lead runs the cases in order. No parallel implementation agents.

Risks:

- Grok is slow or rate-limits. Mitigation: `--retries 0`, a bounded `--timeout`, and stop new cloud runs after two `rate-limit` receipts. The network and read-only tmp cases do not call the real model.
- A gate hang uses the same `--timeout` as grok. Mitigation: the hang script passes on the first call (the before-gate) and sleeps after that. One rerun with a longer timeout if the first timeout is the model call.
- Host pressure from other lanes. Mitigation: check memory and load before each case. Pause 10 minutes once, then stop if it persists.
- Signaling the wrong process. Mitigation: the driver signals only process groups it started, and only for its own throwaway path.

## Expected rows (locked before the runs)

From the failure table on `origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`. Recovery prose that the runner stores in the receipt is checked in the case notes. The report's Recovery cell is the observed receipt field (`empty` or a substring).

| Case | Exp status | Exp reason | Exp exit | DoD row |
|------|------------|------------|----------|---------|
| dirty-tree | PASS | ok | 0 | Dirty caller checkout. Exit 0 is allowed when the base commit can be checked out. Dirty porcelain stays. The runner does not stash or reset. |
| detached-head | PASS | ok | 0 | Same checkout rule. Detached HEAD still names a commit, so `worktree-failed` is the wrong row. HEAD stays detached at the same SHA. |
| two-builds | PASS | intact | 0 | No concurrent row. Both runs exit 0, distinct `cloud/` branches, `git fsck` clean, caller HEAD and status unchanged. |
| over-cap | PASS | ok | 0 | No size row in the cloud table. A finished build is the PASS row. The local 3-file / 250-line cap is not a cloud failure row. |
| no-tests | FAIL | tests | 1 | Gate red, retries spent. The default discover command exits 1 when `tests/` is missing. |
| gate-hang | TIMEOUT | timeout | 3 | Timeout. Recovery should tell the operator to rerun with a longer `--timeout`. No commit. |
| network-down | FAIL | no-change | 1 | No network row. A non-zero grok exit that is not rate-limit or unauthenticated, with an empty diff and a green gate, is no-change. |
| tmp-unwritable | FAIL | worktree-failed | 1 | The base cannot be checked out when `tmp/` is not writable. Caller status unchanged. |
| non-ascii | PASS | ok | 0 | No encoding row. PASS keeps the non-ASCII task text. A path with a space may be committed. |

Flags on every probe: `--retries 0`, `--no-review`, `--base HEAD`, `--repo` on a throwaway clone. Review stays available on the product default. These probes pass `--no-review` so a reviewer verdict does not hide the git, gate, or timeout result. Decision logged.

## Items

Format: `item | commit | tests | result`

(none yet)
