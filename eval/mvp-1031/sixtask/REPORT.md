# MVP six-task trial through ./pfy build

Pass 1. Branch `bot/mvp-sixtask-1031`. Runner from `origin/bot/mvp-cloud-1031` (merged, lane head at the start of each task is in that task's `meta.json`). Review on. No `--local`. No `--no-review`. `--timeout 900`. `--keep-worktree`. One throwaway clone per task at `997d89264495861a178713ccf7d4447ea828afc4`, with the canonical MVP-2 gate planted on `demo-base`.

`Gate` in the table is the canonical MVP-2 gate re-run on the produced tree (the commit when one exists, otherwise the kept worktree) with the planted acceptance test restored if the agent changed it. `Status`, `Exit`, and `Attempts` are the receipt. `Review` is `review.verdict` (`none` when the runner never stored one). `Human` is a read of the diff against the task text.

| Task | Status | Exit | Attempts | Gate | Review | Human | Wall_s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1-smolvm-stderr-first | PASS | 0 | 1 | PASS | accept | accept | 211.2 |
| t2-tree-sig-119 | PASS | 0 | 1 | PASS | accept | accept | 66.3 |
| t3-daemon-stop-fail | PASS | 0 | 1 | PASS | accept | accept | 259.7 |
| t4-timeout-substep | FAIL | 1 | 3 | PASS | none | accept | 1439.7 |
| t5-receipts-outside-repo | FAIL | 1 | 3 | PASS | none | accept | 707.7 |
| t6-tree-sig-three | PASS | 0 | 1 | PASS | accept | accept | 93.4 |

| Tasks | Gate_pass | Review_accept | Human_accept | Wall_s | Attempts | Exit_sum |
| --- | --- | --- | --- | --- | --- | --- |
| 6 | 6 | 4 | 6 | 2778.0 | 10 | 2 |

## Comparison

| Arm | Runner gate | Review accept | Human accept | Wall |
| --- | --- | --- | --- | --- |
| MVP-2 cloud baseline | 6/6 | 6/6 | 6/6 | 583.6 s (drop-in rounds this to 584 s) |
| MVP-3 local | 5/6 | 5/6 loop | 4/6 | 3859.9 s (drop-in rounds this to 3860 s) |
| This pass, cloud default `./pfy build` | 4/6 runner PASS, 6/6 canonical gate | 4/6 | 6/6 | 2778.0 s |

Runner gate means receipt `status` `PASS` (commit plus review accept). Canonical gate means the MVP-2 test on the produced tree.

## Verdict

NO-GO for cloud-default `./pfy build` as Mark's daily build command, if the bar is keeping MVP-2's 6/6 gate and 6/6 review accept.

Reasons:

1. t1, t2, t3, and t6 pass the daily command in one attempt. Review verdict is accept. Canonical gate rerun is 0. Commits are `a96d0776bdb82fc98d4f6c8789efe381697f1550`, `6951f72013c776f9b3107bff646c81106121553b`, `fe211001ba9b6bee1e7f7e8cd937f779a8538244`, and `2ed13d37634a6a3b9220890144f4b818ff4d057d`. Branches start with `cloud/`. `pushed` is false. Those four are the shape the runner is built for: edit product code, do not touch tests.
2. t4 and t5 exit 1, reason `tests-tampered`, three attempts, no commit, review never runs. The diffs are the right fixes. t4's smoke change matches `eval/mvp2/patches/t4-timeout-substep-C.patch`. t5 sets `PFY_SMOKE_RECEIPT_DIR` in the two test modules the task names. The canonical gate rerun exited 0 for both, and the planted acceptance test was unchanged. The runner still refuses the commit because any `tests/` edit is tamper and `--writable-test` does not exist.
3. Wall 2778.0 s is mostly those two rejected tasks (1439.7 s and 707.7 s). The four PASS tasks sum to 630.6 s, near the old six-task cloud total, with a review call included. That is not 6/6.
4. The failure matches the runner's own contract. It does not match the lane bar. A suggested patch is `eval/mvp-1031/sixtask/findings/writable-test.patch`. Detail: `eval/mvp-1031/sixtask/findings/writable-test.md`. This lane did not edit the runner.

## Per task

t1. Command: `./pfy build` on `eval/mvp2/tasks/t1-smolvm-stderr-first.md`, `--repo` the t1 clone, `--base demo-base`, gate `python3 -m unittest tests.test_mvp2_t1_smolvm_evidence`. Exit 0. 211.2 s. 1 attempt. Review accept. Human accept. Stderr pull wins, cache-only still works, only `smoke_109_111.py` changed.

t2. Same shape, task `t2-tree-sig-119.md`, gate `python3 -m unittest tests.test_mvp2_t2_tree_sig_119`. Exit 0. 66.3 s. 1 attempt. Review accept. Human accept. `tree_sig` matches `smoke_122_124.py`.

t3. Task `t3-daemon-stop-fail.md`. Gate is the MVP-2 t3 test plus `test_overtime_daemon_stop_timeout_uses_shared_text`. Exit 0. 259.7 s. 1 attempt. Review accept. Human accept. A stop timeout with no live lock returns 1 after the real HOME check.

t4. Task `t4-timeout-substep.md`. Exit 1. 1439.7 s. 3 attempts. Review none. Canonical gate 0. Human accept of the diff. Runner reason `tests-tampered`. No commit.

t5. Task `t5-receipts-outside-repo.md`. Exit 1. 707.7 s. 3 attempts. Review none. Canonical gate 0. Human accept of the diff. Runner reason `tests-tampered`. No commit.

t6. Task `t6-tree-sig-three.md`, gate `python3 -m unittest tests.test_mvp2_t6_tree_sig_three`. Exit 0. 93.4 s. 1 attempt. Review accept. Human accept. The three older `tree_sig` functions match `smoke_122_124.py`. `smoke_119_121.py` and `smoke_122_124.py` were not edited.

Receipts: `eval/mvp-1031/sixtask/<task>/receipt.json`. Diffs: `diff.patch` next to each receipt. Nothing was pushed from the target clones.
