# Handoff: mvp-land-1031 (issue #306)

Lane for issue #306: land the 10/31 MVP stack. Worktree on nimo: `~/DEVELOP/pfy-mentat/tmp/mvp-merge-plan-1031/tmp/stack-after`. No PR. Not merged to `main` from this lane. Gate requests are not sent from this lane.

## SHAs

| What | SHA | Ref |
| --- | --- | --- |
| Rescued scratch tip (was detached, unpushed) | `cee9bdd92bce33df5a8c94c5c77eb376bc242dcd` | `bot/mvp-stack-1031` (stays here) |
| `origin/main` merged | `2a744823e05588e8d6331d511e2ec7fb77ec0ecb` | same as the PM note |
| Merge of main into the stack | `a2551f1e0512db7579ffd10b318cd5c8beb0421d` | `build/306-mvp-stack` |

The main merge was clean (`docs/TODO.md` auto-merged: main's PT/UTC close-date wording on four done rows; integrate's sections kept).

## Root cause notes (written before each fix)

The four red tests from `MERGE-PLAN-1031.md` "Still red on the stacked runner" reproduce at `a2551f1`: `Ran 20 tests, FAILED (failures=2, errors=2)` for the four harness modules. Each harness fails closed on an anchor that no longer occurs once. The runners are right; the catalogs were cut against pre-union text.

### 1. Cloud mutants C1-C16 (`test_catalog_applies_once_and_parses`)

Only C9 misses (count 0). `11bcb7d` (overlap the daily post-change gate and the flake gate) replaced the single `if state.pgid: _signal_pgid(state.pgid, ...)` in the signal handler with a loop over `state.child_pgids` plus the current pgid. Fix: re-cut C9 to disable that loop. Same intent: the interrupt handler no longer kills the process groups.

### 2. Cloud2 mutants C17-C43 (`test_wave5_mutants_each_apply_once_and_parse`)

Four miss (count 0):

- C22: `f4a64ec` changed the call to `self.recheck_sha(sha or "")`.
- C31: `7667b2e` put a TMPDIR comment and block between `env.pop(key, None)` and `run_command(`.
- C38: `11bcb7d` nested the communicate in an inner `try` (child tracking), so the `except subprocess.TimeoutExpired:` block is 4 spaces deeper.
- C39: `f4a64ec` plus the timeoutfix union added `_undo_commit(keep_edits=True)` and the `last_reject` branch to the review-timeout block.

Fix: re-cut the anchors to the current text. Each `new` keeps the original mutation (skip recheck; keep secret env; no pgid kill on timeout; timeout becomes a review reject).

### 3. Review mutants R1-R14 (`test_catalog_anchors_match_a_copy_of_the_runner`, `check_anchors` rc 1)

Four miss in `scripts/pfy_build_local.py`:

- R3, R4: `5cdc5c2` renamed the outage verdict to `reviewer-unavailable` and split it into a timeout branch and an HTTP/transport branch. The old `redact(detail)` block is gone. Re-cut both on the transport branch (the HTTP outage the mutants were written for).
- R11: `a516e8c` moved the `:!` excludes before the positive `:(literal)` pathspecs (git 2.53 drops an untracked path otherwise). Re-cut the first replacement to the new order.
- R14: `5d6d18b` folded the scattered `!= "1"` seam guards into `_test_seam_on()`. Re-cut R14 to make that predicate always on, so stub env is read in production.

### 4. Planted review diffs (`test_planted_set_shape_and_patches_apply`)

The test stops at the first miss (`b07-shell-rm`, `scripts/pfy_build_cloud.py:616`). Applying all 20 at `f4c317e`: 15 apply, 5 do not.

- b07, b09: context drift only. Later merges moved `diff_aims_at_root` (now line 638) and the attempt loop. The generator's edits still match once; only the saved hunks are stale.
- b08, g01 (`examples/x-intake-local/smoke_109_111.py`): `110f24a` rewrote `state_snapshot` to hash content via `os.lstat`, so the `if not p.exists(): ... newest = p.stat().st_mtime` text is gone. The generator also stops on its `snap` needle (`base missing snap needle`). g01's old task (use lstat on the root) is already what the code does.
- g04 (`examples/x-intake-local/smoke_149.py`): the same rewrite made `home_sig` lstat-based with `os.readlink` and a content hash, so the old `q.stat().st_size` shape (and the `149` needle) is gone, and the old task is already done.

