# Handoff: mvp-pass3-review-1031

Exit: lane empty. The reviewer pass over `git diff origin/main...origin/bot/mvp-integrate-1031` is filed, and the two small findings in a file this lane may edit are fixed and pushed. Wall clock and host pressure did not fire. No question was asked. No merge, no PR, no tag, no force push.

Launch: 2026-11-01T00:35:37Z. Finish check: 2026-11-01T00:54:29Z. MemAvailable about 68 GiB. Load about 5.7 on 32 cores. Stop-new-items bound is 2026-11-01T08:15:37Z.

Branch: `bot/mvp-pass3-review-1031`. Base: `origin/bot/mvp-integrate-1031` at `1dee0b9`. Review range merge-base: `origin/main` at `c0d38af`.

## Items done

| Item | SHA | Tests | Result |
|------|-----|-------|--------|
| Exit card before the review | `5b0e04fb115eb44edff69a33be3997104d148e5b` | none (docs) | pushed |
| Findings table | `9d230872ef33fd3c691bed3e41425bcea50c4d81` | none (docs) | 7 rows in `docs/ops/REVIEW-pass3-1031.md` |
| Finding 5: echoed apt install | `99016b981666e9a71c324736d2b11931755f193b` | `tests.test_workflow_image_pin` ripgrep cases | was red (helper PASS), then OK |
| Finding 6: echoed rg run | `430d49adfbfc1bce0cd1b52f8453c34ce9fba4cd` | `tests.test_workflow_image_pin` | was red (helper PASS), then 33 OK in 19.925s |

## Skipped

- Findings 1 and 2 (`scripts/pfy_build_local.py` review code). Live lanes mvp3 and mvp-probe-fix2 own that file. Written up. Not edited.
- Findings 3, 4, and 7 (`scripts/pfy_build_cloud.py`). Live lanes mvp-timeoutfix-1031 and mvp-cloud-perf-1031 own that file. Each fix is small. Ownership wins. Not edited.
- `command echo` and `busybox echo` still count as a real command in `_command_is_echo`. Not filed. Covering every wrapper is a shell parser. Decision 7 in `docs/ops/AUTONOMOUS-DECISIONS-mvp-pass3-review-1031.md`.
- Line-by-line read of the 389 `eval/` paths and of every one of the 68 test modules. Control-flow files and a whole-diff secret / `/tmp` / swallow scan were done. Unread receipts stay a coverage limit, copied below.
- Pregate not run. The drop-in forbids `scripts/pregate.sh`. At finish, `pgrep -f 'Runner[.]Worker'` was empty, so the shared-host rule would have allowed one pregate. The lane ban stands.
- Full `unittest discover` not run. This lane's evidence is the targeted image-pin module. No red-base failure was observed on that module.

## Test evidence

- Finding 5, before the fix: `test_echo_of_apt_install_does_not_count_as_install` failed because the helper printed `PASS workflow image pin` and exited 0.
- Finding 5, after the fix: the six ripgrep cases in `tests.test_workflow_image_pin` passed (commit `99016b9`).
- Finding 6, before the fix: the same helper PASS on `echo rg --version` with a real apt install line.
- Finding 6, after the fix, this turn: `TMPDIR=$PWD/tmp nice -n 19 python3 -m unittest tests.test_workflow_image_pin`. 33 tests, 19.925s, OK. The new test loops `echo rg --version`, `sudo echo rg --version`, and `printf rg --version`.
- Findings 1, 2, 3, 4, and 7 have no new test from this lane. The integrate tree's existing tests were not re-run for those rows.

## How each change fails and recovers

- Finding 5. Fail: a workflow step that only echoes `apt-get install -y ripgrep`, then really runs `rg --version`, used to pass the structural check. Recover: `_installs_ripgrep` skips a line whose command is `echo` or `printf`, including `sudo echo`. The helper exits nonzero and says `does not install ripgrep`. A real `sudo apt-get install` line plus a real `rg --version` still passes (`test_apt_install_and_rg_version_passes`).
- Finding 6. Fail: a real apt install plus `echo rg --version` used to pass, so the check never required rg to run. Recover: `_runs_rg` uses the same skip. The helper says ripgrep was installed but rg was not run (`does not run rg`). `rg --version` and `command -v rg` on their own lines still count.
- A line that both echoes and really installs is skipped. That fails closed: the check asks for a real install line.
- Docs-only rows (exit card, findings table, this handoff) have no runtime fail path. A missing findings row would leave the table short of the seven defects confirmed on the integrate tip.

## Cross-lane requests

Exact rows are in [REVIEW-pass3-1031.md](REVIEW-pass3-1031.md). Do not treat `tree_digest` as missing. It runs, and it still does not close finding 2.

- mvp3 and mvp-probe-fix2, finding 1 (B, their BX2): `scripts/pfy_build_local.py:2386`. `_collect_diff` follows a symlink to a file and puts the target bytes in the reviewer diff and `patch.diff`. If the path is a symlink, do not read the target.
- mvp3 and mvp-probe-fix2, finding 2 (B, their BX1): `scripts/pfy_build_local.py:3346`. The reviewed diff is captured before `_gate_run` (3398). `tree_digest` at 3452 is after the gate. The compare at 3598 only sees edits after that digest. Digest each to-be-committed file after review and refuse when those bytes differ (`gate-modified-reviewed-file`).
- mvp-timeoutfix-1031 and mvp-cloud-perf-1031, finding 3 (S): `scripts/pfy_build_cloud.py:614`. `diff_aims_at_root` matches a deleted `rm -rf /` and a context line, so a patch that removes the command is rejected. Consider only lines that start with `+` and are not `+++`. Keep the absolute-path match, including `rm -rf /tmp/x`.
- Same lanes, finding 4 (S): `scripts/pfy_build_cloud.py:83` and `_protected` at 316. `.env.bak` and `.env.local` are not protected. Treat a basename of `.env` or `.env.*` other than `.env.example` as protected. Behavior test: a stub that writes `.env.bak` gets `protected-path-changed`, no branch, and the secret text stays out of the receipt.
- Same lanes, finding 7 (N): `scripts/pfy_build_cloud.py:1503`. `reap` swallows `OSError` while writing the ABORTED receipt for a dead pid and still returns 0. Print the receipt error and return exit 1 when that receipt was required and not written.

## Gate

Tester plus Reviewer. Findings 5 and 6 change runtime behavior in `scripts/check_workflow_image_pin.py` and add behavior tests. The findings table is docs and needs Reviewer as well.

Pregate not run: drop-in forbids `scripts/pregate.sh`.

## Next step

Stop this lane. mvp3 or mvp-probe-fix2 applies findings 1 and 2. mvp-timeoutfix-1031 or mvp-cloud-perf-1031 applies findings 3, 4, and 7. No further review defect in a file this lane may edit was confirmed.

## Coverage limit

Read for control flow: `scripts/pfy_build_cloud.py`, `pfylib/build_preflight.py`, `scripts/check_workflow_image_pin.py`, `scripts/catalog_stage_eval.py` evidence helpers, `scripts/pfy` `cmd_build`, `scripts/pfy_build_local.py` diff collection and the review/commit loop, `pfylib/attach.py` session reach, `eval/mvp-1031/check_receipt.py`.

Whole-diff scan for secret shapes, `/tmp`, and `except` then `pass` (219 raw hits, mostly docs, eval receipts, and the intentional leaker). The 389 `eval/` paths were not read line by line. Not every one of the 68 test modules was read in full, so a tautological test outside the modules named in the review can still exist.
