# Handoff: mvp-cloud-1031

Exit: lane empty. The daily cloud build DoD is met on `bot/mvp-cloud-1031`. Wall clock and host pressure did not fire. No question was asked. No merge, no PR, no tag.

Launch: 2026-10-31T20:00:40Z. This handoff is inside the wall cap (stop new items by 2026-11-01T03:40:40Z).

## Items done

| Item | SHA | Tests | Result |
|------|-----|-------|--------|
| Loop exits before code | 9903e70 | docs only | PASS |
| Confirm origin/main has no cloud runner | 9903e70 | git ls-tree | PASS |
| Skeleton: usage exit 2, dry-run receipt, no grok | 62d7e3a | test_pfy_build_cloud, 3 OK | PASS |
| Dispatch in scripts/pfy cmd_build | 860df72 | test_pfy_build_cloud, 4 OK | PASS |
| PASS path: cloud/ branch, reviewed paths, caller porcelain unchanged | 141b203 | test_pfy_build_cloud, 5 OK | PASS |
| Gate red then PASS; review reject then accept; final reject leaves no branch | 6a8220e | CloudBuildRetryTests, 3 OK | PASS |
| No-change, gitignored extra, scope mismatch | ea5ce77 | CloudBuildNoChangeTests, 3 OK | PASS |
| Rate limit, auth, dirty caller, SIGTERM, reap, timeout, redaction, protect, keep-worktree, no-review | 9285fec | CloudBuildFailureTests, 13 OK | PASS |
| .gitignore line pipelines/dogfood/build-cloud/ | db964a4 | cloud module plus tests.test_pfy_build_p, 40 OK, 1 skipped | PASS |
| tests-tampered, tests-flaky, worktree-failed | b9a4890 | CloudBuildGateReasonTests, 3 OK | PASS |

Log commits between those rows: e51c47a, 265f4c2, c539081, 49c89cc, 38fa7ad, a5c2e7f. The drop-in commit on this branch is 979b3c6.

## Skipped

- mvp-dedupe-1031: round 2. It rewrites the inline classifier and edits pfylib/build_preflight.py. The plan says to start it only after origin/bot/mvp-integrate-1031 has a pushed handoff. That module is not on this branch. Recorded as lane empty, not implemented here.
- mvp-surface-1031, mvp-eval-1031, mvp-review-fix-1031, mvp-preflight-1031: other lanes own those files. Not edited.
- G10 (stage promotion, voice, Laguna, ADR-0017, catalog apply, T-0081, T-0074, T-0070): excluded by the plan. No ADR and no OQ draft. The daily default stays cloud Grok.
- Pregate not run: host busy. `pgrep -f 'Runner[.]Worker'` matched pid 1561207 at 2026-10-31T20:20:54Z.

## Test evidence

Targeted, niced, no network, fake grok, scratch under this worktree's `tmp/cloud-build-tests`:

- `nice -n 19 python3 -m unittest tests.test_pfy_build_cloud tests.test_pfy_build_p` after the gitignore line: 40 tests, OK, 1 skipped (the dogfood module's existing skip). The line `FAIL: grok not on PATH` is that module's expected missing-grok message, not a failure.
- `nice -n 19 python3 -m unittest tests.test_pfy_build_cloud.CloudBuildGateReasonTests`: 3 tests, OK, 0.354s.
- Earlier rows: skeleton 3, dispatch 4 total, pass 5 total, retries 3, no-change 3, failures 13. All OK.

`tests/test_pfy_build_p.py` was run and not edited. Forbidden files were not edited. The runner does not read `auth.json` and does not call a local model.

## How each change fails and recovers

- PASS: fake grok writes a reviewed file, the gate is green twice, review prints `verdict: accept`, and the commit contains only those paths. Recover from a bad attempt by retrying up to `--retries` extra times (default 2). Spent retries exit 1 and leave no branch.
- Gate red: attempt reason `tests`, no commit, next prompt includes the gate tail. A second green run that then goes red is `tests-flaky` and is not committed.
- A new or changed test file is `tests-tampered` before the gate runs again. The weakened gate is not the evidence. No commit.
- Review reject: attempt `PASS-REJECTED`, no commit, next prompt gets the reasons and the previous diff. Spent rejects exit 1, reason `review-rejected`, no branch.
- No-change: the gate still runs. A green gate and an empty diff is not PASS. Feedback is `no-change` plus the gate tail. Spent retries exit 1, no branch.
- Scope mismatch: after `git add` of the reviewed paths, the cached name set must match. On mismatch, `git reset`, exit 1, reason `scope-commit-mismatch`, no branch. Never `git add -A -f`. A gitignored extra file is not in the commit.
- Rate limit (non-zero rc and matching text): exit 4, status BLOCKED, reason `rate-limit`, no branch. Recovery is the exact `./pfy build --local "<task>"` line. That command is not started. rc 0 with the same words is not a rate limit.
- Auth (missing grok, or text such as `not logged in`): exit 1, reason `unauthenticated`. Recovery tells Mark to run `grok` once and rerun the same `./pfy build`. It does not suggest `--local`. Empty HOME does not open `auth.json`.
- Dirty caller files stay dirty and are absent from the new commit. If `git worktree add` fails, exit 1, reason `worktree-failed`, caller status unchanged, grok is not started.
- SIGTERM: exit 1, reason `interrupted`, the grok process group is signaled, no branch. After SIGKILL, `./pfy build --reap` exits 0 and writes ABORTED / `no-receipt` for a dead cloud pid whose receipt is missing. A live recorded pid is left alone. A pgid listed only in `tmp/local-build.pids.json` is not signaled.
- Timeout of the grok call: exit 3, reason `timeout`, the grok group is killed, no branch.
- Protected path (`auth.json` and the default globs): reason `protected-path-changed`, not committed.
- Receipt text is redacted before write. `AKIA`, `BEGIN PRIVATE KEY`, and `sk_` plus 8 characters do not remain in the file.
- `--dry-run` exits 0, starts no grok, writes no branch, receipt status DRY-RUN, commit null.
- `--keep-worktree` leaves the worktree and sets `worktree_removed` false. `--no-review` makes one grok call and stores `review.verdict` `skipped`.

## Cross-lane requests

- mvp-integrate-1031: merge `origin/bot/mvp-cloud-1031` last in the plan's order. The demo grok run and `eval/mvp-1031/check_receipt.py` belong to that lane once the eval branch exists. Do not treat this handoff as a Feature GO.
- mvp-dedupe-1031, after integrate: replace the inline `classify_cloud_failure` with `pfylib.build_preflight` if that module has landed. Keep the cloud behavior tests green, including rate-limit and auth. This lane left the inline copy so the branch tests alone.
- mvp-surface-1031: the operator card is still that lane's file (`docs/modules/pfy-build.md`, `docs/ops/pfy-build-daily.md`). This lane did not write it.
- mvp-review-fix-1031: local G4 and G5 stay on that lane. Cloud does not copy `git add -A -f` or the no-change-before-gate skip.

## Gate

Tester plus Reviewer. This is a runtime change (`scripts/pfy_build_cloud.py` and `scripts/pfy` `cmd_build` plus the build help paragraph).

Pregate not run: host busy.

## Next step

Stop this lane. When the other round-1 branches have pushed, or when the wall clock says to collect them, launch mvp-integrate-1031. Merge this branch last. The real `./pfy build "<task>"` demo is that lane's job.
