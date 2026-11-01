# Six-task bar on the integration tip

Two passes of MVP-2 t1 through t6 through `./pfy build` on branch `bot/mvp-sixtask-int-1031`.
Review stays on. No `--local`. No `--no-review`. `--timeout 900`. `--keep-worktree`.
Each task is a throwaway clone at `997d89264495861a178713ccf7d4447ea828afc4` with the canonical MVP-2 gate planted on `demo-base`.

`--writable-test` is passed only where the task file says a test must change.
t4: `tests/test_x_intake_smoke_112_114.py`.
t5: `tests/test_x_intake_smoke_117_118.py`, `tests/test_x_intake_smoke_119_121.py`.
t1, t2, t3, and t6 pass no writable path. The planted acceptance tests stay hashed.

`Status`, `Exit`, and `Attempts` are the receipt.
`Gate` is the canonical MVP-2 gate re-run (PASS only when that exit is 0).
`Review` is `review.verdict`, or `none` when the runner stored none.
`Human` is a read of the diff against the task text, stored on `meta.json` before this file is rendered.
`Writable` is the exact path list on that command.
`Wall_s` is the `./pfy build` process only.

| Pass | Task | Status | Exit | Attempts | Gate | Review | Human | Wall_s | Writable |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pass1 | t1-smolvm-stderr-first | PASS | 0 | 1 | PASS | accept | accept | 163.4 | - |
| pass1 | t2-tree-sig-119 | PASS | 0 | 1 | PASS | accept | accept | 65.7 | - |
| pass1 | t3-daemon-stop-fail | PASS | 0 | 1 | PASS | accept | accept | 366.3 | - |
| pass1 | t4-timeout-substep | PASS | 0 | 1 | PASS | accept | accept | 337.8 | tests/test_x_intake_smoke_112_114.py |
| pass1 | t5-receipts-outside-repo | PASS | 0 | 1 | PASS | accept | accept | 215.3 | tests/test_x_intake_smoke_117_118.py, tests/test_x_intake_smoke_119_121.py |
| pass1 | t6-tree-sig-three | PASS | 0 | 1 | PASS | accept | accept | 95.3 | - |
| pass2 | t1-smolvm-stderr-first | PASS | 0 | 1 | PASS | accept | accept | 150.5 | - |
| pass2 | t2-tree-sig-119 | PASS | 0 | 1 | PASS | accept | accept | 58.4 | - |
| pass2 | t3-daemon-stop-fail | PASS | 0 | 1 | PASS | accept | accept | 208.1 | - |
| pass2 | t4-timeout-substep | PASS | 0 | 1 | PASS | accept | accept | 349.0 | tests/test_x_intake_smoke_112_114.py |
| pass2 | t5-receipts-outside-repo | PASS | 0 | 1 | PASS | accept | accept | 174.3 | tests/test_x_intake_smoke_117_118.py, tests/test_x_intake_smoke_119_121.py |
| pass2 | t6-tree-sig-three | PASS | 0 | 1 | PASS | accept | accept | 76.0 | - |

| Pass | Tasks | Runner_pass | Review_accept | Human_accept | Gate_pass | Wall_s |
| --- | --- | --- | --- | --- | --- | --- |
| pass1 | 6 | 6 | 6 | 6 | 6 | 1243.8 |
| pass2 | 6 | 6 | 6 | 6 | 6 | 1016.3 |

VERDICT: GO

## Per task

