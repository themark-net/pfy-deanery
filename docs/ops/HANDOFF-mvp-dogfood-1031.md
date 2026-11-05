# Handoff: mvp-dogfood-1031

Extra cloud lane. Branch `bot/mvp-dogfood-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-dogfood-1031`. Base `origin/bot/mvp-cloud-1031`, merged before each item. Exit: lane empty after 10 real cloud runs. No merge, no PR, no tag.

The product edits live only on throwaway `cloud/` branches inside `tmp/target-N`. Nothing from a target was pushed. This branch holds the report, the receipts, the checker, and these ops notes.

## Items done

| run | record | cloud commit | result |
| --- | --- | --- | --- |
| checker | 552147c |  | `check_reports.py` plus `tests/test_mvp_1031_dogfood_reports.py` |
| 01-stale-enterable | b08d603 | 8d29f5d | PASS exit 0 wall 39s review accept human yes |
| 02-enterable-test | 77fedac | none | FAIL exit 1 wall 343s tests-tampered human no |
| 03-t0110-status | 40d05c3 | 96224de | PASS exit 0 wall 46s review accept human yes |
| 04-pregate-latest | 411b9d6 | daa83e5 | PASS exit 0 wall 289s review accept human yes |
| 05-board-loaders | 6cd05a5 | 5e44ca0 | PASS exit 0 wall 133s review accept human yes |
| 06-digest-after-add | e5141f6 | 6c9db24 | PASS exit 0 wall 68s review accept human yes |
| 07-pregate-lock | 22aa6b5 | f7d00a2 | PASS exit 0 wall 94s review accept human yes |
| 08-board-loaders-next | d6b8819 | 51f4cd7 | PASS exit 0 wall 130s review accept human yes |
| 09-splice-close | 90d5113 | 24e73be | PASS exit 0 wall 85s review accept human yes |
| 10-board-loaders-rest | eefa37e | fe9ccc5 | PASS exit 0 wall 166s review accept human yes |

Rates: 10 runs, gate 9/10, review accept 9/10, human accept 9/10, median wall 112s. Detail is `eval/mvp-1031/dogfood/REPORT.md`.

Why each task was picked is in that run's `notes.md`. Short form: 01 dropped `next_steps` on the not-ok enterable path. 02 the behavior test that would lock it. 03 T-0110 still marked doing in two TODO cells. 04 pregate latest summary clobber. 05, 08, and 10 three slices of the copied board loader. 06 local-build digest moved to after `git add`. 07 pregate single-flight `flock -n`. 09 splice sockets closed after the pump threads join.

## Skipped

- New test files after run 02 (x148 present-but-unusable bwrap, lock-unittest asserts, tmp-cleanup private tmpdir). Run 02 used 3 attempts, all `tests-tampered`, no new information. A second one would be exit 5.
- ADR-0017. The two broken links need that ADR. OQ draft below. Not a dogfood task.
- A second T-0110 status edit. Run 03 already measured it.
- More `_load_*` copies after runs 05, 08, and 10. Same refactor, three PASS results. Not a new runner fact.
- Voice, catalog promotion, local models, hardware, and anything that needs `--local` or a secret.

Two of the 12 grok budget slots were not used.

## Test evidence

`nice -n 19 python3 eval/mvp-1031/dogfood/check_reports.py` prints `OK runs=10`.

`nice -n 19 python3 -m unittest tests.test_mvp_1031_dogfood_reports` is 7 tests, OK. The planted mismatch (PASS row vs FAIL receipt, wrong exit code, secret-like receipt, missing receipt, omitted run dir) makes the checker exit 1. The suite's stdout does not contain the planted secret value.

Receipts were grepped before each commit. No token, bearer, key, or auth value is in the committed receipts.

## How this fails and recovers

The checker fails when a run dir and the REPORT row disagree on status or exit code, when a run dir has no receipt, or when a receipt matches a secret-like pattern. Recover by fixing the row or redacting the receipt, then rerun the checker. A planted bad tree under the test temp dir is the fail case. It is not committed.

Run 02 fails closed: a new file under `tests/` is `tests-tampered` before the after-gate, on every attempt, and the worktree is deleted. There is no `cloud/` commit. The produced fix is saved as `eval/mvp-1031/dogfood/02-enterable-test/attempt.diff` and is not a commit. Recover by the cross-lane change below, then rerun a new-test task. This lane did not edit the runner.

The other nine runs fail if the throwaway gate stays red. The runner retries up to the default 3 attempts, then records FAIL and deletes the worktree. Those nine passed on attempt 1. A bad cloud commit is not pushed. Human accept is the recovery check: only run 02 is human no, because it has no commit.

## Cross-lane requests

mvp-cloud-1031, finding F1, severity high. `tests_tampered` rejects a path that was not in the base snapshot, so a task whose point is a new behavior test cannot PASS. Evidence: run 02, command in `eval/mvp-1031/dogfood/02-enterable-test/command.txt`, exit 1, receipt reason `tests-tampered`, attempts 1, 2, and 3 the same, `worktree_removed` true, no branch. Suggested fix, not applied: keep rejecting a base test that was edited or deleted, and stop rejecting a path that was not in the base snapshot. Update `test_changed_test_file_fails_before_the_gate` in the same change. Sketch: `eval/mvp-1031/dogfood/findings/F1-tests-tampered-new-file.md`.

## OQ draft

Not filed in `docs/OPEN_QUESTIONS.md` (that index is not this lane's file).

`docs/modules/pfylib.md` and `docs/modules/README.md` link to `docs/adr/0017-product-catalog-evaluation-handoff-harness.md`. That file is absent on this branch and on `origin/main`. Question: write the ADR, or retarget the two links at an existing doc? This lane did not choose.

## Gate

Pregate plus Reviewer. This branch changes eval, tests, and docs only. It does not change the runner or product code.

Pregate not run: host busy. At 2026-10-31T21:17:16Z `Runner.Worker` was live (pid 1974251) and `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` was held. This lane did not take the lock and did not signal that process.

## Next step

Do not merge this branch. Lane mvp-cloud-1031 applies F1 if Mark wants a new behavior test to be able to PASS. The throwaway `cloud/` commits are evidence of what the runner produced. They are not landed fixes. The caller checkout on this worktree was not switched or committed by any build.
