# Handoff: mvp3-followups-1031

Branch `bot/mvp3-followups-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp3-followups-1031`. Base `6664713`. Drop-in parent `a9dc798`. No rebase, no force push, no PR, no merge, no tag. `origin/main` stayed `c0d38af` (ancestor). No local model. No `./pfy build --local` trial. Pregate not run: this drop-in says the operator runs it, and the heavy lock was already held.

Exit: lane empty. The code follow-ups sit in files `bot/mvp-review-fix2-1031` owns. This lane did not edit them.

## Done

| Item | Commit | What landed |
|------|--------|-------------|
| Exit card | `0f6fa08` | Run log and decisions, before item edits |
| 1. Review cap | `d3e73f6` | Operator usage: review is on, cap is 3 files and 250 lines, a larger legitimate diff is `PASS-REJECTED` |
| 4. Self-review, docs | `16f7c07` | Same usage section: the reviewer is the same `--model` as the agent |
| 10. TMPDIR note | `6d562a1` | Current practice is `TMPDIR=$PWD/tmp` in the worktree |
| 6. Inversion note | `309d4ec` | The test was renamed on purpose. Live reason is `commit-recheck-failed`. The assertion was not pinned |
| 9. Ubuntu skips | this handoff | Review E2E already runs with bwrap hidden. No code change |

## How each docs change fails and recovers

| Change | How it fails | Recovery |
|--------|--------------|----------|
| Cap text | An operator expects a 4-file green diff to PASS | Raise `--max-files` and `--max-lines`, or pass `--no-review` for the one-attempt path. The attempt receipt names the counts |
| Self-review text | A reader treats the model accept as a second person | The usage doc says it is the same model. The receipt still has only the `model` tag until the owning lane adds a label |
| TMPDIR note | A later lane follows the old line and writes scratch under the main checkout | Use `TMPDIR=$PWD/tmp` in that worktree. The relative-outdir failure is environmental. Record it. Do not point `TMPDIR` at `~/DEVELOP/pfy-mentat/tmp/pgs` |
| Ignored-helper note | The assertion stays green for `scope-commit-mismatch`, which this path does not return | Pin `commit-recheck-failed` in the owned test. Until then the note is the record |

## Item 6, the inversion

`0f0d889` renamed `test_ignored_helper_is_in_the_commit` to `test_ignored_helper_is_not_committed` on purpose. The old test proved `git add -A -f` committed a gitignored helper. The new test proves that helper stays out of the commit. The assertion still accepts either `commit-recheck-failed` or `scope-commit-mismatch`. One run (`1.099s`, OK) returned `commit-recheck-failed`: git status hides the ignored helper, the commit is only `src/calc.py`, and the archive recheck fails because that file imports the missing helper. `scope-commit-mismatch` does not fire. Pinning the assertion is a cross-lane request. `tests/test_pfy_build_local.py` is owned by `bot/mvp-review-fix2-1031`.

## Item 9, ubuntu skips

The review E2E runs on an ubuntu-like PATH. `tests.test_pfy_build_local_review` with bwrap removed from PATH: Ran 19 tests in 60.511s, OK, skipped 0. The module uses the stub opencode and the stub HTTP reviewer. It has no bwrap skip. No code change. `bot/mvp-ci-cover-1031` already added `tests/test_pfy_build_local_review_ci.py` on that branch (17 tests, skipped 0, in their handoff). This lane did not copy it. The `tests/test_pfy_build_local_*.py` glob is owned by review-fix2.

Full `unittest discover` was not run. `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` was held by `scripts/pregate.sh 6664713` (pid 3498221, elapsed about 19 minutes when checked) and a waiter for `t4-timeout-substep`. The nimo number skipped=16 is the mvp3-fix-1031 suite on this host with bwrap present (Ran 967, failures=1, the known in-repo TMPDIR outdir case).

Bwrap-hidden runs on this tree, targeted, not the whole suite:

| Module | Skipped | Why | Runs on ubuntu? |
|--------|---------|-----|-----------------|
| `tests.test_pfy_build_local_review` | 0 of 19 | Stub opencode and stub reviewer | Yes |
| `tests.test_pfy_local_build_eval` | 0 in the combined 167 | Missing bwrap sets `PFY_LOCAL_BUILD_UNSAFE_NO_SANDBOX=1` and the tests still run | Yes |
| `tests.test_harness2_local_sandbox` | 40 | `bwrap required: not on PATH (GitHub-hosted ubuntu runners have none)` | Those 40 skip |
| same module | 1 + 1 | harness2 not staged, stage venv absent | Also skips on this nimo host |
| `tests.test_harness2_local_drive` | 5 | harness2 not staged, checked before bwrap | Also skips here. A staged nimo checkout would then skip them for missing bwrap |
| `tests.test_x_intake_smoke_149` | 16 | `SKIP: bwrap-missing; confinement was not demonstrated` | Those 16 skip. The no-bwrap exit path still runs |
| `tests.test_x_intake_smoke_148` | 10 | same confinement skip | Those 10 skip |
| `tests.test_x_intake_smoke_146_147` | 16 | `the hiroute smoke needs a working bwrap` | Those 16 skip |
| `tests.test_pfy_build_local` | 10 of 10 selected | 4 LocalBuildTests plus 6 SandboxEscapeTests, `SKIP: bwrap-missing` | Those 10 skip. The rest of the module does not use that guard |

