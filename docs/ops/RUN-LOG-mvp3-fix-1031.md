# RUN-LOG mvp3-fix-1031

Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp3`
Branch: `bot/mvp3-review-retry`
Start: `d624535` (Tester FAIL, Reviewer passed). Drop-in `abf7902` was already on the branch.
Rules: new commits only. No rebase, no amend, no force push, no merge, no PR.

## Items

B1. Cherry-picked `7bdede7` as `0f0d889` with `git cherry-pick -x`. The only conflicts were `docs/ops/*mvp-review-fix-1031.md`, removed with `git rm`. Cherry-picked `88ebcae` as `cb2f90e` the same way. Added the end-to-end test in `5553141`: the attempt writes a gitignored out-of-scope file and an in-scope fix, the ignored file stays on disk, the review body does not contain it, and the commit is only `src/calc.py`. Pushed.

B2. `d74975a`. A reviewer HTTP error exits 1 with `review-http-error` and does not commit. A review timeout exits 3 with `TIMEOUT` and does not commit. An empty diff is not sent to the reviewer (`review-empty-diff`, exit 1). Spent scope or wiring checks exit 1 with `PASS-REJECTED`. The previous diff reaches the retry prompt. `--no-review` does not retry a red gate. Pushed.

S6. `c4ff582`. `docs/ops/HANDOFF-mvp3-review-retry.md` line 3 says the review loop code lands on main after Tester and Reviewer PASS, with the local default staying NO-GO. The old "Do not merge from this run" line now says the same. Pushed.

T6. `ff3e802`. `eval/mvp3/REPORT.md` now says t6 ended at `2026-10-31T04:07:03Z`. Source: `finished_at` on `tmp/mvp3-runs/receipts/t6-tree-sig-three-L/receipt.json`. Pushed.

## Suite

`TMPDIR=$PWD/tmp flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .`

Ran 967 tests in 707.417s. FAILED (failures=1, skipped=16).

The one failure is `tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe`. `TMPDIR` is this worktree's `tmp/`, so the temp outdir is inside the repo and `log_path_for_receipt` returns a relative path. The mvp3 review-retry run log recorded the same failure. It is not from this fix.

`python3 -m unittest tests.test_pfy_build_local_review`: Ran 19 tests in 61.847s, OK.

Pregate was not run.

state: DONE
