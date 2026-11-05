# Handoff: mvp-dogfood2-1031

Medium cloud dogfood lane. Branch `bot/mvp-dogfood2-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-dogfood2-1031`. Base `origin/bot/mvp-integrate-1031`. Exit: lane empty after 9 real cloud runs. Launch 2026-10-31T21:23:19Z. Close 2026-11-01T00:25:00Z. No merge, no PR, no tag.

Each run is `./pfy build "<task>"` from this worktree against a throwaway clone under `tmp/target-<n>`. No `--local`. Nothing from a target was pushed. A PASS this lane accepts is cherry-picked here with a Built-by trailer. The runner merged before each run was `origin/bot/mvp-cloudfix-1031`. Per-row SHA is in the report.

## Items done

| run | record | cloud commit | result |
| --- | --- | --- | --- |
| prep | 641be30 |  | loop card, decisions |
| 01-tree-sig-copies | f564621 | 31a863c | PASS exit 0 wall 398s review accept human yes |
| 02-pregate-orphans | c745784 | 42e4452 | PASS exit 0 wall 1490s review accept human yes |
| 03-receipts-outside | dd9a5bf | 507cfcf | PASS exit 0 wall 223s review accept human yes |
| 04-remaining-home-sigs | 7e2c5c1 | 3e4c7ba | PASS exit 0 wall 661s review accept human yes |
| 05-timeout-substep | 323dd6e | 26e71fa | PASS exit 0 wall 306s review accept human yes |
| 06-daemon-stop-timeout | c876db0 | 072c7cd | PASS exit 0 wall 301s review accept human yes |
| report-checker | 67ee5f8 |  | rows, rates, trailers; named in b14e4c3 |
| 07-hr-sigterm | 5d544b2 | none | TIMEOUT exit 3 wall 2942s review none human no |
| 08-hr-sigterm-exact | b052f15 | e8a216a | PASS exit 0 wall 891s review accept human yes |
| 09-state-snapshot | bea476d | 110f24a | PASS exit 0 wall 643s review accept human yes |

Rates: 9 runs, gate 8/9, review accept 8/9, human accept 8/9, median wall 643s. Sorted walls: 223, 301, 306, 398, 643, 661, 891, 1490, 2942. Detail is `eval/dogfood2-1031/REPORT.md`.

Cloudfix before the run: 01 to 06 `d35af20`, 07 `90d3c6e`, 08 `0dfc9d1`, 09 `8047018`.

Why each task was picked is in that run's `notes.md`. Short form: 01 three mtime `tree_sig` copies. 02 pregate orphan chdir plus reparent. 03 receipt dir on the 117 and 119 tests. 04 `tree_sig` on 117 and `home_sig` on 148 and 149. 05 timeout text names the sub-step. 06 daemon-stop timeout fails the overtime smoke. 07 SIGTERM cleanup with a leading-space gate, rejected. 08 the same cleanup with the exact argv. 09 `state_snapshot` in smoke_109 still stored the newest mtime.

## Skipped

Logged in `docs/ops/AUTONOMOUS-DECISIONS-mvp-dogfood2-1031.md`.

- T-0091 voice, shelved. T-0094 local TTS. T-0081 docker cage. T-0064 parked EBUSY. T-0043 parked write-guard. T-0062 Laguna hardware. T-0046 AgenC, ADR-0010. T-0016 and OQ-0008 hardware. T-0005 and OQ-0003 catalog stages.
- Dogfood1 tasks (stale enterable, enterable test, T-0110 status, pregate latest, board loaders, digest-after-add, pregate lock, splice close) and selfhost tasks (receipt dir, tree_sig mode and symlink, home_sig docstring, daemon-stop, receipt-148).
- `smoke_128_130.home_sig` includes mtime on purpose (`test_mtime_only_fails`).
- `scripts/smoke-product-levers.sh` already uses `mktemp -d -t`, so the old `/tmp` template is gone.
- harness2 "not-searchable dir" needs a human decision. OQ draft below.
- The mvp3 scope check versus `git add -A -f` lives in `scripts/pfy_build_local.py`, which this lane must not edit. On the cloud runner, task 03 did not commit a gitignored receipt.
- Assertion neutralization and the unsandboxed `--unsafe-no-sandbox` path stay with mvp-sandbox-gate-1031.
- HarnessRouter, Moira, and Kenfold happy paths need Docker on the box.
- Catalog files (`sources/entries/`, `TOOLS.md`, `data/tools.json`) and the runner files (`scripts/pfy_build_cloud.py`, `scripts/pfy_build_local.py`, `scripts/pfy`, `pfylib/build_preflight.py`, `eval/mvp-1031/**`).