That is 92 tests that skip only because bwrap is missing (40+16+10+16+10). Added to the 16 that already skip on nimo with bwrap present, the ubuntu-like total is about 108. Two more skip on real ubuntu-24.04 if `grok` and `opencode` are absent: `CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same` (`SKIP: grok-missing`) and `test_real_opencode_accepts_the_flags_we_pass` (`SKIP: opencode-missing`). This host has both, so the bwrap-only PATH mirror still runs them. The reviewer's "about 104 against 16" is that band. The gap is confinement and missing host tools, not the review loop.

Do not install bwrap on the ubuntu job to unskip confinement tests. `docs/ops/PREGATE.md` says those tests skip on the pinned image.

## Cross-lane requests

Owner for the runner and the review tests: `bot/mvp-review-fix2-1031`. At this handoff their tip is `8c40087` (wave 4 close). An earlier look saw `c114c7f`. Fetched before this commit: the MVP-3 handoff still has the open scope sentences, the ignored-helper assertion still accepts both reasons, the inject env is still read without the seam, and there is still no `no-reviewable-change` and no `review-crashed`. Do not treat this branch as having made these code changes.

1. Item 2. When there is no `files:` line and no `--allow-path`, stderr must say `scope check skipped: no allow list`, and the top-level receipt must show that same phrase. Today `_check_scope` sets `skipped: no-allow-list` on the attempt check and nothing is printed. review-fix2 `cef308c` uses a different warnings string (`no allow list: scope was not checked`). Test both the bare task and a task that has `files:` or `--allow-path`.
2. Item 3. One test-only env var, off by default, must gate both hooks. `_stub_extra_rw` still reads `PFY_STUB_PLAN`, `PFY_STUB_COUNT`, and `PFY_STUB_PROMPTS` in production. `_stage_reviewed` still writes `injected-extra.txt` when `PFY_LOCAL_BUILD_INJECT_EXTRA_STAGE=1`. review-fix2 gates only the stub binds behind `PFY_LOCAL_BUILD_TEST_SEAM=1` (`8dd5baf`). The inject hook is still open. Test: switch unset, both hooks do nothing; switch set, the existing tests still bind and inject. Document the variable name.
3. Item 4, receipt only. Docs are `16f7c07`. The receipt `review` object does not say the reviewer is the same model. Add that on the receipt, for example `review.same_model: true` next to the existing `model` tag.
4. Item 5. Only excluded paths changed (the reviewed name set is empty) must not reach `git commit`. Reason `no-reviewable-change`, exit 1, no branch. Today an empty wanted list falls through and a failed `git commit` is `commit-failed`.
5. Item 6. Pin `test_ignored_helper_is_not_committed` to `commit-recheck-failed` only. The either-or is what the reviewer flagged. The rename was intentional. See the section above.
6. Item 7. A poster that writes no out file (python missing, or the script dies before `open(out)`) must fail closed as `review-crashed` or `review-http-error`, exit 1, one attempt, no commit. Today `OSError` on `pfy-review-out.json` falls back to stdout plus stderr, `_parse_verdict` returns `review-unparseable`, and the loop retries that like a reject. An HTTP body `{"error": ...}` is already `review-http-error` and is not retried. The crash with no file is the hole.
7. Item 8. `docs/ops/HANDOFF-mvp3-review-retry.md` is on their owned list. Lines 38, 45, and 51 still say the scope check and `git add -A -f` disagree, and "Next code fix, not done here". Mark those sentences superseded by mvp3-fix-1031 `582414b` (`0f0d889` stages only reviewed paths). review-fix2 added a Review defaults section and did not mark these lines.
8. `docs/TODO.md` is owned by `bot/mvp-integrate-1031`. This lane did not add a row. If a row is wanted, one line: reviewer follow-ups 2, 3, 5, 6, 7, and 8 are waiting on `bot/mvp-review-fix2-1031`.

## Gate

This branch changes docs only. No runtime change. Gate: pregate plus Reviewer. The operator pregates the tip. Do not treat this handoff as a Feature GO. `./pfy build --local` stays opt-in. The local default stays NO-GO.

The code requests above, once they land on the owning branch, need Tester plus Reviewer.

## Next

Lane empty here. Next step is the owning lane, or the integrator, landing the seven code and handoff requests above. Then Tester plus Reviewer on that tree. This branch can merge as docs whenever pregate and Reviewer accept `bot/mvp3-followups-1031`.

## Finish

state: lane empty | tests: review module 19 OK skipped 0 in 60.511s with bwrap hidden | files: docs | err: none
