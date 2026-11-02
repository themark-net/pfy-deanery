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
