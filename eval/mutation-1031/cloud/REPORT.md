# Cloud runner mutation report, wave 5 (2026-10-31)

Harness: `eval/mutation-1031/cloud/run_mutants.py`, reused from `origin/bot/mvp-mutate-cloud-1031` at `9f707fd` and extended. The wave-3 catalog `MUTANTS` (C1-C16) is unchanged. This lane adds `CLOUD2_MUTANTS` (C17-C43). `main()` runs both lists. `--mutant` filters the combined catalog.

Each mutant is applied to a copy of `scripts/pfy_build_cloud.py` inside `git clone --local --no-hardlinks` under this worktree's `tmp/mutation-1031/cloud/clones/`. The worktree file is never opened for write. The suite is `nice -n 19 python3 -m unittest`, timeout 180s. A failing suite is killed. A timeout is killed. A missed anchor is `unapplicable` and the process exits 2. Survived means exit 0.

Before (`--baseline-only`) runs only `tests.test_pfy_build_cloud`. After also runs `tests.test_mut_cloud_survivors` and `tests.test_mut_cloud2_survivors`. Both harness modules are skipped so the harness does not start itself.

Wave-3 score, not re-run here: 16 killed, 0 survived, on the runner that lane measured (sha256 `d4f28f2ed82ad8db824def2be1753ce82301a57d175c6070fca085a2c5f95432`). See that lane's `eval/mutation-1031/cloud/REPORT.md` on `origin/bot/mvp-mutate-cloud-1031`. This table does not rescore C1-C16.

This lane's runner sha256, both rounds: `f2dd898417eafaf99a70562a36ca0f31e3db7a8112af936b4359d757a05e5c00`. The source file was not edited.

Merges, never rebase: `origin/bot/mvp-integrate-1031` `f877c7d` (merge `9763263`). `origin/bot/mvp-dogfood-fix-1031` `1fa9fd3` was already inside that tip.

Raw rows: `results/before.json` (HEAD `1dd23ee`, 516.8s, file time 2026-10-31T23:59:55Z) and `results/after.json` (HEAD `dd0c34e`, 708.7s, file time 2026-11-01T00:30:19Z). The harness recorded `origin/bot/mvp-cloudfix-1031` as `80470185e9bfccadef83ae19401344e8dcd0d945` at both runs.

The before file's `detail` field is noisy. A passing recovery test prints `FAIL: commit-recheck-failed`, and the old `first_detail` kept that line. Status is the unittest exit code and is the score. `first_detail` now prefers `FAIL: test_`, `ERROR: test_`, `AssertionError`, and `Traceback`. The after file names the killing test.
The C1-C16 table below is the mutate-cloud score. Its raw rows stay on `origin/bot/mvp-mutate-cloud-1031`. The JSON files here are the wave-5 run.


## Mutant table

| ID | Mutant | Before | After | What went red |
|----|--------|--------|-------|----------------|
Wave 3, C1-C16.

| C1 | gate result inverted | killed | killed | `test_direct_grok_home_fails_then_a_clean_retry_lands` |
| C2 | retry count off by one | killed | killed | same first failure (one fewer attempt) |
| C3 | review accept and reject swapped | killed | killed | same first failure |
| C4 | missing verdict treated as accept | survived | killed | `test_missing_review_verdict_is_rejected_and_not_committed` |
| C5 | scope set check skipped | killed | killed | `test_staged_name_outside_the_reviewed_set_resets_and_does_not_commit` |
| C6 | git add of a path outside the reviewed set | killed | killed | `test_gitignored_extra_file_is_absent_from_the_commit` |
| C7 | rate-limit class ignored | killed | killed | `test_embedded_429_follows_the_preflight_classifier` |
| C8 | auth regex removed | killed | killed | `test_not_signed_in_is_unauthenticated_on_zero_and_nonzero_exit` |
| C9 | interrupted handler does not kill the process group | killed | killed | `test_sigint_interrupts_with_no_branch` |
| C10 | reap signals the local pid file | survived | killed | `test_reap_does_not_signal_the_local_pid_file` |
| C11 | redaction step skipped | killed | killed | `test_receipt_redacts_an_xai_marker_in_the_task_and_the_reply` |
| C12 | receipt pushed hard-coded true | killed | killed | `test_pass_does_not_push_the_cloud_branch` |
| C13 | worktree not removed on PASS | killed | killed | `test_pass_matches_receipt_and_leaves_caller_clean` |
| C14 | branch prefix changed | killed | killed | `test_zero_exit_with_rate_limit_text_is_not_blocked` |
| C15 | dry-run starts grok | killed | killed | `test_dry_run_writes_receipt_and_starts_no_grok` (exit 1, `no-change`) |
| C16 | exit codes 4, 3, 1, 2 shuffled | killed | killed | `test_embedded_429_follows_the_preflight_classifier` |

