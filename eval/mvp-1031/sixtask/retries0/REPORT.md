# Retries 0 pass

One attempt per task, review still on. The command adds `--retries 0` and does not pass `--no-review`. Fresh clone, canonical gate planted, `--timeout 900`, `--keep-worktree`. `Gate` is the canonical rerun. `Review` is `none` when the runner stored no verdict.

| Task | Status | Exit | Attempts | Gate | Review | Human | Wall_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1-smolvm-stderr-first | PASS | 0 | 1 | PASS | accept | accept | 174.7 |
| t2-tree-sig-119 | PASS | 0 | 1 | PASS | accept | accept | 58.7 |
| t3-daemon-stop-fail | PASS | 0 | 1 | PASS | accept | accept | 253.5 |
| t4-timeout-substep | FAIL | 1 | 1 | PASS | none | accept | 229.7 |
| t5-receipts-outside-repo | FAIL | 1 | 1 | PASS | none | accept | 108.9 |
| t6-tree-sig-three | PASS | 0 | 1 | PASS | accept | accept | 118.8 |

| Tasks | Gate_pass | Review_accept | Human_accept | Wall_s | Attempts | Exit_sum |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | 6 | 4 | 6 | 944.3 | 6 | 2 |

Same outcome class as pass 1 (2778.0 s, 10 attempts) and the variance pass (2356.0 s, 10 attempts). t4 and t5 failed `tests-tampered` on the only attempt. The extra attempts in the other passes did not produce a commit.
