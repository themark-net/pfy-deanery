# Dogfood report: mvp-dogfood-1031

Real cloud `./pfy build "<task>"` runs. Each target is a throwaway clone under this worktree's `tmp/`. Nothing from a target is pushed. A rate limit or auth failure stays in the table as that status. No PASS is filled in by hand.

Gate pass means the receipt's last attempt reached a green gate (status PASS, or an attempt reason other than `tests`, `tests-flaky`, or `tests-tampered` on a run that still finished PASS). Review accept means `review.verdict` is `accept`. Human accept means this lane would hand the `cloud/` commit to Mark.

## Runs

| dir | status | exit_code | gate | review | human | wall_s | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 01-stale-enterable | PASS | 0 | pass | accept | yes | 39 | ok |
| 02-enterable-test | FAIL | 1 | fail | none | no | 343 | tests-tampered |

## Rates

- runs: 2
- gate_pass_rate: 1/2
- review_accept_rate: 1/2
- human_accept_rate: 1/2
- median_wall_s: 191

Gate pass means the receipt status is PASS (the after-gate exited 0 twice). Review accept means `review.verdict` is `accept`. Human accept means this lane would hand that cloud commit to Mark. Median is the middle wall time in seconds, or the average of the two middle values when the count is even.

## Findings

| id | severity | run | summary |
| --- | --- | --- | --- |
| F1 | high | 02-enterable-test | A new test file is tests-tampered before the gate, on all 3 attempts, and the tree is deleted. A missing behavior test cannot PASS. See findings/F1-tests-tampered-new-file.md. |

Severity is high, medium, or low against the Functional MVP Definition of Done.
