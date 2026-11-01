# Handoff: mvp-cloudfix-1031

Exit: no new findings for 60 minutes. Wave 4 superseded the earlier lane-empty state. The daily cloud runner on `bot/mvp-cloudfix-1031` meets the Functional MVP DoD and the failure-case table with behavior tests. The real high findings from the parallel lanes, including realfail2 and realfail3, are fixed on this branch. sixtask-int handed off GO with no cloud-runner request. Wall clock and host pressure did not fire. No question was asked. No merge, no PR, no tag.

Launch: 2026-10-31T20:30:10Z. Stop: 2026-11-01T00:20Z. This handoff is inside the wall cap (stop new items by 2026-11-01T04:10:10Z, wall 2026-11-01T04:30:10Z).

Integration order: merge `bot/mvp-cloudfix-1031` after `bot/mvp-cloud-1031` and `bot/mvp-preflight-1031`. This branch already contains the preflight merge `6c22fc7` and the integrate merge `da65338` (merge, not rebase). Do not merge it before those two, and do not merge it to main from this lane.

## Items done

| Item | SHA | Result |
|------|-----|--------|
| Loop exits before code | 8614547 | PASS, docs only |
| SIGKILL reap signals the live grok | 6dd9e63 | PASS, 44 tests OK, skipped 1 |
| DoD rows: retries, SIGINT, origin/main, staged caller, phrases | 9a7358f | PASS, 50 tests OK, skipped 1 |
| Merge preflight and call classify_cloud_failure | 6c22fc7 then 37d2a3a | PASS, 59 tests OK, skipped 1 |
| New test file reaches the gate (dogfood F1) | 9f1b6be | PASS, 53 tests OK, skipped 1 |
| Reject rm -rf / even when review accepts | eb13975 | PASS, 54 tests OK, skipped 1 |
| Not signed in is unauthenticated | fb71e1e | PASS, 63 tests OK, skipped 1 |
| Redact an xai- marker | e558bd5 | PASS, 56 tests OK, skipped 1 |
| Stage reviewed paths with :(literal) | 8c57694 | PASS, 57 tests OK, skipped 1 |
| --writable-test for one named base test (sixtask t4) | b06981d | PASS, 59 tests OK, skipped 1 |
| Archive recheck of a gitignored helper | ef0c845 | PASS, 60 tests OK, skipped 1 |
| Direct grok-home, .env, and pem are protected | 8a2a73b | PASS, 62 tests OK, skipped 1 |
| Two writable tests, a third still fails (sixtask t5) | 26b6d05 | PASS, 63 tests OK, skipped 1 |
| Bearer and API_TOKEN redaction | 1a4f067 | PASS, 63 tests OK, skipped 1 |
| Default gate command on dry-run | 469d285 | PASS, 63 tests OK, skipped 1 |
| PASS does not push to a bare origin | 61d539a | PASS, 64 tests OK, skipped 1 |
| Wave 4 exit card | 848411c | PASS, docs only |
| Merge origin/bot/mvp-integrate-1031 | da65338 | PASS, 64 tests OK, skipped 1 |
| Missing base is worktree-failed | 3ee4819 | PASS, 65 tests OK, skipped 1 |
| Every terminal failure has a recovery line | 827b4b0 | PASS, 66 tests OK, skipped 1 |
| Unwritable tmp is worktree-failed | 7276eee | PASS, 67 tests OK, skipped 1 |
| Hung gate is timeout | 8bcb06e | PASS, 68 tests OK, skipped 1 |

Doc commits that record those SHAs include af303d5, 570eb6f, b397eee, 0c62a90, cb7c584, c5cb343, 67a5a5f, 16440e6, 763deb2, 57c6dad, f316036, 10877ad, 39607b8, 3ef85f2, 02758f0, fdfd205, 9e637ce, 90d3c6e, 9ca171b, d78ed00, 0dfc9d1, 8047018. The drop-in commit is 18fa22d. This handoff commit is the last one.

Real-run receipts (before is on the other lane, cited, not copied; after is gitignored under this worktree):

