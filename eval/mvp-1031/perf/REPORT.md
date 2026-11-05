# Cloud build perf report (mvp-cloud-perf-1031)

Finding: two real cloud builds on the pre-cut checkout timed out in the before-gate at the 600s cap. They are not a before/after speed number. The operator stopped further heavy-lock runs the same day. No after-cut build ran.

Scalar rows, with no gate tails: `eval/mvp-1031/perf/timeout-rows.json`.

## Runs

Checkout for every row: `bce574b1b32fd8523b5dfae646c473f2062cb1b8` (phase timing, no overlap cuts). Command shape: `./pfy build` with the default gate `python3 -m unittest discover -s tests -t .`, `--base HEAD`, `--retries 0`, `--timeout 600`, cloud grok, no `--local`. Throwaway clone: `tmp/perf-measure/before` (gitignored). Planned after checkout `f4a64ecc36a03f052ccaace71f9593c571181dcc` was never cloned.

| id | finished (UTC) | status | reason | wall_s | gate_s | agent_s | before gate | after gate | review |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| before-1-1 | 2026-11-01T00:55:51Z | TIMEOUT | timeout | 602.155 | 602.035 | 0.0 | exit 124, aborted timeout | not started | none |
| before-1-2 | 2026-11-01T01:05:54Z | TIMEOUT | timeout | 602.147 | 602.016 | 0.0 | exit 124, aborted timeout | not started | none |
| before-2-1 | 2026-11-01T01:10:15Z | FAIL | interrupted | 261.376 | 261.249 | 0.0 | exit -15, aborted interrupted | not started | none |

Task 1 text: create `docs/ops/perf-sample-a.txt` with the single line `sample-a`. Attempt 2 is the one automatic recovery of that timeout. Task 2 (sample-b) started and was interrupted during its before-gate. Task 3 did not start. Preflight stayed under 0.01s and worktree under 0.1s on all three rows. Commit stayed 0.

The before-gate tail on both TIMEOUT rows is still unittest progress. It does not contain an `OK` summary. 602s is the cap, not a measured suite length. Do not quote 602s as how long `unittest discover` takes on this host.

## Why there is no after column

The driver held `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` for about 40 minutes and blocked another lane. At 2026-10-31 18:10:18 local the operator killed `tmp/perf-measure/run.py` and wrote: do not rerun it under the heavy lock today; record the two TIMEOUT rows and finish. This lane did not start another `./pfy build` and did not start a full `unittest discover`.

The 600s cap was too short for this host. Both recoveries in the budget of 2 were spent on that cap. A longer timeout would be a new measurement, and the operator closed that window.

## What the cuts change, without a wall number

Historical receipts (survey, 2026-10-31T23:50Z) have no `phases` object. Combined harness median 167.4s (n=60). sixtask-int PASS median 168.9s (n=12). Those numbers are other runs. They are not this host's default suite.

Git setup on a throwaway clone was under 0.2s (worktree add 0.17s, archive to tar 0.14s). The runner does not `git fetch`. The repeated full gate is the non-model cost. The cuts overlap gates. They do not drop a gate.

| cut | SHA | what overlaps | when it stays serial |
| --- | --- | --- | --- |
| phase seconds | `bce574b1b32fd8523b5dfae646c473f2062cb1b8` | none; receipt gains `phases` and `wall_seconds` | dry-run and reap receipts stay without phases |
| A, post gates | `11bcb7d7fb6bd1b9500d15f62cb5be72f8320310` | after-change gate and flake gate, default test command only | `PFY_BUILD_SERIAL_GATES=1`, a custom `--test-cmd`, an unchanged tree, or a failed tree copy |
| B, review and extract | `f4a64ecc36a03f052ccaace71f9593c571181dcc` | review grok and the clean-extract recheck, after the commit is created | `--no-review` keeps the serial `commit_paths` path |

On a day when one default suite finishes, cut A removes one suite from the wall (the two post-change gates share one span) and cut B hides the extract behind the review call (the shorter of the two). This report does not claim that saving, because no build here reached those phases.

## Same checks

Behavior tests, re-run 2026-11-01T01:17Z on this worktree with `nice -n 19 python3 -m unittest tests.test_pfy_build_phase_clock tests.test_pfy_build_cloud`: 71 tests, OK, 25.821s. `tests.test_pfy_build_cloud` is 61 tests and stays green, including the custom-command counter tests that require a serial flake gate. The phase module is 10 tests:

- A PASS records all six phase keys and runs four gates.
- A red gate still records time for the gates that ran.
- `--no-review` still runs four gates.
- A gate nested inside commit is not also billed to commit.
- The default command overlaps the two post-change gates and still runs four gates.
- `PFY_BUILD_SERIAL_GATES=1` keeps four gates in order, with no overlap.
- A signal during the overlapped gates kills both gate children.
- Review overlaps only the clean-extract gate, and four gates still run.
- A review reject wins when the extract also fails: reason `review-rejected`, no branch, edits kept, the extract really missed the gitignored helper.
- A signal during review and recheck kills both children.

## Later measurement

Use checkout `bce574b` before the cuts and `f4a64ec` after both cuts. Three small file-create tasks, default gate, review on, `--retries 0`, no `--local`. Set `--timeout` above one finished default discover on that host. Hold the heavy lock only when no other lane needs it. The two TIMEOUT rows above are the baseline finding for the 600s cap, not the before sample.