Fix: in `eval/mvp-1031/review-quality/build_cases.py`, update the two needles and re-cut b08, g01, g04 against the current functions with the same label and the same kind of change (b08: drop the missing-path `None` branch, so a missing path is recorded as unreadable; g01 and g04: a no-behavior-change edit that matches its task). Keep ids, so the saved `results/before` and `results/after` rows still line up. Then regenerate all 20 diffs and `cases.json` with the generator. Do not hand-edit diffs.

### 5. Built-by subject check (`tests.test_selfhost_1031_log`, found by the full suite at `28daaa6`)

Not in the plan's red list, and already red at `cee9bdd` (the last merge of the stack is `bot/mvp-selfhost2-1031`). `test_this_branch_has_no_bad_built_by_trailer` walks every `Built-by: ./pfy build (cloud) receipt` commit in history and wants the subject to equal the task cut at 72 characters. 15 of the 36 trailer commits fail:

- 5 `dogfood3` commits (`2587cad`, `55ad1b1`, `4ef4c66`, `775e34b`, `98e5795`): the subject is exactly what the union runner writes. The dogfood fix changed `scripts/pfy_build_cloud.py` `commit_subject` to whole words plus `...`, so a mid-word cut no longer appears. The test's `expected_subject` is the pre-fix rule. The runner is right; the check is stale.
- 10 `selfhost2` commits (`4a0fe4e`, `cdf4d68`, `36bc071`, `ae5e5e5`, `9138656`, `1faa9fd`, `e6339ca`, `67e3333`, `d217349`, `3eeab42`): the lane cherry-picked each cloud build and gave it a readable subject, as its drop-in asked ("Commit with a clear message naming the item"). The receipts are PASS. On nimo each commit has the same `git patch-id --stable` as the receipt's `commit`, so the change is the cloud build's change; only the message differs. Those receipt commits are not on origin, so CI cannot repeat that check. History is not rewritten (no force-push).

Fix: the check accepts either runner rule (the old 72-character cut, still in history from the selfhost/dogfood2 lanes, or the current `commit_subject`). The 10 reworded selfhost2 SHAs get an exact-SHA list with the reason; for them only the subject comparison is skipped, and the trailer path, receipt presence and PASS status are still checked. Any new mismatch still fails.

## Fixture commits

| Commit | What |
| --- | --- |
| `6c1405e` | Planted set: `build_cases.py` needles updated, b08/g01/g04 re-cut (same ids), all 20 diffs and `cases.json` regenerated by the generator |
| `28daaa6` | Cloud C9 C22 C31 C38 C39 and review R3 R4 R11 R14 anchors re-cut (each `new` keeps the original mutation) |
| `b528486` | Built-by subject check (item 5 above) |

Who did the work: Hermes (`-z -m qwen3.6:35b`) took the mutant re-cut first and timed out after 45 minutes with no edits (its default `minimax-m3:cloud` returned nothing; an earlier log shows HTTP 402). Grok Build headless did the mutant re-cut (exit 0), reviewed line by line here. The planted re-cut and item 5 were small and done directly.

## Tests at `b528486`

Scope: `python3 -m unittest discover -s tests -t .` (the CI scope; fixture tests under `eval/` are not suites), `TMPDIR` under the worktree `tmp/`, host nimo with bwrap.

- `Ran 1372 tests in 993.210s` / `OK (skipped=16)`. At `28daaa6` the same run was `FAILED (failures=1, skipped=16)`, only item 5.
- Per-module counts: [mvp-land-1031-tests.txt](mvp-land-1031-tests.txt) (133 modules, from the unittest loader; skips counted from the log).
- The five re-cut checks: `test_mut_cloud_harness` 4, `test_mut_cloud2_harness` 3, `test_mut_review_harness` 6, `test_review_quality_replay` 7, `test_selfhost_1031_log` 3; all ok, none skipped. `eval/mutation-1031/review/run_mutants.py --check-anchors` prints `anchors 14 ok`.

## Fail/recover checks from MERGE-PLAN-1031 (still hold)

- Review timeout is `reviewer-unavailable`: `scripts/pfy_build_local.py` timeout and transport branches both return verdict and reason `reviewer-unavailable`.
- One `"warnings"` key: a single `"warnings"` entry in the local runner's result dict.
- `_undo_commit` before `as_reject`: `scripts/pfy_build_cloud.py` review-timeout block calls `self._undo_commit(keep_edits=True)` before `as_reject`.
- The recheck extract has its own git repo: the nested `git init -q` stays; `test_recheck_git_does_not_walk_up_to_the_caller_repo` is in the green run.

