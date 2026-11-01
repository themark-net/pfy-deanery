# REVIEW pass 3 (2026-10-31)

Reviewer pass over `git diff origin/main...origin/bot/mvp-integrate-1031` at `1dee0b9` (522 commits, 619 files). This lane is `bot/mvp-pass3-review-1031`.

Severity: **B** blocker (wrong behavior, fail-open, secret, or a test that cannot catch its bug). **S** should-fix. **N** nit (dead code, doc that contradicts code, small scratch miss).

A live lane owns `scripts/pfy_build_local.py` (mvp3 and mvp-probe-fix2) and `scripts/pfy_build_cloud.py` (mvp-timeoutfix and mvp-cloud-perf). Those rows are cross-lane. This lane does not edit them.

## Findings

| # | Sev | File:line | Why | Fix |
|---|-----|-----------|-----|-----|
| 1 | B | `scripts/pfy_build_local.py:2386` | `_collect_diff` treats a symlink to a file as in-tree. `Path.is_file()` follows the link, then `read_text` puts the target bytes into the reviewer diff and `patch.diff`. An outside target is reviewed and can be committed as if it lived in the worktree. | Cross-lane mvp3 / mvp-probe-fix2 (their BX2). In `_collect_diff`, if the path is a symlink, do not read the target. Count it out of scope and keep the target bytes out of the prompt and every receipt file. Not edited here. |
| 2 | B | `scripts/pfy_build_local.py:3346` | The reviewed diff is captured before `_gate_run` (3398). `tree_digest` at 3452 runs after that gate. The later compare (3598) only notices edits made after that post-gate digest. A gate that rewrites a reviewed file changes the bytes that will be committed and does not change the diff the reviewer accepted. | Cross-lane mvp3 / mvp-probe-fix2 (their BX1). Digest each to-be-committed file after review and refuse the commit when it differs from the reviewed bytes (`gate-modified-reviewed-file`). Not edited here. |
| 3 | S | `scripts/pfy_build_cloud.py:614` | `diff_aims_at_root` says it matches an added line aimed at the filesystem root. The regex runs on the whole diff, so a deleted `rm -rf /` and a context line both return true. A patch that removes the dangerous command is rejected. The same regex also matches `rm -rf /tmp/x`, which is fail-closed and should stay. | Cross-lane mvp-timeoutfix / mvp-cloud-perf. Inside `diff_aims_at_root`, consider only lines that start with `+` and not `+++`. Keep the absolute-path match. Not edited here. |
| 4 | S | `scripts/pfy_build_cloud.py:83` | `DEFAULT_PROTECT` covers `auth.json` and `.env`. `_protected` (316) does not cover `.env.bak` or `.env.local`, including under a subdirectory. A cloud attempt can commit those files. Confirmed: `_protected(".env")` is true and `_protected(".env.bak")` is false. | Cross-lane mvp-timeoutfix / mvp-cloud-perf. In `_protected`, treat a basename of `.env` or `.env.*` other than `.env.example` as protected. Behavior test: a stub that writes `.env.bak` plus a normal file gets `protected-path-changed`, no branch, and the secret text stays out of the receipt. Not edited here. |
| 5 | S | `scripts/check_workflow_image_pin.py:245` | `_installs_ripgrep` token-searches the line. `echo apt-get install -y ripgrep` counts as an install. With a real `rg --version` on the next line, `eval-structural.yml` would pass the ripgrep check without installing anything. | Fixed in this lane. A line whose command is `echo` or `printf`, including `sudo echo`, does not count. A real `sudo apt-get install ripgrep` on its own line still counts. Test: `test_echo_of_apt_install_does_not_count_as_install`. |
| 6 | S | `scripts/check_workflow_image_pin.py:257` | `_runs_rg` treats `echo rg --version` as an invocation. Paired with a real apt install, the structural workflow passes without running rg. | This lane. Same echo / printf skip inside `_runs_rg`. `rg --version` and `command -v rg` on their own lines still count. |
| 7 | N | `scripts/pfy_build_cloud.py:1503` | `reap` swallows `OSError` while writing the ABORTED receipt for a dead pid, then still returns 0. The operator can see `reaped` and have no receipt. | Cross-lane mvp-timeoutfix / mvp-cloud-perf. Print the receipt error and return exit 1 when the abort receipt was required and not written. Not edited here. |

## Checked and not filed

- Secrets: a scan of added lines found no live key material. Hits are the redaction literals (`BEGIN PRIVATE KEY`, `AKIA` fixture) and the receipt checker. Values were not copied into this file.
- `/tmp`: cloud and local runners keep worktrees under the repo `tmp/` and set `TMPDIR` there. `scripts/smoke-product-levers.sh` and `scripts/eval-auto.sh` use `mktemp` so `TMPDIR` is honored. `tests/support_tmpclean_leaker.py` writes `/tmp` on purpose. Doc mentions of `/tmp` are not product writes.
- `classify_runner_failure` maps `not signed in` on exit 0 and exit 1 to `unauthenticated`. That matches the cloudfix handoff. `auth.json` on exit 0 stays `other` via `pfylib/build_preflight.py`.
- `tests/test_entry_149_count.py` compares the published count to the live `test_` methods. That can fail when they diverge. It is not tautological.
- Receipt checker tests run `check_receipt.py` and the add fixture. They are not self-comparisons.
- No dead function was confirmed in the files read below.

## Coverage

Read for control flow: `scripts/pfy_build_cloud.py` (resolve, protect, redact, review parse, execute, reap), `pfylib/build_preflight.py`, `scripts/check_workflow_image_pin.py`, `scripts/catalog_stage_eval.py` evidence helpers, `scripts/pfy` `cmd_build`, `scripts/pfy_build_local.py` diff collection and the review/commit loop, `pfylib/attach.py` session reach, `eval/mvp-1031/check_receipt.py`.

Whole-diff scan for secret shapes, `/tmp`, and `except` then `pass` (219 raw hits, mostly docs, eval receipts, and the intentional leaker). The 389 `eval/` paths were not read line by line. Not every one of the 68 test modules was read in full, so a tautological test outside the modules above can still exist.
