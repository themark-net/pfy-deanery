# MVP DoD walkthrough (2026-10-31)

Every line of the Functional MVP Definition of Done and every failure-case row from `origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`. For each row: the command that proves it, the test (file and test name, checked to exist), and the evidence receipt as `branch:path`.

Rechecked `2026-10-31T21:21:27Z` after `git fetch`:

| Branch | Tip | What it adds for this list |
|--------|-----|----------------------------|
| `origin/bot/mvp-integrate-1031` | `19c2710` | PASS demo `eval/mvp-1031/demo-receipt.json` |
| `origin/bot/mvp-realfail-1031` | `d09647a` | Real receipts under `eval/mvp-1031/realfail/` |
| `origin/bot/mvp-cloudfix-1031` | `57c6dad` | Extra behavior tests. After-fix receipts are named only as `tmp/` paths in `docs/ops/RUN-LOG-mvp-cloudfix-1031.md`. They are not in git. |
| `origin/bot/mvp-realfail2-1031` | `884a16a` | Drop-in on top of cloudfix. No receipt directory of its own yet. |

This branch is `bot/mvp-docs-1031`, which contains the integrate tip. A test cited on cloudfix is also on realfail2 until that branch diverges. It is not on this branch unless the row says so.

## GAPs

A row is a GAP when the matching receipt is not on a fetched branch, or when no test with that name exists on a fetched branch. Tests below were confirmed with `git grep` on the named branch.

1. Auth `unauthenticated` receipt. Realfail `eval/mvp-1031/realfail/auth-failure/receipt.json` is `FAIL` / `no-change` with empty recovery. Grok text was `Not signed in`. Cloudfix run log names `tmp/auth-after/receipt.json` (`FAIL` / `unauthenticated`). That file is not on a branch.
2. Review-reject spent receipt. Realfail `eval/mvp-1031/realfail/review-reject/receipt.json` is `PASS` / `ok` (review accepted `danger.sh`). Cloudfix names `tmp/danger-after/receipt.json` (`FAIL` / `review-rejected`, 3 attempts). Not on a branch.
3. Review-reject then a later accept. Test exists on this branch. No branch holds a receipt whose attempts go `PASS-REJECTED` then `PASS`.
4. Redaction of the planted `xai-` marker. Realfail `eval/mvp-1031/realfail/redaction/receipt.json` is `PASS` and still contains `xai-FAKE0000` in `task` and `output_tail` (realfail FINDING). Cloudfix names `tmp/redact-after/receipt.json`. Not on a branch.
5. SIGKILL reap of the live grok. Realfail `eval/mvp-1031/realfail/sigkill-reap/receipt.json` is `ABORTED` / `no-receipt`, and `eval/mvp-1031/realfail/sigkill-reap/FINDING.md` says the live grok was still running. Cloudfix names `tmp/sigkill-after/receipt.json`. Not on a branch.
6. `scope-commit-mismatch` receipt. Test exists on this branch. Realfail gitignored-extra explicitly did not produce this reason. No branch receipt uses `scope-commit-mismatch`.
7. `worktree-failed` receipt. Test exists on this branch. No branch receipt uses `reason` `worktree-failed`.
8. Gate red, then a later PASS. Test exists on this branch. No branch receipt shows attempt 1 `tests` and a later attempt `PASS`. The demo receipt is one PASS attempt.

`origin/bot/mvp-realfail2-1031` has not closed any of these. Next recheck is when that branch gains a commit past `884a16a`.

## Daily command

| DoD line | Command | Test | Receipt |
|----------|---------|------|---------|
| `./pfy build "<task>"` is the daily command. A missing task exits 2 and prints that command, and names `-p` and `--local`. | `./pfy build` (quickstart, exit 2) and `./pfy build --help` (exit 0) | `tests/test_pfy_build_cloud.py` `CloudBuildSkeletonTests.test_no_task_exits_2_and_names_the_daily_command` and `test_help_exits_0_and_names_the_daily_command` | Usage writes no receipt. Help writes no receipt. |

`tests/test_pfy_build_local.py` `CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same` still expects dogfood flags on bare `./pfy build --help`. Integrate recorded that failure. It is not the proof for this row.

## Flags