After task 09 the remaining named gaps are in that list. Exit is lane empty. Turn cap was 12. Wall stop for new tasks was 2026-11-01T05:03:19Z. Three dogfood slots were unused.

## Test evidence

`nice -n 19 python3 -m unittest tests.test_dogfood2_1031_report` is 3 tests, OK, and prints `OK runs=9`. A planted status mismatch and a planted trailer mismatch each exit 1.

Per accept, the affected module was run niced with `TMPDIR` under this worktree:

| run | tests | result |
| --- | --- | --- |
| 01 | tests.test_tree_sig_copies | 5 OK |
| 02 | tests.test_pregate_orphans | 5 OK |
| 03 | tests.test_mvp2_t5_receipts plus two gitignore tests | 3 OK |
| 04 | tests.test_remaining_home_sigs, plus 148, 149, and 117 | 2 OK and 46 OK |
| 05 | tests.test_mvp2_t4_timeout_step plus 3 timeout tests | 5 OK |
| 06 | tests.test_mvp2_t3_daemon_stop plus the existing daemon-stop test | 2 OK |
| 08 | tests.test_hr_sigterm_exact plus 4 harnessrouter cleanup tests | 5 OK in 11.881s |
| 09 | tests.test_state_snapshot_109 plus tests.test_x_intake_smoke_109_111 | 14 OK in 3.014s |

Run 07's gate was red on purpose (`AssertionError: -15 != 1`) before the cloud run. The gate file stays at `eval/dogfood2-1031/07-hr-sigterm/gate.py` and is not under `tests/`. Receipts were scanned before commit. No AKIA, PEM, or key material is in the committed receipts. Run 09's `command.txt` matches the letters `sk-` only inside the filename `task-09.txt`.

## How this fails and recovers

The report checker fails when a run directory is missing from `REPORT.md`, when status, exit code, or review verdict disagrees with `receipt.json`, when the rate or median line disagrees with the table, or when a human-accept PASS commit lacks `Built-by: ./pfy build (cloud) receipt eval/dogfood2-1031/<dir>/receipt.json`. Recover by fixing the row or the trailer, then rerun the checker. The planted trees live under this worktree's `tmp/` and are not committed.

Product fails and the recovery that landed:

- 01 and 04. A same-size rewrite with the mtime restored compared equal. The value is now streamed bytes, lstat mode, and symlink text. A missing path is None. An unreadable file stays in the value.
- 02. A daemon that chdir'd away and reparented was invisible and was not signalled. `tracked`, `note`, `escaped`, and `signal_pids` cover that case. `pregate.sh` calls them.
- 03. The 117 and 119 tests could write a receipt inside the repo. They set `PFY_SMOKE_RECEIPT_DIR` to a temp directory.
- 05. A timeout reason did not name the sub-step. The festival version timeout returns 1 inside the `with`, with the step in the reason. The post-with real-HOME compare stays skipped, matching the old TimeoutExpired path.
- 06. A daemon stop timeout with the lock already gone still passed. The smoke now returns the stop text and exit 1. A live lock still wins.
- 07. SIGTERM during docker run returned -15, so the finally and the receipt never ran. Attempt 1 missed a correct `volume rm` line because the gate wanted a leading space. Attempt 2 logged `docker -- volume rm` and review rejected it. Attempt 3 hit the 1200s timeout. No commit. The red gate stayed off `tests/`.
- 08. The same SIGTERM gap, with the logged lines required to be exactly `rm -f pfy-hr-smoke` and `volume rm -f pfy-hr-smoke`. The handler raises, the existing finally removes both, and the function returns 1 with a reason that contains SIGTERM. Passed on attempt 1.
- 09. `state_snapshot` kept only the newest mtime. It now stores one hash per path (streamed bytes, lstat mode, symlink text) or None when the path is missing. mtime stays outside the value. Symlinks stay unfollowed. The no-bwrap real-home snapshot test still passes. The smolvm functions in that file were left as they were.