## Branch-delete list (step 6 of #306, only after `main` contains this stack)

Checked with `git merge-base --is-ancestor <tip> b528486` after `git fetch` on 2026-11-02. Re-check against `main` before deleting.

Ancestors (delete once `main` holds the stack): `bot/backlog-catalog-1030`, `bot/mvp-backlog-burn-1031`, `bot/mvp-ci-cover-1031`, `bot/mvp-cloud-1031`, `bot/mvp-cloud-perf-1031`, `bot/mvp-cloudfix-1031`, `bot/mvp-crosslane-1031`, `bot/mvp-daily-card-1031`, `bot/mvp-docs-1031`, `bot/mvp-docs-final-1031`, `bot/mvp-dogfood-1031`, `bot/mvp-dogfood-fix-1031`, `bot/mvp-dogfood2-1031`, `bot/mvp-dogfood3-1031`, `bot/mvp-dsv4-1031`, `bot/mvp-eval-1031`, `bot/mvp-followups-fix2-1031`, `bot/mvp-freshclone-1031`, `bot/mvp-gom-dogfood-1031`, `bot/mvp-integrate-1031`, `bot/mvp-local-t5-1031`, `bot/mvp-mutate-cloud-1031`, `bot/mvp-mutate-cloud2-1031`, `bot/mvp-mutate-preflight-1031`, `bot/mvp-mutate-review-1031`, `bot/mvp-pass3-review-1031`, `bot/mvp-plan-1031`, `bot/mvp-preflight-1031`, `bot/mvp-realfail-1031`, `bot/mvp-realfail2-1031`, `bot/mvp-realfail3-1031`, `bot/mvp-review-fix-1031`, `bot/mvp-review-fix2-1031`, `bot/mvp-review-quality-1031`, `bot/mvp-selfhost-1031`, `bot/mvp-sixtask-1031`, `bot/mvp-sixtask-int-1031`, `bot/mvp-stack-1031`, `bot/mvp-surface-1031`, `bot/mvp-tmpclean-1031`, `bot/mvp-tmpclean2-1031`.

Cherry-picked, subject check done (non-merge subjects missing from the stack):

| Branch | Missing | Decision |
| --- | --- | --- |
| `bot/mvp-intfix-1031` | 0 | delete after main holds the stack |
| `bot/mvp3-followups-1031` | 0 | delete after main holds the stack |
| `bot/mvp-probe-fix2-1031` | 3 | keep until those 3 are checked (tip moved after the cherry-pick) |
| `bot/mvp3-review-retry` | 1 (`d168446`, docs only; its file `HANDOFF-mvp3-fix2-1031.md` came in through `ff8b881`) | BX3 resolved: `3a550e5`, `0d3c0fc`, `0e683b9`, `ff8b881` cherry-picked onto this stack (Tester FAIL at `89cc0d2`, see B1 below). Delete after main holds the stack. |

Keep (commits after the 2026-10-31 18:20 PT freeze, not on this stack; a later lane must land or drop them): `bot/doctrine-commit-integrity-1031` (1), `bot/flake-pgrep-x-1031` (10), `bot/lessons-xstaging-1031` (1), `bot/mvp-backlog-fu-1031` (7), `bot/mvp-cloud347-1031` (15), `bot/mvp-dogfood4-1031` (22), `bot/mvp-dogfood5-1031` (15), `bot/mvp-dogfood6-1031` (26), `bot/mvp-flake-harness2-1031` (11), `bot/mvp-hermes-check-1031` (5), `bot/mvp-integrate-pass4-1031` (48), `bot/mvp-localbench-tmpdir-1031` (3), `bot/mvp-merge-plan-1031` (5, plan lane), `bot/mvp-pfy-followups-next-1031` (11), `bot/mvp-pregate-fixture-tmp-1031` (3), `bot/mvp-probe-int-1031` (7), `bot/mvp-probe-s2s5-1031` (14), `bot/mvp-selfhost2-1031` (10), `bot/mvp-tautology-scan-1031` (13), `bot/mvp-timeoutfix-1031` (1, handoff doc only), `bot/mvp3-s2s5-1031` (7). Counts are missing non-merge subjects.

