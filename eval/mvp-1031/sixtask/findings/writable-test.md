# Finding: tests-tampered blocks MVP-2 tasks that must edit tests

For lane mvp-cloud-1031. Do not apply this from the sixtask lane. The runner files are not ours.

## What happened

`./pfy build` with review on (default `--retries` 2, so 3 attempts) rejects any edit under `tests/` as `tests-tampered` before review and before a commit. There is no `--writable-test` flag. The local runner has that flag. MVP-2 t4 and t5 require those edits.

The produced diffs are the right fixes. The canonical MVP-2 gate, re-run on the kept worktree with the planted acceptance test restored if needed, exited 0 for both. The runner still exited 1, wrote no branch, and never called review.

## t4 command

```text
./pfy build "<eval/mvp2/tasks/t4-timeout-substep.md>" \
  --repo tmp/sixtask-clones/pass1/t4-timeout-substep \
  --base demo-base \
  --test-cmd "python3 -m unittest tests.test_mvp2_t4_timeout_step tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_timeout_reason_is_shared_text tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_festival_timeout_reason_is_shared_text tests.test_x_intake_smoke_112_114.XIntakeSmoke112114Tests.test_overtime_daemon_stop_timeout_uses_shared_text" \
  --receipt-dir eval/mvp-1031/sixtask/t4-timeout-substep \
  --timeout 900 \
  --keep-worktree
```

Exit code: 1. Wall: 1439.7 s. Attempts: 3.

Receipt excerpt (`eval/mvp-1031/sixtask/t4-timeout-substep/receipt.json`):

```json
"status": "FAIL",
"reason": "tests-tampered",
"exit_code": 1,
"branch": null,
"commit": null,
"review": {"verdict": null, "reasons": []}
```

Each attempt row is `status` `FAIL`, `reason` `tests-tampered`. The smoke diff matches `eval/mvp2/patches/t4-timeout-substep-C.patch` on `examples/x-intake-local/smoke_112_114.py`. The only test edit is the two assertion strings the task allows.

## t5 command

```text
./pfy build "<eval/mvp2/tasks/t5-receipts-outside-repo.md>" \
  --repo tmp/sixtask-clones/pass1/t5-receipts-outside-repo \
  --base demo-base \
  --test-cmd "python3 -m unittest tests.test_mvp2_t5_receipts" \
  --receipt-dir eval/mvp-1031/sixtask/t5-receipts-outside-repo \
  --timeout 900 \
  --keep-worktree
```

Exit code: 1. Wall: 707.7 s. Attempts: 3. Same receipt shape: `status` `FAIL`, `reason` `tests-tampered`, `commit` null, review verdict null.

The diff only changes `tests/test_x_intake_smoke_117_118.py` and `tests/test_x_intake_smoke_119_121.py`. Both set `PFY_SMOKE_RECEIPT_DIR` from `setUp` and read the receipt from that temp dir. Smoke scripts were not edited.

## Suggested fix

`findings/writable-test.patch` (against `scripts/pfy_build_cloud.py` on this lane's merged cloud base).

- Add repeatable `--writable-test GLOB`. Default is an empty list, so today's tests that expect `tests-tampered` stay red when a test file changes.
- `tests_tampered` gains an optional `writable` argument and skips paths that match those globs, including a new test file that matches.
- The call site passes `args.writable_test`.

Cloud lane should add a behavior test: with the flag, an allowed test edit can reach review and commit; without the flag, the same edit is still `tests-tampered` and no branch is created. Do not weaken the default.

## How this fails and recovers

Fail: a task that must change a named test file spends three grok attempts and exits 1 with no commit, even when the canonical gate is green. Recover: rerun with `--writable-test` set to that file once the flag exists. Until then, Mark does not get a commit for t4 or t5 from `./pfy build`.

## Retries 0 reproduction

A later pass used `--retries 0` (one attempt, review still on, no `--no-review`). Same reject, sooner.

t4: exit 1, wall 229.7 s, attempts 1, reason `tests-tampered`, commit null, review verdict null. Canonical gate rerun 0. Receipt: `eval/mvp-1031/sixtask/retries0/t4-timeout-substep/receipt.json`. The diff still names the `new` and `version` sub-steps and changes only the two allowed assertion strings.

t5: exit 1, wall 108.9 s, attempts 1, reason `tests-tampered`, commit null, review verdict null. Canonical gate rerun 0. Receipt: `eval/mvp-1031/sixtask/retries0/t5-receipts-outside-repo/receipt.json`. The diff is only the two allowed test modules, both setting `PFY_SMOKE_RECEIPT_DIR`.

Attempts 2 and 3 on the earlier passes did not turn either reject into a commit. The retry budget is not a workaround.