A cloud commit was amended only to append the Built-by trailer. The 72 character subject was left as the runner wrote it. Produced code was not hand-edited. Run 02's noqa comment contains an em dash from the model. It is still in the file.

## Cross-lane requests

For mvp-cloudfix-1031. The same three rows are in `eval/dogfood2-1031/REPORT.md`.

1. F1, medium, all nine runs. Stop cutting the cloud commit subject at 72 characters. The slice is `redact(" ".join(self.args.task_text.split())[:72])` in `scripts/pfy_build_cloud.py`. Runs 01 and 04 share a subject. Run 08 ends at "harne". Run 09 ends at "records only".
2. F2, medium, run 02. Record `review.truncated` on the receipt. The largest patch in the 60 to 250 line band is 10454 characters. `DIFF_CAP` is 12000. This lane cannot prove the cap from the line band alone. No run truncated.
3. F3, high, run 07. Keep the unified diff of a review-rejected attempt on the receipt. Attempt 2 passed a weak substring with `docker -- volume rm`. Review rejected it. Attempt 3 timed out and the runner removed the worktree, so the receipt has prose only.

The mvp3 "gitignored receipt rides in via `git add -A -f`" hole did not reproduce on task 03. The cloud runner adds named paths and checks the cached names.

## OQ draft

Not filed in `docs/OPEN_QUESTIONS.md`. That index is shared, and this lane does not own it.

`examples/harness2-local/sandbox.py` prunes a directory on a read-only mount when the directory is not executable or not readable, so `find` does not exit 1. The comment names the gap: a mode 751 directory (searchable, unreadable, like `/etc/sssd`) is skipped, while a host socket inside it stays connectable by name. Fail-closed would also block ordinary mode 751 directories. Question: should that prune fail closed, and which directories are the allowlist? This lane did not change the prune.

## Gate

Tester plus Reviewer. This branch changes runtime product code: `scripts/pregate.sh`, `scripts/pregate_orphans.py`, and the x-intake smokes `smoke_109_111.py`, `smoke_112_114.py`, `smoke_115_116.py`, `smoke_117_118.py`, `smoke_119_121.py`, `smoke_122_124.py`, `smoke_148.py`, and `smoke_149.py`. It also changes tests, `eval/dogfood2-1031/`, and these ops notes. The runner files were merged from cloudfix and were not hand-edited here.

Pregate not run: host busy. At 2026-11-01T00:23:34Z `Runner.Worker` was empty. At 2026-11-01T00:24:42Z `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` was held by another lane's `./scripts/pregate.sh 1f3b1a3`. This lane did not take the lock and did not start a second pregate.

`.project-map/index.html` was left as it was. Other lanes were inside `./pfy build` and that pregate, so this lane did not start a second Grok to redraw the map.

## Next step

Leave this branch unmerged. mvp-cloudfix-1031 can take F1, F2, and F3. When integrate collects branches, merge `bot/mvp-dogfood2-1031` after the runner fixes if those findings should be on the same tree. The throwaway clones under `tmp/target-<n>` are local and gitignored. Their gate commits (including `3673e15` on target-09 and `f033d34` on target-07) stay off this branch.
