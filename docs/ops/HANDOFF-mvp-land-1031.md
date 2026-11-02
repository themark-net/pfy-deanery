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

`b07-shell-rm.diff` no longer applies at `scripts/pfy_build_cloud.py:616`: later merges moved `diff_aims_at_root` (now line 638), so the hunk context and offsets are stale. Fix: regenerate all 20 diffs and `cases.json` with the repo generator `eval/mvp-1031/review-quality/build_cases.py`; do not hand-edit diffs.
