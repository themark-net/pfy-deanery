# Handoff: mvp-cloudfix-1031

Exit: lane empty. The daily cloud runner on `bot/mvp-cloudfix-1031` meets the Functional MVP DoD and the failure-case table with behavior tests, and the real high findings from the parallel lanes are fixed on this branch. Wall clock and host pressure did not fire. No question was asked. No merge, no PR, no tag.

Launch: 2026-10-31T20:30:10Z. This handoff is inside the wall cap (stop new items by 2026-11-01T04:10:10Z, wall 2026-11-01T04:30:10Z).

Integration order: merge `bot/mvp-cloudfix-1031` after `bot/mvp-cloud-1031` and `bot/mvp-preflight-1031`. This branch already contains the preflight merge `6c22fc7`. Do not merge it before those two, and do not merge it to main from this lane.

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

Doc commits that record those SHAs: af303d5, 570eb6f, b397eee, 0c62a90, cb7c584, c5cb343, 67a5a5f, 16440e6, 763deb2, 57c6dad, f316036, 10877ad, 39607b8, 3ef85f2, 02758f0. The drop-in commit is 18fa22d.

Real-run receipts (before is on the other lane, cited, not copied; after is gitignored under this worktree):

- sigkill-reap before `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/sigkill-reap/receipt.json`. After `tmp/sigkill-after/receipt.json`.
- F1 before `origin/bot/mvp-dogfood-1031:eval/mvp-1031/dogfood/02-enterable-test/receipt.json`. After `tmp/f1-after/receipt.json` (commit 0693d66).
- review-reject before `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/review-reject/receipt.json` (commit 9accbc1). After `tmp/danger-after/receipt.json`.
- auth-failure before `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/auth-failure/receipt.json`. After `tmp/auth-after/receipt.json`.
- redaction before `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/redaction/receipt.json`. After `tmp/redact-after/receipt.json` (commit 597ac75).
- writable-test before `origin/bot/mvp-sixtask-1031:eval/mvp-1031/sixtask/t4-timeout-substep/receipt.json`. After `tmp/writable-after/receipt.json` (commit 25f9e2a).
- t5 before `origin/bot/mvp-sixtask-1031:eval/mvp-1031/sixtask/t5-receipts-outside-repo/receipt.json`. No second grok run. The two-file lock is 26b6d05.

## Skipped

- Sixtask t5 real grok repro. Same tests-tampered gap as t4, which already has an after receipt. The two-file behavior test locks the extra shape.
- Selfhost symlink run on `origin/bot/mvp-selfhost-1031` (`eval/selfhost-1031/03-tree-sig-symlink`). Runner exit 0, review accept. The human reject is about the diff content, so this lane did not change the runner.
- Moving `Not signed in` into `pfylib/build_preflight.py`. That module is read-only here after the merge. The runner maps the phrase after `classify_cloud_failure` returns other. `auth.json` on a zero exit stays other.
- Operator card, eval checker, and local-runner files. Other lanes own them. `scripts/pfy` was not edited. `--writable-test` is on the cloud argparse, so `./pfy build --help` shows it.
- Pregate not run: host busy. `pgrep -f 'Runner[.]Worker'` matched pid 2242260 at 2026-10-31T21:25:20Z.
- No ADR. No open question blocked a fit item. No secret was read.

## Test evidence

Latest full run, niced, fake grok, scratch under this worktree's `tmp/`:

`nice -n 19 python3 -m unittest tests.test_pfy_build_cloud tests.test_pfy_build_p`

64 tests, OK, 1 skipped, about 11s, at commit 61d539a (2026-10-31T21:24Z). The skipped test is the dogfood module's existing skip. The line `FAIL: grok not on PATH` is that module's expected missing-grok message, not a failure.

`tests/test_pfy_build_p.py` and `pfylib/build_preflight.py` were not edited. The runner does not read `auth.json` and does not call a local model.

## How each change fails and recovers

