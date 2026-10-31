# Variance pass

Second full run of the six tasks. Same command shape as pass 1: review on, `--timeout 900`, `--keep-worktree`, fresh clone, canonical gate planted. `Gate` is the canonical rerun. `Review` is `none` when the runner stored no verdict.

| Task | Status | Exit | Attempts | Gate | Review | Human | Wall_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1-smolvm-stderr-first | PASS | 0 | 1 | PASS | accept | accept | 130.2 |
| t2-tree-sig-119 | PASS | 0 | 1 | PASS | accept | accept | 51.1 |
| t3-daemon-stop-fail | PASS | 0 | 1 | PASS | accept | accept | 225.8 |
| t4-timeout-substep | FAIL | 1 | 3 | PASS | none | accept | 999.4 |
| t5-receipts-outside-repo | FAIL | 1 | 3 | PASS | none | accept | 839.0 |
| t6-tree-sig-three | PASS | 0 | 1 | PASS | accept | accept | 110.5 |

| Tasks | Gate_pass | Review_accept | Human_accept | Wall_s | Attempts | Exit_sum |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | 6 | 4 | 6 | 2356.0 | 10 | 2 |

Pass 1 wall was 2778.0 s with the same 4/6 runner PASS, 4/6 review accept, and 6/6 human accept. t4 and t5 failed `tests-tampered` on both passes.
