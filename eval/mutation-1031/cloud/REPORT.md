# Cloud runner mutation report (2026-10-31)

Harness: `eval/mutation-1031/cloud/run_mutants.py`.

Each mutant is applied to a copy of `scripts/pfy_build_cloud.py` inside `git clone --local --no-hardlinks` under this worktree's `tmp/mutation-1031/cloud/clones/`. The worktree file is never opened for write. The suite is `nice -n 19 python3 -m unittest`, timeout 180s. A failing suite is killed. A timeout is killed. A missed anchor is `unapplicable` and the process exits 2. Survived means exit 0.

Before (`--baseline-only`) runs only `tests.test_pfy_build_cloud`. After also runs `tests.test_mut_cloud_survivors` (not `tests.test_mut_cloud_harness`, which would start the harness again).

Base: `origin/bot/mvp-cloudfix-1031` `d35af20`, merged as `0a76e22`. Runner sha256 `d4f28f2ed82ad8db824def2be1753ce82301a57d175c6070fca085a2c5f95432` on both rounds. Checked again at 2026-10-31T21:43Z: cloudfix was still `d35af20`, so there was no third round.

Raw rows: `results/before.json` (HEAD `9429aaf`), `results/after.json` (HEAD `38b26a1`).

## Mutant table

| ID | Mutant | Before | After | What went red |
|----|--------|--------|-------|----------------|
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

## Re-run

```bash
git fetch origin && git merge --no-edit origin/bot/mvp-cloudfix-1031
nice -n 19 python3 eval/mutation-1031/cloud/run_mutants.py --label after
```

Use `--baseline-only` to score the suite without `tests.test_mut_cloud_*`. If an anchor no longer matches, the row is `unapplicable` and the command exits 2. Update that anchor. Do not treat it as survived.