| Flag | Command | Test | Receipt |
|------|---------|------|---------|
| `--repo DIR` | `./pfy build --help` (help text: git repo to build) | `tests/test_pfy_build_cloud.py` `CloudBuildPassTests.test_pass_matches_receipt_and_leaves_caller_clean` (passes `--repo`) | Demo used `--repo` on a temp fixture. Receipt `origin/bot/mvp-integrate-1031:eval/mvp-1031/demo-receipt.json` (also on this branch). |
| `--base REF`, default `origin/main` when the ref exists | `./pfy build "quickstart dry run" --dry-run --receipt-dir "$PWD/tmp/quickstart-dry-run"` left `base` `origin/main` without passing `--base` | On cloudfix and realfail2: `tests/test_pfy_build_cloud.py` `test_default_base_is_origin_main_not_the_caller_head` and `test_explicit_base_selects_that_ref`. Not on this branch. | Dry-run receipt is gitignored `tmp/quickstart-dry-run/receipt.json` in this worktree, not a branch object. |
| `--test-cmd CMD`, default `python3 -m unittest discover -s tests -t .` | `./pfy build --help` | `CloudBuildPassTests.test_pass_matches_receipt_and_leaves_caller_clean` passes `--test-cmd`. Demo gate is `python3 -m unittest test_add`. | `eval/mvp-1031/demo-receipt.json` field `gate.cmd`. |
| `--retries N`, default 2 extra, 3 total | `./pfy build --help` prints `default 2, so 3 total` | On cloudfix and realfail2: `test_gate_stays_red_for_the_default_three_attempts`. On this branch the spent-3 case is the realfail receipt, not a same-named test. | `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/gate-red/receipt.json` has attempts 1, 2, 3, each `FAIL` / `tests`. |
| `--no-review` | `./pfy build --help` | `tests/test_pfy_build_cloud.py` `CloudBuildFailureTests.test_no_review_skips_the_second_grok_call` | No branch receipt for a `--no-review` run. The test writes a temp receipt. |
| `--receipt-dir DIR` | Dry-run command above wrote `tmp/quickstart-dry-run/receipt.json` | `CloudBuildSkeletonTests.test_dry_run_writes_receipt_and_starts_no_grok` | Same gitignored dry-run file. Demo copy is the integrate path above. |
| `--dry-run` | Same dry-run command. Exit 0. Stdout `DRY-RUN dry-run branch=none receipt=...`. `status` `DRY-RUN`, `commit` null. | `CloudBuildSkeletonTests.test_dry_run_writes_receipt_and_starts_no_grok` | Gitignored tmp receipt. Not on a branch. |
| `--reap` | `./pfy build --reap --repo tmp/qs-land-repo` printed `reaped: none`, exit 0 | `CloudBuildFailureTests.test_reap_aborts_a_dead_cloud_pid_and_spares_a_local_only_pid` and `test_reap_leaves_a_live_recorded_pid_alone` | See SIGKILL row. The empty throwaway wrote no receipt. |
| `--keep-worktree` | `./pfy build --help` | `CloudBuildFailureTests.test_keep_worktree_leaves_the_directory` | Demo receipt `worktree_removed` true (flag was not set). No branch receipt with the flag on. |

## PASS

