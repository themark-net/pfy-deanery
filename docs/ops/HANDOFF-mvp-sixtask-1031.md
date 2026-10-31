# Handoff: mvp-sixtask-1031

Exit: lane empty. The six-task trial, the variance pass, and the `--retries 0` pass are recorded. Wall clock and host pressure did not fire. No question was asked. No merge, no PR, no tag.

Launch: 2026-10-31T20:16:38Z. This handoff is inside the wall cap (no new item after 2026-11-01T03:56:38Z). Branch `bot/mvp-sixtask-1031`. Evidence pin for pregate: `4271dcb`. The commit that adds this file is docs-only.

Verdict: NO-GO for cloud-default `./pfy build` as Mark's daily build command. The bar is MVP-2's 6/6 gate and 6/6 review accept. Three real-grok passes stayed at 4/6 runner PASS and 4/6 review accept. Detail: `eval/mvp-1031/sixtask/REPORT.md`.

## Items done

Evidence SHAs are the ones in the run log. The following commit on the branch is the log-line commit.

| Item | SHA | Result |
|------|-----|--------|
| Loop exits before any trial | 42d6952 | PASS |
| Merge `origin/bot/mvp-cloud-1031` | d0adb75 | PASS, runner still has no `--writable-test` |
| Report checker and one-task harness | 3d1b2bf | 8 tests OK, 1 skipped |
| Pass 1 t1 | 7eb77e7 | PASS, 211.2 s, review accept |
| Pass 1 t2 | 9cf7a7c | PASS, 66.3 s, review accept |
| Pass 1 t3 | f0f11eb | PASS, 259.7 s, review accept |
| Pass 1 t4 | 58a178f | FINDING, tests-tampered, 1439.7 s, 3 attempts |
| Pass 1 t5 | 306f703 | FINDING, tests-tampered, 707.7 s, 3 attempts |
| Pass 1 t6 | f5ca6ac | PASS, 93.4 s, review accept |
| Pass 1 report | e662d04 | NO-GO, 2778.0 s |
| Variance t1 | 486350a | PASS, 130.2 s |
| Variance t2 | 62a19f5 | PASS, 51.1 s |
| Variance t3 | 0b700a3 | PASS, 225.8 s |
| Variance t4 | 638afc1 | FINDING, tests-tampered, 999.4 s, 3 attempts |
| Variance t5 | 8db3035 | FINDING, tests-tampered, 839.0 s, 3 attempts |
| Variance t6 | c19212a | PASS, 110.5 s |
| Variance report | 96dd2a5 | same 4/6 class, 2356.0 s |
| Retries 0 t1 | 5d2c362 | PASS, 174.7 s, one attempt, review on |
| Retries 0 t2 | 07f65e8 | PASS, 58.7 s |
| Retries 0 t3 | 8932ae3 | PASS, 253.5 s |
| Retries 0 t4 | 056a462 | FINDING, tests-tampered, 229.7 s, 1 attempt |
| Retries 0 t5 | 3e2d843 | FINDING, tests-tampered, 108.9 s, 1 attempt |
| Retries 0 t6 | 7613bdc | PASS, 118.8 s |
| Retries 0 report | 627d8d7 | same 4/6 class, 944.3 s, 10 tests OK |

Pass totals (checker-verified):

| Pass | Runner PASS | Canonical gate | Review accept | Human accept | Wall_s | Attempts |
|------|-------------|----------------|---------------|--------------|--------|----------|
| Pass 1 | 4/6 | 6/6 | 4/6 | 6/6 | 2778.0 | 10 |
| Variance | 4/6 | 6/6 | 4/6 | 6/6 | 2356.0 | 10 |
| `--retries 0` | 4/6 | 6/6 | 4/6 | 6/6 | 944.3 | 6 |

MVP-2 cloud baseline was 6/6 gate, 6/6 accept, 583.6 s. MVP-3 local was 5/6 gate, 5/6 loop, 4/6 human, 3859.9 s.

The four code-only tasks (t1, t2, t3, t6) passed on attempt 1 in every pass. t4 and t5 produced diffs a human accepts, and the canonical gate rerun exited 0, but the runner exited 1 with reason `tests-tampered`, wrote no branch, and never called review. Attempts 2 and 3 did not change that. `--retries 0` still runs review for a passing attempt. It was not `--no-review`.

## Skipped