Before: 14 killed, 2 survived. After: 16 killed, 0 survived.

The "what went red" column is the failure that shows the mutant changed behavior. For C1, C2, and C3 the first reported failure is the direct grok-home test because that case is sensitive to gate and retry count. C15's unittest output lists `test_p_help_reaches_dogfood_and_positional_reaches_cloud` first. The dry-run test also fails: the run exits 1 with reason `no-change` instead of writing a dry-run receipt and leaving grok unstarted.

## How the edits are applied

- C1 flips the post-change gate check from `exit != 0` to `exit == 0`.
- C2 sets `max_attempts` to `args.retries` instead of `args.retries + 1`.
- C3 returns accept when the reply says reject, and reject when it says accept.
- C4 returns accept when the reply has no verdict line.
- C5 guards the cached-name comparison with `False and`.
- C6 replaces the literal `git add` of reviewed paths with `git add -A -f`.
- C7 turns a `rate-limit` class into `other` inside `classify_runner_failure`. The phrase list lives in `pfylib/build_preflight.py`, which this lane does not edit.
- C8 stops applying the runner regex `_NOT_SIGNED_IN`.
- C9 sets the interrupt flag and does not signal the child group.
- C10, before the cloud pid file is read, signals `pgid` and `agent_pgid` from `tmp/local-build.pids.json`.
- C11 makes `redact()` return the input text.
- C12 writes `"pushed": True` on the finished receipt.
- C13 returns from `drop_worktree` before the worktree is removed.
- C14 uses the branch prefix `mut/` instead of `cloud/`.
- C15 skips the dry-run return, so `execute()` starts grok.
- C16 remaps fail, usage, timeout, and blocked to 2, 4, 1, and 3. Exit 0 stays 0.

## Survivors left

None.

C4 survived the baseline because every existing fake grok prints `verdict: accept` or `verdict: reject`. A reply of `looks fine` was not in the suite. The new test uses that reply with `--retries 0`. The current runner rejects it (`review-unparseable`, no branch, exit 1). C4 commits and exits 0, so the test fails.

C10 survived the baseline because the existing reap tests call `kill(pid, 0)`. A sleeper that has been signaled is a zombie until the parent reaps it, and `kill(pid, 0)` still succeeds. The new test uses `poll()`, which is `None` only while the process is running. On C10, `poll()` is `-15` (SIGTERM).

No runner change was required. No test is marked `expectedFailure`.

Wave 5, C17-C43.