| # | DoD line | Command | Test | Receipt |
|---|----------|---------|------|---------|
| 1 | Exit code 0 | Demo command in [HANDOFF-mvp-integrate-1031.md](HANDOFF-mvp-integrate-1031.md). Build exit 0. | `CloudBuildPassTests.test_pass_matches_receipt_and_leaves_caller_clean` | `eval/mvp-1031/demo-receipt.json` `exit_code` 0. Branch `origin/bot/mvp-integrate-1031` and this branch. |
| 2 | Stdout `PASS ok branch=cloud/<slug>-<stamp> receipt=<path>` | The same test asserts that regex on stdout. This lane did not re-run the cloud demo. | Same test | Demo branch field `cloud/make-add-return-the-sum-of-its-two-argum-20261031T210933627529Z`. |
| 3 | `receipt.json` schema `pfy-cloud-build/1` and the PASS fields (`status` `PASS`, `reason` `ok`, `review.verdict` `accept`, `review.reasons` list, attempts length at least 1, last `PASS`, `gate.cmd`, `gate.before`, `gate.after`, `recovery` empty, `pushed` false, `worktree_removed` true) | `python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt.json` exit 0 (ran `2026-10-31T21:21:27Z`, no stdout) | `tests/test_mvp_1031_receipt.py` `CheckReceiptTests.test_pass_receipt_exits_0` and `test_rejects_listed_field_failures` | Same demo receipt. `base` is `main` (the demo passed `--base main`). `recovery` is `""`. `worktree_removed` is true. |
| 4 | `git rev-parse <branch>` equals `commit`. Commit is not the caller's previous HEAD. Caller branch and `git status --porcelain` stay unchanged. No stash, reset, or commit in the caller. | The pass test checks rev-parse, caller HEAD, and a dirty file that stays dirty. Integrate handoff: fixture `main` stayed on the red seed `65ef19b`. The `cloud/` commit is `ebef4238a7eff8f938747623f7920b3fde74e586`. | Same pass test | Demo `commit` field matches that sha. |
| 5 | Commit tree contains only paths the review saw. A gitignored file outside that set is absent. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildNoChangeTests.test_gitignored_extra_file_is_absent_from_the_commit` | That test, on this branch | `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/gitignored-extra/receipt.json` is `PASS` / `ok`, commit `696dc4e83bffa1c2300c4216bb66e32680779bd8`. Handoff `f8e5553`: commit contains `kept.py` and not `ignored-extra.txt`. |
| 6 | Nothing pushed. No PR. `pushed` false. | Checker exit 0 rejects `pushed` true (`test_rejects_listed_field_failures`). | `CheckReceiptTests.test_rejects_listed_field_failures` and the pass test | Demo `pushed` false. |

## Dry-run, usage, -p, --local

| DoD line | Command | Test | Receipt |
|----------|---------|------|---------|
| Dry-run exits 0, starts no grok, writes no branch, receipt `DRY-RUN`, `commit` null | Quickstart dry-run above | `CloudBuildSkeletonTests.test_dry_run_writes_receipt_and_starts_no_grok` | Gitignored tmp receipt. Not on a branch. |
| `./pfy build` with no task exits 2 and prints the daily command, plus `-p` as the jev dogfood wrap and `--local` as the opt-in fallback | `./pfy build` exit 2. Output is in [QUICKSTART-pfy-build.md](../QUICKSTART-pfy-build.md). | `CloudBuildSkeletonTests.test_no_task_exits_2_and_names_the_daily_command` | None. Usage writes nothing. |
| `./pfy build -p "<prompt>"` stays `scripts/pfy_build_p.py`. Exit codes and `receipt.jsonl` do not change. | `./pfy build -p --help` exit 0. First line: `Apply local jev toolset, shadow decision, run grok -p (plain).` | `tests/test_pfy_build_cloud.py` `CloudBuildDispatchTests.test_p_help_reaches_dogfood_and_positional_reaches_cloud`. `tests/test_pfy_build_p.py` `BuildHelperFailRecoverTests.test_ready_exit_0` and `test_dry_run_writes_real_receipt_without_exec_grok`. | Dogfood dry-run receipt is produced by that p test under a temp dir, not committed here. |
| `./pfy build --local` stays the local runner. A gitignored extra file cannot be committed. A no-change attempt runs the gate. Local is not the default. Review stays on. | This lane did not run `--local`. Help text from `./pfy build --help` says `--local` is the opt-in fallback. | Local, on this branch: `tests/test_pfy_build_local.py` `LocalBuildTests.test_ignored_helper_is_not_committed`, `test_gitignore_star_does_not_commit`, `test_no_change_does_not_commit`. Cloud no-change gate tail: `CloudBuildNoChangeTests.test_no_change_runs_the_gate_and_does_not_pass` (asserts `GATE-TAIL-EMPTY` in the next prompt). | No local-model receipt from this lane. Cloud no-change receipt: `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/no-change/receipt.json` (`FAIL` / `no-change`, attempts 1..3, branch null). Handoff `e0bdb62`: prompts 2 and 3 contain `NO-CHANGE-GATE-TAIL`. |

## Failure cases

| Case | Command | Test | Receipt |
|------|---------|------|---------|
| Cloud rate limit. Exit 4. No branch. `BLOCKED` / `rate-limit`. Recovery is the exact `./pfy build --local "<task>"`. This run does not start it. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildFailureTests.test_rate_limit_exits_4_and_does_not_start_local` | That test, on this branch. Classifier phrases: `tests/test_build_preflight.py` `ClassifyCloudFailureTests.test_each_rate_limit_phrase_wins_even_with_not_logged_in`. | `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/rate-limit/receipt.json`. `BLOCKED` / `rate-limit`, exit 4, branch null, `pushed` false. `recovery` is `./pfy build --local rate-limit-sim`. Not run by this lane. |
| Auth failure or grok missing. Exit 1. `FAIL` / `unauthenticated`. Recovery is log in with grok, then rerun the same `./pfy build`. No `--local`. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildFailureTests.test_not_logged_in_exits_1_and_does_not_suggest_local` and `test_missing_grok_with_empty_home_does_not_raise` | Those two, on this branch. Cloudfix and realfail2 add `test_not_signed_in_is_unauthenticated_on_zero_and_nonzero_exit` for the real `Not signed in` text. | GAP. Realfail auth receipt is `FAIL` / `no-change`, recovery empty. See GAP 1. |
| Gate red, retries left. Exit stays open. Attempt `FAIL` with `tests`, `tests-flaky`, or `tests-tampered`. Feedback includes the gate tail. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildRetryTests.test_gate_red_then_pass_commits_only_the_green_attempt` | That test: attempt 0 `reason` `tests`, then `PASS`. Tampered: `CloudBuildGateReasonTests.test_changed_test_file_fails_before_the_gate_and_is_not_committed` (`tests-tampered`). Flaky: `test_second_green_gate_that_goes_red_is_flaky_and_not_committed` (`tests-flaky`). | GAP for a branch receipt of red-then-PASS. See GAP 8. Tampered and flaky have tests only. |
| Gate red, retries spent. Exit 1. No branch. Attempts length 3 by default. | Realfail gate-red run, recorded in that lane's handoff. | On cloudfix and realfail2: `test_gate_stays_red_for_the_default_three_attempts`. Not on this branch. | `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/gate-red/receipt.json`. `FAIL` / `tests`, exit 1, branch null, attempts `(1, FAIL, tests)`, `(2, FAIL, tests)`, `(3, FAIL, tests)`. `gate.before.exit` 1, `gate.after.exit` 1. |
| Review reject, retries left. Attempt `PASS-REJECTED` / `review-rejected`, `review.verdict` `reject`. Next call gets the reasons and the diff. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildRetryTests.test_review_reject_then_accept` | That test, on this branch. | GAP. See GAP 3. |
| Review reject, retries spent. Exit 1. `FAIL` / `review-rejected`. No branch. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildRetryTests.test_final_review_reject_leaves_no_branch` | That test, on this branch. Cloudfix also rejects a root recursive delete the reviewer accepted (`eb13975`). | GAP for the fixed behavior. Realfail review-reject receipt is the FINDING (`PASS` / `ok`, commit `9accbc129eeb6d4288a5f5f4e473849451d2f7b0`). See GAP 2. |
| No-change. Counts as an attempt. Exit 1 when retries are spent. Gate still runs. Green gate plus empty diff is not PASS. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildNoChangeTests.test_no_change_runs_the_gate_and_does_not_pass` | That test. Real run: realfail handoff `e0bdb62`. | `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/no-change/receipt.json`. Three `FAIL` / `no-change` attempts, exit 1, branch null. Gate before and after exit 0. |
| Scope vs commit mismatch. Exit 1. Index reset. No branch. `reason` `scope-commit-mismatch`. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildNoChangeTests.test_staged_name_outside_the_reviewed_set_resets_and_does_not_commit` | That test asserts `payload["reason"] == "scope-commit-mismatch"`. | GAP. See GAP 6. |
| Dirty caller. Exit 0 when the worktree base is clean. Dirty caller files stay dirty and stay out of the commit. If the base cannot be checked out, exit 1, `reason` `worktree-failed`. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildFailureTests.test_dirty_caller_file_stays_dirty_and_out_of_the_commit` and `tests.test_pfy_build_cloud.CloudBuildGateReasonTests.test_worktree_add_failure_leaves_the_caller_dirty_file` | Those two, on this branch. | Dirty PASS: `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/dirty-caller/receipt.json` (`PASS` / `ok`, branch `cloud/create-kept-py-containing-exactly-the-li-20261031T203521526172Z`, commit `ac54ba9bc41c1c907ae2ca4a959126801d63928e`). Handoff `3fbb203`: `untracked-dirty.txt` and `staged-dirty.txt` stayed dirty and are absent from the commit. `worktree-failed` receipt: GAP. See GAP 7. |
| SIGINT or SIGTERM. Exit 1. `FAIL` / `interrupted`. No branch. Grok process group is signaled. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildFailureTests.test_sigterm_interrupts_with_no_branch` | SIGTERM test on this branch. SIGINT test `test_sigint_interrupts_with_no_branch` is on cloudfix and realfail2, not on this branch. The handler `signal.signal(signal.SIGINT, ...)` is in `scripts/pfy_build_cloud.py` on this branch. | `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/interrupted-sigint/receipt.json` and `interrupted-sigterm/receipt.json`. Both `FAIL` / `interrupted`, exit 1, branch null. Handoff `00d0ec4`. |
| SIGKILL. Next `./pfy build --reap` exits 0. Receipt `ABORTED` / `no-receipt`. Reap signals only pgids in `tmp/cloud-build.pids.json`, not a pid listed only in `tmp/local-build.pids.json`. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildFailureTests.test_reap_aborts_a_dead_cloud_pid_and_spares_a_local_only_pid` | That test, on this branch. | Status fields: realfail sigkill receipt `ABORTED` / `no-receipt`, exit 1, empty attempts. The live-grok half is GAP. See GAP 5. |
| Timeout. Exit 3. `TIMEOUT` / `timeout`. No branch. Rerun with a longer `--timeout`. | `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildFailureTests.test_timeout_exits_3_and_kills_the_grok_group` | That test, on this branch. | `origin/bot/mvp-realfail-1031:eval/mvp-1031/realfail/timeout/receipt.json`. `TIMEOUT` / `timeout`, exit 3, branch null, one attempt. |

## Receipt redaction

DoD: receipt text is redacted (token, bearer, AKIA, private-key blocks). A receipt that contains those raw forms is a failed run.

| Command | Test | Receipt |
|---------|------|---------|
| `python3 -m unittest tests.test_pfy_build_cloud.CloudBuildFailureTests.test_receipt_redacts_tokens_keys_and_private_key_blocks` | That test, on this branch. Checker: `tests/test_mvp_1031_receipt.py` `CheckReceiptTests.test_rejects_secret_markers_in_pass_shaped_json` (rejects `AKIA`, `BEGIN PRIVATE KEY`, and `sk_` plus 8 characters). | GAP for a committed receipt that shows redaction succeeding. The realfail redaction receipt still has the planted `xai-` marker. Cloudfix adds `test_receipt_redacts_an_xai_marker_in_the_task_and_the_reply` on that branch and on realfail2. See GAP 4. |
| `python3 -m unittest tests.test_mvp_1031_realfail_receipts.RealfailReceiptTests.test_committed_report_matches_receipts_and_has_no_secrets` | On `origin/bot/mvp-realfail-1031` only (`tests/test_mvp_1031_realfail_receipts.py`). Also `test_planted_bad_receipt_is_rejected`. Not on this branch. | The realfail tree. A redaction row marked matching is rejected while the marker is still in the case directory (realfail handoff). |

## How a missing row fails and how it recovers

A GAP stays until a later branch commits the receipt or the test named above. Recovery is a new commit on that lane, then a recheck here: `git fetch` and `git grep` the test name, or `git cat-file -e <branch>:<receipt path>`. This lane does not copy `eval/` onto `bot/mvp-docs-1031`.

`tests/test_mvp_1031_realfail_receipts.py` on realfail is the fail/recover pair for a bad committed receipt: the planted bad file is rejected, and a temp receipt that matches the report is accepted.
