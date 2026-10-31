# Dogfood report: mvp-dogfood-1031

Real cloud `./pfy build "<task>"` runs. Each target is a throwaway clone under this worktree's `tmp/`. Nothing from a target is pushed. A rate limit or auth failure stays in the table as that status. No PASS is filled in by hand.

Gate pass means the receipt's last attempt reached a green gate (status PASS, or an attempt reason other than `tests`, `tests-flaky`, or `tests-tampered` on a run that still finished PASS). Review accept means `review.verdict` is `accept`. Human accept means this lane would hand the `cloud/` commit to Mark.

## Runs

| dir | status | exit_code | gate | review | human | wall_s | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

## Rates

- runs: 0
- gate_pass_rate: n/a
- review_accept_rate: n/a
- human_accept_rate: n/a
- median_wall_s: n/a

## Findings

| id | severity | run | summary |
| --- | --- | --- | --- |

None yet. Severity is high, medium, or low against the Functional MVP Definition of Done.
