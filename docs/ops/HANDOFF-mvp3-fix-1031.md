# Handoff: mvp3-fix-1031

Branch `bot/mvp3-review-retry`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp3`. The tip is the commit that adds this file. Its parent is `ff3e802`.

Tester FAIL on `d624535` is answered on this branch. No rebase, no amend, no force push, no merge, no PR.

## Item commits

- B1 `0f0d889`: cherry-pick of `7bdede7` (stage only reviewed paths). Doc conflicts were removed.
- No-change gate `cb2f90e`: cherry-pick of `88ebcae` (a no-change attempt runs the gate and does not call the reviewer). Doc conflicts were removed. Stage-only reviewed paths is B1 `0f0d889`.
- B1 `5553141`: end-to-end test. The attempt writes a gitignored out-of-scope file and an in-scope fix. The file stays on disk, the review body never sees it, and the commit contains only `src/calc.py`.
- B2 `d74975a`: the review fails closed. HTTP error: exit 1, reason `review-http-error`, no commit. Review timeout: exit 3, status `TIMEOUT`, no commit. Empty diff: exit 1, reason `review-empty-diff`, the reviewer is not called, no commit. Scope or wiring retries spent: exit 1, status `PASS-REJECTED`, no commit. The previous diff is in the retry prompt. `--no-review` does not retry a red gate.
- S6 `c4ff582`: `docs/ops/HANDOFF-mvp3-review-retry.md` line 3 says the review loop code lands on main after Tester and Reviewer PASS, with the local default staying NO-GO. The old "Do not merge from this run" line matches that.
- T6 `ff3e802`: t6 ended at `2026-10-31T04:07:03Z`. Source is `finished_at` on the t6 receipt under `tmp/mvp3-runs/receipts/t6-tree-sig-three-L/receipt.json`.

## Suite

Command: `TMPDIR=$PWD/tmp flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .`

Ran 967 tests in 707.417s. FAILED (failures=1, skipped=16).

The failure is `tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe`. The required `TMPDIR` is inside the repo, so the temp outdir is in-tree and the helper returns a relative path. The mvp3 review-retry run log has the same environmental failure. These commits do not touch that helper.

`python3 -m unittest tests.test_pfy_build_local_review` passed: 19 tests, 61.847s.

## Open

No item is open. B1, B2, S6, and T6 are pushed. Pregate was not run. The operator runs it at this tip.

The local default stays NO-GO. The review loop code lands on main after Tester and Reviewer PASS.