- SIGKILL: if the pid file still holds the dead gate, reap leaves the live grok. Recovery is `--reap` after the pid file holds the grok pgid. It SIGTERMs then SIGKILLs that group and writes ABORTED / no-receipt. A pgid listed only in the local pid file is not signaled. A live recorded runner pid is left alone.
- New test file: a path absent from the base snapshot is not `tests-tampered`. If that new test still fails the gate, the reason is `tests` and the next prompt gets the gate tail. An edited or deleted base test that is not named by `--writable-test` is still `tests-tampered` before the after-gate, with no branch.
- Review reject of a root delete: a diff that contains `rm -rf /` or `rm -fr /` cannot PASS even when the model prints accept. Three attempts, reason `review-rejected`, no branch. `--no-review` hits the same check once.
- Auth: `Not signed in` on exit 0 or 1 is `unauthenticated`. Recovery tells Mark to run grok once and rerun the same `./pfy build` task. It does not suggest `--local` and it does not create `auth.json`.
- Redaction: AKIA, a bearer value, an `API_TOKEN=` assignment, `sk_` plus 8 characters, a private-key block, and `xai-` plus 6 characters become `[redacted]` in the receipt. The build can still PASS. The committed file is not rewritten by redact.
- Literal pathspec: a reviewed name is not a wildcard. A file named `*` commits, and a pyc beside it does not. If the staged set still differs, reason `scope-commit-mismatch`, the index is reset, and there is no branch.
- Writable test: without the flag, editing a committed test is `tests-tampered` on every attempt. With one or two `--writable-test` paths, those files may change and land. A base test that is not named still fails, and a later attempt that restores it can land.
- Archive recheck: a commit that passes only because a gitignored helper is in the worktree is reset with `git reset --hard HEAD~1`. Reason `commit-recheck-failed`. The gate tail feeds the next attempt. The branch is created only after the fresh extract passes. A later attempt that does not need the helper can PASS with one surviving commit.
- Protect globs: `auth.json`, `.env`, `*.pem`, and `pipelines/dogfood/**/grok-home/**` (including a direct `pipelines/dogfood/grok-home/` path, because `**` matches zero directories) are `protected-path-changed` and are not committed. A later attempt that deletes them can land the real file.
- No push: a PASS writes the local `cloud/` branch and sets `pushed` false. A bare origin stays empty.

## Cross-lane requests

- mvp-integrate-1031: merge `bot/mvp-cloudfix-1031` after `bot/mvp-cloud-1031` and `bot/mvp-preflight-1031`. The demo and `check_receipt.py` stay on the integrate lane. This handoff is not a Feature GO.
- mvp-preflight-1031: absorb `not signed in` (including exit 0) into `classify_cloud_failure`. Leave `auth.json` on the non-zero path so a successful reply that names the file stays other. This lane did not edit that module.
- mvp-realfail-1031: the four FINDINGs can be rerun against this branch: sigkill-reap, review-reject, auth-failure, redaction.
- mvp-dogfood-1031: F1 is fixed here. A new test file can reach the gate and land. An edit or delete of a base test still fails unless `--writable-test` names it.
- mvp-sixtask-1031: t4 and t5 need `--writable-test` for each existing test file the task is allowed to edit. The flag is repeatable. A test file that is not named still fails. Their report's NO-GO is that missing flag on the old cloud base. This lane did not edit their eval files.
- mvp-surface-1031: the operator card stays in that lane's files. This lane did not write `docs/modules/` or `docs/ops/pfy-build-daily.md`.
- mvp-review-fix-1031: local G4 and G5 were mirrored here without `git add -A -f`. The local runner was not edited.

## Gate

Tester plus Reviewer. This is a runtime change (`scripts/pfy_build_cloud.py` and `tests/test_pfy_build_cloud.py`). `scripts/pfy` was not edited in this lane.

Pregate not run: host busy.

## Next step

Stop this lane. When integrate collects branches, merge this one after cloud and preflight. Sixtask can rerun t4 and t5 with `--writable-test`. Realfail can rerun the four FINDINGs. Do not merge to main from here.