| ID | Mutant | Before | After | What went red |
|----|--------|--------|-------|----------------|
| C17 | writable-test allow list ignored | killed | killed | `test_two_writable_tests_land_and_a_third_base_file_does_not` |
| C18 | every base test treated as writable | killed | killed | `test_changed_test_file_fails_before_the_gate_and_is_not_committed` |
| C19 | writable-test match is exact, globs do not apply | survived | killed | `test_writable_glob_lets_the_matching_base_test_change` |
| C20 | git add drops the literal pathspec | killed | killed | `test_star_filename_commits_that_file_and_not_the_pyc` |
| C21 | git add uses a glob pathspec | survived | killed | `test_literal_star_does_not_stage_a_sibling_pyc` |
| C22 | archive recheck skipped | killed | killed | `test_new_test_file_reaches_the_gate_and_lands` |
| C23 | archive recheck timeout counted as a pass | survived | killed | `test_recheck_timeout_does_not_commit` |
| C24 | archive recheck failure does not retry | killed | killed | `test_gitignored_helper_fails_recheck_then_a_clean_retry_lands` |
| C25 | protected path check skipped | killed | killed | `test_direct_grok_home_fails_then_a_clean_retry_lands` |
| C26 | protected `**` no longer matches zero directories | killed | killed | `test_direct_grok_home_fails_then_a_clean_retry_lands` |
| C27 | protected globs do not match the file basename | survived | killed | `test_nested_auth_json_is_protected` |
| C28 | assignment redaction never fires | killed | killed | `test_receipt_keeps_fixture_ids_and_still_hides_secret_assignments` |
| C29 | assignment redaction hides fixture ids | killed | killed | `test_receipt_keeps_fixture_ids_and_still_hides_secret_assignments` |
| C30 | pem block redaction skipped | survived | killed | `test_private_key_body_is_redacted` |
| C31 | product gate keeps secret env vars | killed | killed | `test_gate_drops_secret_env_and_grok_still_sees_it` |
| C32 | uppercase env name is not enough to redact | killed | killed | `test_receipt_redacts_tokens_keys_and_private_key_blocks` |
| C33 | recovery line stays off the terminal | killed | killed | `test_missing_gate_binary_exits_2_before_grok` |
| C34 | gate timeout recovery says grok timed out | killed | killed | `test_hung_gate_is_timeout_and_does_not_commit` |
| C35 | missing base is a usage error | killed | killed | `test_missing_base_is_worktree_failed_and_leaves_the_caller` |
| C36 | HEAD mismatch silently builds origin/main | killed | killed | `test_head_that_is_not_origin_main_exits_2_before_grok` |
| C37 | absent origin/main is an error instead of HEAD | killed | killed | `test_default_gate_import_error_exits_2_before_grok` (ERROR) |
| C38 | timeout does not kill the grok process group | killed | killed | `test_timeout_exits_3_and_kills_the_grok_group` |
| C39 | review timeout is a review reject | survived | killed | `test_review_timeout_is_timeout_not_reject` |
| C40 | before-gate timeout still starts grok | survived | killed | `test_hung_before_gate_does_not_start_grok` |
| C41 | timeout of zero is accepted | survived | killed | `test_timeout_zero_is_usage_and_does_not_start_grok` |
| C42 | failure recovery line is empty | killed | killed | `test_every_failure_reason_receipt_has_a_recovery_line` |
| C43 | missing-base recovery omits the ref | killed | killed | `test_missing_base_is_worktree_failed_and_leaves_the_caller` |

Before: 19 killed, 8 survived. After: 27 killed, 0 survived. 0 unapplicable. 0 error. 0 equivalent.

A first after run against `7ded452` scored 26 killed and 1 survived (C21). That run is not the score. The bracket-filename test does not separate `:(literal)` from `:(glob)`, because both pathspecs stage `foo[1].py`. The killing test landed in `dd0c34e`.

## How the edits are applied

- C17 guards the writable-test allow list with `False and`.
- C18 returns True from `_writable_test` after the traversal check, so every non-traversing base test is writable.
- C19 compares the pattern with `==` and does not call `fnmatch`.
- C20 stages with `git add -- <path>` and drops `:(literal)`.
- C21 stages with `:(glob)` instead of `:(literal)`.
- C22 sets the recheck result to pass without calling `recheck_sha`.
- C23 returns a pass when the archive recheck reports `aborted: timeout`.
- C24 refuses to retry `commit-recheck-failed`.
- C25 computes protected hits and then ignores them.
- C26 disables the `/**/` collapse, so a pattern no longer matches zero extra directories.
- C27 matches a protected glob against the full relative path only. The basename check is gone.
- C28 never rewrites an assignment to `[redacted]`.
- C29 rewrites every assignment, including fixture ids such as `user_key=list-user`.
- C30 skips `_PEM.sub`, so a key body can remain after the BEGIN and END replace.
- C31 leaves TOKEN, SECRET, PASSWORD, and KEY names in the product-gate child env.
- C32 drops the `name.isupper()` redaction clause.
- C33 does not print `self.recovery` on stderr.
- C34 skips the gate-timeout recovery sentence, so the wording falls through to the grok timeout line.
- C35 turns `BaseMissing` into usage exit 2.
- C36 returns `origin/main` when HEAD and `origin/main` differ, with no usage error.
- C37 raises `UsageError` when `origin/main` is absent, instead of building from HEAD.
- C38 on `TimeoutExpired` does not call `_kill_pgid` before `communicate`.
- C39 records a review timeout as `review-rejected` and exit 1.
- C40 ignores a before-gate timeout and continues into grok.
- C41 rejects only `--timeout < 0`, so zero is accepted.
- C42 makes `failure_recovery` return an empty string.
- C43 drops the missing ref from the worktree recovery sentence.

