# Handoff: mvp3-followups-1031

Branch `bot/mvp3-followups-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp3-followups-1031`. Base `6664713`. No rebase, no force push, no PR, no merge, no tag. `origin/main` stayed `c0d38af` (ancestor of HEAD). No local model. No `./pfy build --local` trial. Pregate not run: this drop-in says the operator runs it, and a GitHub `Runner.Worker` was live (pid 3751002).

Exit: lane empty. The ten reviewer follow-ups are on this branch. The operator override (2026-10-31 16:40 PT) gave this lane the runner, the review tests, and `docs/ops/HANDOFF-mvp3-review-retry.md`. `bot/mvp-review-fix2-1031` is closed and is not the owner here. The integrator reconciles that branch later.

## Done

| Item | Commit | What landed |
|------|--------|-------------|
| Exit card | `0f6fa08` | Run log and decisions, before item edits |
| 1. Review cap | `d3e73f6` | Operator usage: review is on, cap is 3 files and 250 lines, a larger legitimate diff is `PASS-REJECTED` |
| 2. Scope skip | `d84e29f` | No `files:` line and no `--allow-path`: stderr and receipt `warnings` say `scope check skipped: no allow list`. A `files:` line or `--allow-path` stays quiet |
| 3. Test seam | `6da1cb3` | `PFY_LOCAL_BUILD_TEST_SEAM=1` gates stub binds and the inject write. Unset, both do nothing |
| 4. Self-review docs | `16f7c07` | The reviewer is the same `--model` as the agent |
| 4. Self-review receipt | `fa69cac` | `review.same_model` is true. `review.reviewer` is `same local model as the agent`. The review HTTP body uses that model |
| 5. Empty reviewed set | `d6de542` | Only excluded paths changed: `no-reviewable-change`, exit 1, no commit, not retried |
| 6. Ignored helper | `a077e72` | `test_ignored_helper_is_not_committed` expects only `commit-recheck-failed` |
| 7. Poster crash | `1fe4365` | No out file is `review-crashed`, one attempt, not retried. The crash env is ignored unless the seam is on |
| 8. Old handoff | `97c2236` | Lines 38, 45, and 51 of `docs/ops/HANDOFF-mvp3-review-retry.md` are superseded by mvp3-fix-1031 `582414b` |
| 9. Ubuntu skips | prior handoff, no code | Review E2E already runs with bwrap hidden. See below |
| 10. TMPDIR note | `6d562a1` | Current practice is `TMPDIR=$PWD/tmp` in the worktree |

Tip at this handoff is the commit that adds this file. The code commits above are the runtime and test SHAs.

## How each change fails and recovers

| Change | How it fails | Recovery |
|--------|--------------|----------|
| Cap text | An operator expects a 4-file green diff to PASS | Raise `--max-files` and `--max-lines`, or pass `--no-review` for the one-attempt path. The attempt receipt names the counts |
| Scope warning | No allow list, and a path the task never named is committed | Add a `files:` line or `--allow-path`. The warning then stays off. `--no-review` does not run the scope check, so it does not print the phrase |
| Test seam | A stray `PFY_STUB_*` or `PFY_LOCAL_BUILD_INJECT_EXTRA_STAGE` used to change a real run | Leave `PFY_LOCAL_BUILD_TEST_SEAM` unset. Both hooks do nothing. Set it to `1` only in tests. With the seam on, the inject still forces `scope-commit-mismatch` and the index is reset |
| Self-review receipt | A reader treats the model accept as a second person | `review.same_model` is true and `review.reviewer` names the same model. The review request uses the receipt `model` tag |
| Empty reviewed set | Only `.pytest_cache` (or tmp, bytecode) changed, and `git commit` used to fail as `commit-failed` | Reason is `no-reviewable-change`, exit 1, one attempt, no branch. The index is reset. Change a path the commit will keep |
| Ignored helper | The assertion stayed green for `scope-commit-mismatch`, which this path does not return | The test now requires `commit-recheck-failed`. The helper stays out of the commit. The archive recheck is what fails |
| Poster crash | No out file used to be `review-unparseable` and was retried | Reason is `review-crashed`, exit 1, one attempt, no commit. An HTTP body `{"error": ...}` stays `review-http-error` and is also not retried. A bad verdict stays `review-unparseable` and is still retried. `PFY_LOCAL_BUILD_REVIEW_CRASH=1` does nothing unless the seam is on, so a stray value cannot fail a real run |
| Superseded lines | A later reader treats the scope and commit mismatch as the next code fix | Those three sentences now name mvp3-fix-1031 `582414b`. t4 still needs a local run that writes the sub-step catch. That measurement is not this follow-up |
| TMPDIR note | A later lane writes scratch under the main checkout | Use `TMPDIR=$PWD/tmp` in that worktree |