pass1 t1-smolvm-stderr-first: status PASS, review accept, human accept, writable -.
pass1 t2-tree-sig-119: status PASS, review accept, human accept, writable -.
pass1 t3-daemon-stop-fail: status PASS, review accept, human accept, writable -.
pass1 t4-timeout-substep: status PASS, review accept, human accept, writable tests/test_x_intake_smoke_112_114.py.
pass1 t5-receipts-outside-repo: status PASS, review accept, human accept, writable tests/test_x_intake_smoke_117_118.py, tests/test_x_intake_smoke_119_121.py.
pass1 t6-tree-sig-three: status PASS, review accept, human accept, writable -.
pass2 t1-smolvm-stderr-first: status PASS, review accept, human accept, writable -.
pass2 t2-tree-sig-119: status PASS, review accept, human accept, writable -.
pass2 t3-daemon-stop-fail: status PASS, review accept, human accept, writable -.
pass2 t4-timeout-substep: status PASS, review accept, human accept, writable tests/test_x_intake_smoke_112_114.py.
pass2 t5-receipts-outside-repo: status PASS, review accept, human accept, writable tests/test_x_intake_smoke_117_118.py, tests/test_x_intake_smoke_119_121.py.
pass2 t6-tree-sig-three: status PASS, review accept, human accept, writable -.
pass1 t1-smolvm-stderr-first: reason ok, commit faeca84423835656425190ed626443cd92b05a26. Stderr pull is checked before the stdout cache line, and a cache line still wins when stderr has no pull. The smoke-section comment matches. Only smoke_109_111.py changed. The planted gate was not edited and the canonical rerun passed.
pass1 t2-tree-sig-119: reason ok, commit c3af3f0d16f366ea842f977a04a55442bbd43961. tree_sig now matches the content hash in smoke_122_124.py, including the unreadable marker. Only smoke_119_121.py changed. The planted gate was not edited and the canonical rerun passed.
pass1 t3-daemon-stop-fail: reason ok, commit 0b58a8166439ac34e18fab1acdceb90212fd246c. A daemon stop timeout is stored on the step and, when no lock is alive, returns 1 with that timeout text. A live lock still returns the daemon-still-running reason. A command timeout and a real HOME change still win over the stop-timeout reason. Only smoke_112_114.py changed. The planted gate was not edited and the canonical rerun passed.
pass1 t4-timeout-substep: reason ok, commit c9d9c61ccd5bec9740cbcc34a84a6a6296c9b23c. new times out with timeout_reason(new) and festival version times out with timeout_reason(version). The test file changes only the two expected strings. The daemon-stop assertion and the planted gate are unchanged. Canonical rerun passed.
pass1 t5-receipts-outside-repo: reason ok, commit b212478f521d312f14daa6e83c4c79de520b43ca. Both test modules set PFY_SMOKE_RECEIPT_DIR to a per-test temp dir and read the receipt from there. No smoke script changed. No assertion was skipped or weakened. The planted gate was not edited and the canonical rerun passed.
pass1 t6-tree-sig-three: reason ok, commit 8abf2e19f4a308fcc78fe0f8fe2cde17f3f7a54e. The three older tree_sig functions now match smoke_122_124.py, including the unreadable marker and the directory marker. smoke_119_121.py and smoke_122_124.py were not edited. No test file changed. The planted gate was not edited and the canonical rerun passed.
pass2 t1-smolvm-stderr-first: reason ok, commit 2be173e23796180ad2a84e65547bfd0265670965. Stderr pull is checked before the stdout cache line, and a cache line still wins when stderr has no pull. The smoke-section comment matches. Only smoke_109_111.py changed. The planted gate was not edited and the canonical rerun passed.
pass2 t2-tree-sig-119: reason ok, commit 7bf669d30f773b9a06971d25817e9c38d814a5f8. tree_sig now matches the content hash in smoke_122_124.py, including the unreadable marker. Only smoke_119_121.py changed. The planted gate was not edited and the canonical rerun passed.
pass2 t3-daemon-stop-fail: reason ok, commit b8e06a5dd3fce46110cfb50136956e2596a35f21. A daemon stop timeout with no live lock returns 1 and sets the step timeout text. A live lock still returns the daemon-still-running reason before that. A clean stop still falls through. Only smoke_112_114.py changed. The planted gate was not edited and the canonical rerun passed.
pass2 t4-timeout-substep: reason ok, commit eea0bcc89b913825afaf123b44dba7876974f230. new records timeout_reason(new) and festival version records timeout_reason(version). The test file changes only the two expected strings. The daemon-stop assertion and the planted gate are unchanged. Canonical rerun passed.
pass2 t5-receipts-outside-repo: reason ok, commit 32de678d415c0318a3507686e2c07f50b2047922. Both test modules set PFY_SMOKE_RECEIPT_DIR to a per-test temp dir and read the receipt from there. No smoke script changed. No assertion was skipped or weakened. The planted gate was not edited and the canonical rerun passed.
pass2 t6-tree-sig-three: reason ok, commit d131ccd13f154a8efc3fb88bb1acafd7843dc6a2. The three older tree_sig functions now match smoke_122_124.py, including the unreadable marker and the directory marker. smoke_119_121.py and smoke_122_124.py were not edited. No test file changed. The planted gate was not edited and the canonical rerun passed.

## What moved

The prior trial on the cloud runner without `--writable-test` was NO-GO: 4/6 runner PASS, because t4 and t5 exited `tests-tampered`. This tip has the flag. Both passes here are 6/6 runner PASS, 6/6 review accept, and 6/6 human accept. Each task took one attempt.

t4 writable path, both passes: `tests/test_x_intake_smoke_112_114.py`.
t5 writable paths, both passes: `tests/test_x_intake_smoke_117_118.py`, `tests/test_x_intake_smoke_119_121.py`.
t1, t2, t3, and t6 passed no `--writable-test`. The planted `tests/test_mvp2_t*.py` gates stayed hashed. `acceptance_unchanged` is true on every meta.

Wording moved and the outcome class did not. t1 comments differ between passes and both check stderr before the stdout cache line. t3 pass 1 applies the stop-timeout reason after the command-timeout check. t3 pass 2 returns that reason inside the try, after the live-lock check and before the real HOME check. Both match the task. t4 pass 1 stores the `new` reason before re-raising. t4 pass 2 sets a step name and lets the outer handler call `timeout_reason`. Both passes change only the two expected assertion strings. t2 and t6 match the canonical `tree_sig` in both passes.

No findings file. The bar is met, so there is no runner patch from this lane.