## Survivors the baseline left

Eight. All eight are killed by `tests/test_mut_cloud2_survivors.py`. None is equivalent. None required a runner change. No findings file for mvp-cloudfix-1031.

C19 survived because the existing writable-test cases pass exact paths. A glob pattern was not in the suite.

C21 survived the star-filename test because the extra pyc lived under `__pycache__/`, which a root glob `*` does not match, and `files_changed` already skips `.pyc`. A bracket name is also not a discriminator.

C23 survived because the hung-gate test times out an early gate call. The archive recheck is a later call. Treating that later timeout as a pass still satisfies the early-timeout test.

C27 survived a nested `*.pem` case. Python `fnmatch` lets `*` match `/`, so `*.pem` already matches `keys/id.pem` without the basename check. `auth.json` does not.

C30 survived the receipt test that only checks for `BEGIN`. The header replace still removes that word when the PEM block pass is skipped. The key body stays.

C39 survived because the review tests that time out are not separated from a reject: several paths use `--no-review`. A review call that sleeps was not asserted as exit 3.

C40 survived because the hung-gate test allows grok to have started on a later gate. The before-gate call is the one that must stop the run first.

C41 survived because the suite uses a positive timeout. `--timeout 0` was not asserted.

## How the new tests fail and recover

- C19: `--writable-test tests/test_ed*.py` must let `tests/test_edit.py` land and must leave `tests/test_keep.py` unchanged. Exit 0, receipt PASS. If the pattern is compared as literal text, the run exits 1 with `tests-tampered` and no commit.
- C21: grok writes a file named `*` and a root `extra.pyc`. `:(literal)*` commits only the star file. The pyc stays out of the tree. `:(glob)*` also stages `extra.pyc` (the runner's changed-file list skips `.pyc`, and the file is not gitignored), the scope check fails, and the receipt is not PASS.
- C23: gates 1 to 3 pass. Gate 4 (the archive recheck) sleeps. With `--timeout 1` and `--no-review`, the run exits 3, reason `timeout`, recovery contains `the gate timed out`, and no `cloud/` branch exists. If the recheck timeout is treated as a pass, a branch is created and the exit is 0.
- C27: grok writes `nested/auth.json` and `kept.py`. The run exits 1, reason `protected-path-changed`, recovery names `nested/auth.json`, and no branch is kept. If the basename match is off, the nested file is committed.
- C30: grok prints a private-key block whose body is `MIIB-CLOUD2-SECRET`, and writes `kept.py`. The receipt must not contain that body or `BEGIN PRIVATE KEY`, and it must contain `[redacted-private-key]`. The commit still contains `kept.py`. If the PEM block pass is skipped, the body remains in the receipt.
- C39: the implement call is fast. The review call (argv contains `PFY-CLOUD-REVIEW`) sleeps. `--retries 0 --timeout 1` exits 3, status TIMEOUT, reason `timeout`, and no branch. If the timeout is stored as `review-rejected`, the exit is 1.
- C40: the first gate sleeps 30s and grok would write a side marker. With `--timeout 1` the run exits 3 before grok, recovery contains `the gate timed out`, and the marker is absent. If the before-gate timeout is ignored, the marker exists.
- C41: `--timeout 0` exits 2 with `--timeout must be > 0`. Grok is not started. No receipt file is written. If zero is accepted, grok starts.

## Checks on the unmutated runner

`nice -n 19 python3 -m unittest tests.test_mut_cloud2_harness tests.test_mut_cloud2_survivors tests.test_mut_cloud_harness tests.test_mut_cloud_survivors`

17 tests, OK, 13.385s, at HEAD `dd0c34e` on 2026-11-01T00:34Z. The cloud suite `tests.test_pfy_build_cloud` was 61 tests, OK, 24.938s, before the catalog run. It is not a red base.

## Re-run

```bash
git fetch origin && git merge --no-edit origin/bot/mvp-cloudfix-1031
nice -n 19 python3 eval/mutation-1031/cloud/run_mutants.py --label after --timeout 180
```

Pass `--mutant C17` (and the rest of C17-C43) to score only this wave. Use `--baseline-only` to score `tests.test_pfy_build_cloud` alone. If an anchor no longer matches, the row is `unapplicable` and the command exits 2. Update that anchor. A missed anchor is not a survival.
