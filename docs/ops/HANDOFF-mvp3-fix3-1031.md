# Handoff: mvp3-fix3-1031

Branch `bot/mvp3-review-retry`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp3`. Base for this lane is `16f17d8`, plus the drop-in `0e683b9`. No rebase, no amend, no force push, no merge, no PR.

The code tip before this handoff is `0d3c0fcf1c09d9417cf61b9e7b41177c488f2d99`. BX3 is `3a550e53ea495cbdbc53ef11969d3dc792093bef`. P10 is `0d3c0fcf1c09d9417cf61b9e7b41177c488f2d99`. This file's commit is the lane tip when it is pushed. A commit cannot hold its own SHA. Read `git rev-parse HEAD` on this branch after the push.

Tester FAIL on `16f17d8` (BX3) is answered on this branch. The local default stays NO-GO. The review loop lands on main after Tester and Reviewer PASS.

## Item commits

| Item | Commit | What landed |
|------|--------|-------------|
| BX3 | `3a550e53ea495cbdbc53ef11969d3dc792093bef` | A diff over 8000 characters fails closed as `review-diff-too-large`. A tracked binary change fails closed as `review-binary-change`. The reviewer is not called, nothing is committed, and the run does not retry. The reviewer prompt no longer slices the diff |
| P10 | `0d3c0fcf1c09d9417cf61b9e7b41177c488f2d99` | A tracked edit of `src/café.py` shows `diff --git a/src/café.py b/src/café.py` in the reviewer prompt. The quoted octal path is absent |
| Docs | this commit | `docs/ops/HANDOFF-mvp3-fix2-1031.md` names tip `16f17d8` and the counts 1014 and 99. This handoff and the run log |

## How it fails and how to recover

| Fail | What you see | Recovery |
|------|----------------|----------|
| Diff longer than 8000 characters | Exit 1, reason `review-diff-too-large`, one attempt, no branch | Shrink the change and run again. The line cap can still say the diff is under 250 lines. The diff is not cut to fit |
| Tracked binary change | Exit 1, reason `review-binary-change`, one attempt, no branch | Leave the binary out and run again. Git shows `Binary files differ` and counts those lines as 0. A new file whose bytes are shown as text is not this case |
| Quoted non-ASCII path | The prompt would contain `"a/src/caf\303\251.py"` | The review diff sets `core.quotepath=false`. A tracked edit must show the literal path |

## Suite

Command: `TMPDIR=$PWD/tmp flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .`

Targeted before the full suite: `tests.test_pfy_build_local_review` 41 OK in 87.678s at BX3, then the P10 test OK in 1.127s. That module is 42 tests. `tests.test_pfy_build_local` is unchanged at 61. Together that is 103. With the quotepath flag removed, the P10 test failed and `test_unicode_path_in_scope_is_committed` still passed. The runner was restored before the commit.

Full suite: Ran 1018 tests in 743.334s. FAILED (failures=1, skipped=16). The failure is `tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe`. `TMPDIR` is inside this repo, so the helper returns a relative log path. The same environmental failure is in the mvp3-fix-1031 handoff and in the `d168446` run. This lane does not change that helper. `tests.test_hedge.DetectorTests.test_detector_runs_offline` did not fail in this run.

Pregate was not run. The operator runs it.

## Open

No code item is open. Pregate is the operator's run. No real `--local` model trial was run.