### S1. Patch-ids for the 10 reworded Built-by commits (`b528486`)

`tests/test_selfhost_1031_log.py` `REWORDED_SUBJECTS` accepts these 10 stack commits, whose subjects differ from the cloud runner's subject. Each receipt names the commit the cloud runner made (`commit`). That commit is on no branch on origin (it lived on the lane's local `cloud/*` branch on nimo), so the subject cannot be compared there. The diff can: `git show <sha> | git patch-id --stable` is the same for the stack commit and the receipt commit in all 10 rows, so only the message changed. Recomputed on nimo on 2026-11-02.

| Stack commit | Receipt dir (`eval/selfhost2-1031/`) | Receipt `commit` | `patch-id --stable` | Receipt commit |
| --- | --- | --- | --- | --- |
| `4a0fe4eeebd2` | `01-ad-snap` | `35b758513b59` | `a8f753bf6787ebd6a549ae5e87955c9b244363b2` | same |
| `cdf4d681c19c` | `02b-kolibri-receipt` | `7a79465f4544` | `e20e3149f2c812c58c5909303b6e62cf75faf588` | same |
| `36bc071c3e82` | `03-typed-receipt` | `a586ad16cee9` | `7b440a5182510475a22ea846f8f86c6b11240e92` | same |
| `ae5e5e5e7459` | `04-adapter-hash` | `f11f7de07b3c` | `95fd165c5326d0bf053a5ee8d67a681c10d7283b` | same |
| `91386568b3c5` | `05-smoke140-hash` | `b9de401890a2` | `3730685bb7410c1147ca49dd73f137bf7e89f164` | same |
| `1faa9fd7e80b` | `06-smoke137-hash` | `fdef8d6f11c2` | `7f3a790fdc403cd739acf16af5c4798e5dbf5ea6` | same |
| `e6339ca3c6de` | `07-adapter-symlink-ops` | `e762c1aef89a` | `bfc57e5324a7f3fe383cad013bef11ebf44bf9ef` | same |
| `67e3333a76c3` | `08-surface-symlink` | `dff338cf6bf8` | `0e6f4ce86700748862329d36452ce865f6999dc4` | same |
| `d217349f1acc` | `09-install-symlink` | `89b35a5b6821` | `753d397bf8510701d92480e5d1d77d0c077f1b3b` | same |
| `3eeab428e879` | `10-hedge-ledger` | `e8cc4f32bca3` | `1726ad83ff6e833cafe0c724c47a9f70ef1e8404` | same |

Fail: a later rebase changes one of these diffs, and the allowlist still passes on SHA alone. Recover: rerun the loop above; any row that is not `same` is a new build and needs a new receipt, not an allowlist entry.

### S5. Pregate fail/recover notes (from `HANDOFF-mvp-followups-fix2-1031.md`)

- P2 failing lint: `PREGATE_IMAGE_PIN_ROOT`, when set, is the path linted by `scripts/check_workflow_image_pin.py`. A scratch copy of `tests/fixtures/workflow_image_pin/latest.yml` makes `scripts/pregate.sh --only lint` print `OVERALL=FAIL` with `unpinned GitHub-hosted runs-on (ubuntu-latest)`. Recover: pin the job to `ubuntu-24.04`, or unset the hook. A missing hook path fails closed.
- G1 root length: pregate refuses `RUN_ROOT` or `SCRATCH` longer than `PREGATE_MAX_ROOT_LEN` (default 60) with `path too long (N > LIMIT chars): <path>`, exit 2 before any check, no OVERALL line. A limit equal to the longer path passes and `--only lint` prints `OVERALL=PASS` (`test_root_path_at_the_limit_passes_the_guard`, which again asserts `PASS workflow image pin:`). Recover: a shorter checkout, or a higher `PREGATE_MAX_ROOT_LEN`.
- Shallow checkout: `--base` defaults to `origin/main`, which a `fetch-depth: 1` clone does not have, so pregate exits 2 `unknown base ref`. The image-pin tests pass `--base HEAD` (B2d). Recover for a real run: pass `--base <sha>` or fetch `origin/main`.

## Next

Pregate on the commit that adds this section, then Tester plus Reviewer at that SHA (behavior-changing code), then fast-forward `main`. This lane sends no gate request.

## Tester FAIL at `89cc0d2` (2026-11-02): root causes, written before the fixes