- sigkill-reap before `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/sigkill-reap/receipt.json`. After `tmp/sigkill-after/receipt.json`.
- F1 before `origin/bot/mvp-dogfood-1031:eval/mvp-1031/dogfood/02-enterable-test/receipt.json`. After `tmp/f1-after/receipt.json` (commit 0693d66).
- review-reject before `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/review-reject/receipt.json` (commit 9accbc1). After `tmp/danger-after/receipt.json`.
- auth-failure before `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/auth-failure/receipt.json`. After `tmp/auth-after/receipt.json`.
- redaction before `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/redaction/receipt.json`. After `tmp/redact-after/receipt.json` (commit 597ac75).
- writable-test before `origin/bot/mvp-sixtask-1031:eval/mvp-1031/sixtask/t4-timeout-substep/receipt.json`. After `tmp/writable-after/receipt.json` (commit 25f9e2a).
- t5 before `origin/bot/mvp-sixtask-1031:eval/mvp-1031/sixtask/t5-receipts-outside-repo/receipt.json`. No second grok run. The two-file lock is 26b6d05.
- missing base before `origin/bot/mvp-realfail2-1031:eval/mvp-1031/realfail2/worktree-failed/` (usage text, exit 2, no receipt). After `tmp/base-missing-after/receipt.json` (FAIL worktree-failed, exit 1). Grok was not called.
- protected-path empty recovery before `origin/bot/mvp-realfail2-1031:eval/mvp-1031/realfail2/protected-paths/receipt.json`. No second grok. The fake grok test locks the recovery line.
- tmp-unwritable before `origin/bot/mvp-realfail3-1031:eval/mvp-1031/realfail3/tmp-unwritable/receipt.json` (runner-crash, recovery empty). After `tmp/tmp-unwritable-after/receipt.json` (FAIL worktree-failed, exit 1). Grok was not called.
- gate-hang before `origin/bot/mvp-realfail3-1031:eval/mvp-1031/realfail3/gate-hang/receipt.json` (FAIL tests, exit 1, after-gate exit 124). After `tmp/gate-hang-after/receipt.json` (TIMEOUT timeout, exit 3). One real grok call.

## Skipped

- Sixtask t5 real grok repro. Same tests-tampered gap as t4, which already has an after receipt. The two-file behavior test locks the extra shape.
- Selfhost symlink run on `origin/bot/mvp-selfhost-1031` (`eval/selfhost-1031/03-tree-sig-symlink`). Runner exit 0, review accept. The human reject is about the diff content, so this lane did not change the runner.
- Moving `Not signed in` into `pfylib/build_preflight.py`. That module is read-only here after the merge. The runner maps the phrase after `classify_cloud_failure` returns other. `auth.json` on a zero exit stays other.
- Operator card, eval checker, and local-runner files. Other lanes own them. `scripts/pfy` was not edited. `--writable-test` is on the cloud argparse, so `./pfy build --help` shows it.
- A new `base-missing` reason. The addendum allows `base-missing` or `worktree-failed`. This lane uses `worktree-failed`, which already matches the DoD row.
- Empty recovery on unwritable tmp. The FINDING asked for an empty line. Wave 4 requires every failure reason to have a recovery line, so the receipt tells Mark to make tmp writable.
- realfail3 notes that the handoff marked as not requests: a PASS over the local size cap, a red before-gate that still calls grok when `tests/` is missing, and a network shim recorded as `no-change`. Not fixed here.
- Live grok for missing-base, protected-path, and unwritable tmp. Those paths return before grok starts.
- Pregate not run. At 2026-11-01T00:20Z `Runner.Worker` was idle, and pid 65479 already held `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` running `./scripts/pregate.sh 1f3b1a3`. One pregate per host. This lane did not queue a second.
- No ADR. No open question blocked a fit item. No secret was read.

## Test evidence

Latest code run, niced, fake grok, scratch under this worktree's `tmp/`:

`nice -n 19 python3 -m unittest tests.test_pfy_build_cloud tests.test_pfy_build_p`

68 tests, OK, 1 skipped, about 14s, at commit 8bcb06e (2026-10-31T23:18Z). The skipped test is the dogfood module's existing skip. The line `FAIL: grok not on PATH` is that module's expected missing-grok message, not a failure. The `FAIL: <reason>` lines during the suite are the recovery-walk test writing receipts, not failures.

Later commits are docs only. `tests/test_pfy_build_p.py` and `pfylib/build_preflight.py` were not edited. The runner does not read `auth.json` and does not call a local model.

The hung-gate test was red before the fix (exit 1, reason `tests`) and green after (exit 3, reason `timeout`).

## How each change fails and recovers