- No task was skipped. No item needed a secret, special hardware, or Mark's hands.
- The runner was not patched. `scripts/pfy_build_cloud.py`, `scripts/pfy`, and `tests/test_pfy_build_cloud.py` were not edited. The suggested patch stays at `eval/mvp-1031/sixtask/findings/writable-test.patch`.
- `docs/TODO.md` and `docs/PENDING-HANDOFF.md` were not edited.
- No local model. No `--local`.
- No ADR and no OQ draft. `--writable-test` already exists on the local runner. Asking the cloud lane to add the same opt-in is a cross-lane request, not a new architecture.

## Test evidence

Targeted, niced, scratch under this worktree's `tmp/`:

- `nice -n 19 python3 -m unittest tests.test_mvp_1031_sixtask_report` at the retries 0 report: 10 tests, OK, about 0.002 s. The live pass-1 report, the variance report, and the retries 0 report all match their receipts. Planted status, totals, and missing-receipt cases fail in a temp dir.
- Each task's canonical MVP-2 gate was re-run by `eval/mvp-1031/sixtask/run_task.py` with a fake HOME under `tmp/scratch`. `gate_rerun.exit` is 0 for all 18 task runs. `acceptance_unchanged` is true.

## How a change fails and how it recovers

- Report checker: a row whose status, exit, or attempt count disagrees with `receipt.json`, or a totals line that is not the sum, makes `check_report` return errors and the unittest fail. Recover: fix the cell or the receipt, then re-run that module. The planted mismatch in a temp dir is the fail case. It does not touch the live reports.
- Harness: `build_argv` raises if `--local` or `--no-review` is present. `--retries 0` stays on the argv and review stays on. Recover: drop the banned flag and rerun the one task.
- Secret scan: a token-shaped match is counted and replaced with `[redacted]` in the receipt and the diff before they are kept. The matched text is not printed. Recover: scan again and commit only when the count is 0. Every committed artifact in this lane scanned at 0.
- Trial gap: a correct `tests/` edit is rejected as `tests-tampered` before review. Recover, once the cloud lane lands the flag: rerun t4 and t5 with `--writable-test` pointed at the files the task allows. Until then, `./pfy build` does not commit those tasks. This lane did not apply that patch.

## Cross-lane requests

For lane mvp-cloud-1031:

Add repeatable `--writable-test GLOB`, default empty, so an allowed test edit can reach review and a commit, and the same edit without the flag is still `tests-tampered` with no branch. Behavior test belongs on that lane. Patch and write-up: `eval/mvp-1031/sixtask/findings/writable-test.patch` and `eval/mvp-1031/sixtask/findings/writable-test.md`.

Reproduced three times. Do not treat a later retry as a fix.

- Pass 1 t4: `./pfy build` on `eval/mvp2/tasks/t4-timeout-substep.md`, `--repo tmp/sixtask-clones/pass1/t4-timeout-substep`, `--base demo-base`, the MVP-2 t4 gate as `--test-cmd`, `--timeout 900`, `--keep-worktree`. Exit 1. Wall 1439.7 s. Attempts 3. Receipt `status` `FAIL`, `reason` `tests-tampered`, `exit_code` 1, `branch` null, `commit` null, review verdict null.
- Pass 1 t5: same shape, task `t5-receipts-outside-repo.md`, gate `python3 -m unittest tests.test_mvp2_t5_receipts`. Exit 1. Wall 707.7 s. Attempts 3. Same receipt shape.
- Variance t4 and t5: exit 1, 999.4 s and 839.0 s, 3 attempts, same reason.
- `--retries 0` t4 and t5: exit 1, 229.7 s and 108.9 s, 1 attempt, same reason. The extra attempts bought no commit.

## Gate

This lane is eval and test only. Gate: pregate plus Reviewer on the handoff commit. No runtime change, so Tester is not the gate. No PR was opened.

Pregate not run: host busy. At 2026-10-31T22:27:54Z `pgrep -f 'Runner[.]Worker'` was empty, so this lane queued `nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock ./scripts/pregate.sh 4271dcb`. The flock had not started `pregate.sh`. At 2026-10-31T22:45:11Z the GitHub runner was up (pid 3199955) and the lock was held by another lane's pregate on `0c3f133`, with more heavy jobs ahead. This lane's waiting flock was stopped. The other lanes' processes were left running.

## Next step

Cloud lane lands `--writable-test` and its behavior test, then someone re-runs t4 and t5 through `./pfy build` with that flag and review on. Cloud-default `./pfy build` stays NO-GO as the daily command until those two tasks get a review accept, not only a canonical gate pass.