Write-up: https://github.com/themark-net/pfy-mentat/issues/306#issuecomment-6587809738. CI run 41510427750 (eval-structural, `workflow_dispatch` on `bot/mvp-land-1031`): nimo job 125500577002 had 3 failures, Ubuntu job 125500577122 (Python 3.12.15) had 15 failures and 11 errors.

### B1. BX3: the reviewer can be shown less than the commit stores

The stack has the mvp3 review-retry lane only up to the `16f17d8` era (its fixes were cherry-picked). The BX3 fix landed later on `bot/mvp3-review-retry` (`3a550e5`, test `0d3c0fc`, docs `0e683b9`/`ff8b881`, tip `4be797e`), after the plan's freeze, and the branch-delete list above wrongly parked it as "commits after the freeze" without naming BX3 or the open Tester FAIL. So `_review_prompt` still slices the diff to `DIFF_PROMPT_CAP` (`scripts/pfy_build_local.py:2740`), and a binary change reaches the reviewer only as `Binary files ... differ`. The Tester's h11 (long tail), h11b (many short lines) and h12b (tracked binary) runs committed content the reviewer never saw. Fix: cherry-pick `3a550e5` and `0d3c0fc` (and the two lane docs). They fail closed before the reviewer is called: `review-diff-too-large` over the cap, `review-binary-change` for a binary numstat or git's binary notice; no commit and no retry. Their E2E tests are the h11/h11b/h12b shapes. `_agent_prompt` (`:1155`) still trims the previous diff, but that is feedback to the builder on a rejected attempt, not what the reviewer approves.

### B2a. `test_dogfood2_1031_report` needs history

`eval/dogfood2-1031/check_reports.py` checks that each receipt's commit and its Built-by trailer exist in the repo. `eval-structural.yml` checks out with `fetch-depth: 1` on both jobs, so `31a863c` and the other build commits are absent, and both runners report `commit ... is not in the repo`. The pregate PASS ran in a linked worktree with full history, so it never saw this. Fetching full history in CI would hide the coupling instead of fixing it, and G0 is meant to be a fast tree check. Fix: the real-tree audit skips with a named reason when the repo is shallow and the commit is absent (it still runs, and must pass, wherever history exists, such as pregate in a full clone); the planted-mismatch case builds its own temp repo so it runs everywhere.

### B2b. `tests/test_pfy_local_build_eval.py:566`

`assertNotEqual(main, ROOT)` assumes the suite runs in a linked worktree (as every lane did). In a plain checkout (CI, a fresh clone) the main checkout is ROOT. Fix: drop that assumption; the test still proves the eval refuses scratch in the main checkout, which in a plain checkout is ROOT itself.

### B2c. `rglob(..., recurse_symlinks=False)` is Python 3.13+

Six example smokes (`smoke_112_114.py:126`, `smoke_115_116.py:128`, `smoke_117_118.py:86`, `smoke_119_121.py:95`, `smoke_148.py:135`, `smoke_149.py:135`) pass that keyword. Python 3.12 raises `TypeError`. nimo runs 3.14, so nimo was green. Fix: one stdlib walk that lists a symlink (to a file or directory) as an entry and never descends into it, on 3.12 and later, plus a test.

### B2d. Ubuntu-only failures

- x_intake smokes (`test_x_intake_smoke_112_114`, `_117_118`, `_119_121`, `_112_115_receipts`) and the home/tree signature tests (`test_home_sig_148`, `test_remaining_home_sigs`, `test_tree_sig_112/115/117/119`, `test_tree_sig_copies`): every traceback ends in the B2c `TypeError` (the timeout cases hit it in the post-timeout home check, so stderr shows `TimeoutExpired` chained to it).
- `test_workflow_image_pin` (4 tests): they run `scripts/pregate.sh --in-place --only lint`. Pregate resolves `--base` (default `origin/main`) before it looks at `--only`, and a fetch-depth 1 checkout has no `origin/main`, so it exits 2 (`unknown base ref`) with no OVERALL line. The tests only exercise lint, which never uses the base. Fix: those test invocations pass `--base HEAD`; pregate's documented exit 2 for an unknown base is kept.
- `CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same`: argparse in 3.13 prints `-p, --prompt PROMPT`; 3.12 prints `-p PROMPT, --prompt PROMPT`. The test pinned the 3.13 text. Fix: accept either spelling of the same option.