- SIGKILL: if the pid file still holds the dead gate, reap leaves the live grok. Recovery is `--reap` after the pid file holds the grok pgid. It SIGTERMs then SIGKILLs that group and writes ABORTED / no-receipt. A pgid listed only in the local pid file is not signaled. A live recorded runner pid is left alone.
- New test file: a path absent from the base snapshot is not `tests-tampered`. If that new test still fails the gate, the reason is `tests` and the next prompt gets the gate tail. An edited or deleted base test that is not named by `--writable-test` is still `tests-tampered` before the after-gate, with no branch.
- Review reject of a root delete: a diff that contains `rm -rf /` or `rm -fr /` cannot PASS even when the model prints accept. Three attempts, reason `review-rejected`, no branch. `--no-review` hits the same check once.
- Auth: `Not signed in` on exit 0 or 1 is `unauthenticated`. Recovery tells Mark to run grok once and rerun the same `./pfy build` task. It does not suggest `--local` and it does not create `auth.json`.
- Redaction: AKIA, a bearer value, an `API_TOKEN=` assignment, `sk_` plus 8 characters, a private-key block, and `xai-` plus 6 characters become `[redacted]` in the receipt. The build can still PASS. The committed file is not rewritten by redact.
- Literal pathspec: a reviewed name is not a wildcard. A file named `*` commits, and a pyc beside it does not. If the staged set still differs, reason `scope-commit-mismatch`, the index is reset, and there is no branch.
- Writable test: without the flag, editing a committed test is `tests-tampered` on every attempt. With one or two `--writable-test` paths, those files may change and land. A base test that is not named still fails, and a later attempt that restores it can land.
- Archive recheck: a commit that passes only because a gitignored helper is in the worktree is reset with `git reset --hard HEAD~1`. Reason `commit-recheck-failed`. The gate tail feeds the next attempt. The branch is created only after the fresh extract passes. A later attempt that does not need the helper can PASS with one surviving commit. If that recheck gate times out, the commit is reset and the receipt is TIMEOUT / timeout / exit 3, not `commit-recheck-failed`.
- Protect globs: `auth.json`, `.env`, `*.pem`, and `pipelines/dogfood/**/grok-home/**` (including a direct `pipelines/dogfood/grok-home/` path, because `**` matches zero directories) are `protected-path-changed` and are not committed. Recovery names the path. A later attempt that deletes them can land the real file.
- No push: a PASS writes the local `cloud/` branch and sets `pushed` false. A bare origin stays empty.
- Missing base: a `--base` ref that is not in the repo is `worktree-failed`, exit 1, not usage exit 2. Recovery tells Mark to fetch or pass `--base`. The caller checkout is not changed. Dry-run of a missing base fails the same way and does not start grok. A missing task and a missing repo stay usage exit 2.
- Recovery fill: `finish()` writes a non-empty recovery for every terminal failure when the caller left it blank. PASS and DRY-RUN stay empty. `other` from `classify_cloud_failure` is not a failure. Rate-limit keeps `./pfy build --local <task>`. Auth does not suggest `--local`.
- Unwritable tmp: if `tmp/cloud-build` or the worktree `tmp/` cannot be created, the reason is `worktree-failed`, exit 1. Recovery tells Mark to make the repo tmp directory writable and rerun. Grok is not called. The caller HEAD and porcelain stay as they were.
- Hung gate: a before-gate, after-gate, second gate, or recheck that hits `--timeout` is TIMEOUT / timeout / exit 3. The runner does not record `tests`, does not commit, and does not start another attempt. Recovery says the gate timed out and tells Mark to rerun with a longer `--timeout`. An implement or review grok timeout keeps the grok sentence (`grok timed out`, larger `--timeout`). A normal non-zero gate stays `tests`, `tests-flaky`, or `commit-recheck-failed`.

## Cross-lane requests

- mvp-integrate-1031: merge `bot/mvp-cloudfix-1031` after `bot/mvp-cloud-1031` and `bot/mvp-preflight-1031`. This branch already contains both of those merges. The demo and `check_receipt.py` stay on the integrate lane. This handoff is not a Feature GO.
- mvp-preflight-1031: absorb `not signed in` (including exit 0) into `classify_cloud_failure`. Leave `auth.json` on the non-zero path so a successful reply that names the file stays other. This lane did not edit that module.
- mvp-realfail-1031: the four FINDINGs can be rerun against this branch: sigkill-reap, review-reject, auth-failure, redaction.
- mvp-realfail2-1031: missing `--base` is now `worktree-failed` exit 1 with a recovery line. `protected-path-changed` recovery is non-empty and names the path.
- mvp-realfail3-1031: rerun `tmp-unwritable` and `gate-hang` against this branch. Expected: worktree-failed exit 1 with a writable-tmp line, and TIMEOUT timeout exit 3 with a longer `--timeout` line. The over-cap PASS, the red before-gate that still calls grok, and the network `no-change` were not requests and are not changed here.
- mvp-dogfood-1031: F1 is fixed here. A new test file can reach the gate and land. An edit or delete of a base test still fails unless `--writable-test` names it.
- mvp-sixtask-1031: t4 and t5 need `--writable-test` for each existing test file the task is allowed to edit. The flag is repeatable. A test file that is not named still fails. Their report's NO-GO is that missing flag on the old cloud base. This lane did not edit their eval files.
- mvp-sixtask-int-1031: no request. `eval/mvp-1031/sixtask-int/REPORT.md` on `d642ec1` is GO, twelve receipts PASS, review on. This lane did not edit those files.
- mvp-dogfood2-1031: that lane merged this branch through `8047018` at `b90ae61`. Later docs commits are not in that merge. No request back.
- mvp-surface-1031: the operator card stays in that lane's files. This lane did not write `docs/modules/` or `docs/ops/pfy-build-daily.md`.
- mvp-review-fix-1031: local G4 and G5 were mirrored here without `git add -A -f`. The local runner was not edited.

## Gate

Tester plus Reviewer. This is a runtime change (`scripts/pfy_build_cloud.py` and `tests/test_pfy_build_cloud.py`). `scripts/pfy` was not edited in this lane.

Pregate was not run. `Runner.Worker` was idle at the stop, and another pregate already held the heavy lock. See Skipped.

## Next step

Stop this lane. When integrate collects branches, merge this one after cloud and preflight. realfail3 can rerun tmp-unwritable and gate-hang. Do not merge to main from here.