## Item 6, the inversion

`0f0d889` renamed `test_ignored_helper_is_in_the_commit` to `test_ignored_helper_is_not_committed` on purpose. The old test proved `git add -A -f` committed a gitignored helper. The new test proves that helper stays out of the commit. `a077e72` pins the reason to `commit-recheck-failed` only. One run after the pin (`1.689s`, OK) returned that reason: git status hides the ignored helper, the commit is only `src/calc.py`, and the archive recheck fails because that file imports the missing helper. `scope-commit-mismatch` does not fire.

## Item 9, ubuntu skips

Unchanged from the earlier pass. The review E2E runs on an ubuntu-like PATH. With bwrap removed from PATH the review module ran 19 tests, skipped 0. It uses the stub opencode and the stub HTTP reviewer. It has no bwrap skip. This lane did not copy `tests/test_pfy_build_local_review_ci.py` from `bot/mvp-ci-cover-1031`.

The skips that show up on ubuntu and not on this nimo host are confinement and missing host tools: harness2 sandbox cases, the x-intake smokes that require bwrap, and the local-build sandbox escape cases. `docs/ops/PREGATE.md` says those tests skip on the pinned image. Do not install bwrap on the ubuntu job to unskip them. The close-out run below had bwrap present and skipped 0 of the review tests.

## Test evidence

Close-out, niced, stubs only: `python3 -m unittest tests.test_pfy_build_local_review tests.test_pfy_build_local.LocalBuildTests.test_ignored_helper_is_not_committed`. Ran 25 tests in 72.253s, OK. That is the review module (24, including the new scope, seam, same-model, empty-set, and crash tests) plus the pinned helper test.

Earlier targeted runs, all OK: scope phrase plus the review module, 20 tests in 81.384s; seam plus the review module, 21 tests in 82.336s; same-model plus the no-review pass, 2 tests in 3.445s; empty reviewed set plus the inject mismatch, 2 tests in 2.786s; helper pin, 1 test in 1.689s; crash plus unparseable retry plus HTTP error, 3 tests in 6.317s.

The kill-during-review test still prints a `BrokenPipeError` from the stub HTTP server when the client is killed. The test result is OK. That noise was already there.

## Skipped

| Item | Why |
|------|-----|
| Pregate | This drop-in says the operator runs `scripts/pregate.sh`. `Runner.Worker` pid 3751002 was also live. Pregate not run: host busy |
| t4 sub-step remeasure | Needs a real local model. This lane uses stubs only |
| A TODO row | `docs/TODO.md` is not a file this override assigned. The integrate lane owns that index |

## Cross-lane

The integrator reconciles this branch with the closed `bot/mvp-review-fix2-1031` (tip seen earlier: `8c40087`). Same seam name: `PFY_LOCAL_BUILD_TEST_SEAM`. Differences to keep when merging:

- This branch warns with the exact phrase `scope check skipped: no allow list` on stderr and in top-level `warnings`, and only when review reaches the scope check. Their earlier string was `no allow list: scope was not checked`.
- This branch also gates `PFY_LOCAL_BUILD_INJECT_EXTRA_STAGE` and `PFY_LOCAL_BUILD_REVIEW_CRASH` on that seam. Their seam gated only the stub binds.
- This branch does not add `sandbox_extra_rw` to the receipt. The seam-off test checks behavior: the inject file is absent, and under bwrap the stub cannot write its notes.
- `no-reviewable-change` and `review-crashed` are on this branch.

No request for review-fix2 to reimplement these. They are closed.

## Gate

This tip changes runtime (`scripts/pfy_build_local.py`) and tests. Gate: Tester plus Reviewer. Pregate is the operator's step, not a Feature GO. `./pfy build --local` stays opt-in. The local default stays NO-GO.

## Next

Tester plus Reviewer on `bot/mvp3-followups-1031`. Then the integrator reconciles with review-fix2. Do not rebase this branch. If `origin/main` moves, merge it.

## Finish

state: lane empty | tests: review module plus ignored-helper Ran 25 in 72.253s OK | files: runner, review tests, operator doc, review-retry handoff | err: none
