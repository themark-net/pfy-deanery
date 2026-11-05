# Handoff mvp-probe-fix2-1031

Lane empty at 2026-11-01T01:05:34Z. The 8 hour cap (new items stop 2026-11-01T08:15:26Z) had not fired. Base `origin/bot/mvp3-review-retry` was still `d2521b5` when `915edf0` was pushed. This lane pushed only `bot/mvp-probe-fix2-1031`.

Probe target: the mvp3 fix2 tip `d2521b5`. Scratch results live in gitignored `tmp/probe/results.jsonl` (29 CLI probes, then a rerun of the two hardlink probes with a fake `bwrap` on `PATH`). Evidence copied for reading from `/home/mark/DEVELOP/pfy-mentat/tmp/mvp3/tmp/evidence/mvp3-6664713`.

## Items done

| Item | SHA | Tests | Result |
|------|-----|-------|--------|
| Exit card | `8ce94e3` | none | pushed before probe work |
| BX1 executable bit | `29da017` | `tests.test_pfy_build_local_review` | pass. Reason `gate-modified-reviewed-file` |
| BX2 hardlink outside the worktree | `915edf0` | same module, 38 OK in 84.393s | pass. Reason `hardlink-outside` |
| Operator guard rows | this handoff commit | docs only | digest row names the git mode token; new `hardlink-outside` row |
| Handoff | this commit | docs only | probe table below |

## Probe table

Result at tip means the scratch CLI against `d2521b5` (stub builder, default accept reviewer), before `29da017` and `915edf0`. Finding SHA is the commit on this branch that makes that probe fail closed. `hold` means the tip already did the right thing, or the flag was the judge or the host.

| Probe | Result at tip `d2521b5` | Finding SHA |
|-------|-------------------------|-------------|
| e5c-gate-rewrite | FAIL `gate-modified-reviewed-file`, no commit, no leak | hold (base `4c7c5f6`) |
| g1-symlink-in-scope | PASS-REJECTED `review-rejected`, no leak, 1 attempt | hold (base `90b51f3`) |
| g2-symlink-out-of-scope | PASS-REJECTED `review-rejected`, no leak, 3 attempts, `review.retries` 2 | hold (base `90b51f3`) |
| s7-rename | PASS. A `src/new.py`, D `src/old.py`, M `src/calc.py`. Body `X = 1` | hold (base `3392e78`) |
| s7-rename-plus-edit | PASS. Body and prompt contain `EDITED_RENAME_LINE` | hold |
| s7-rename-across-dir | PASS. `src/sub/new.py` body `EDITED_RENAME_LINE` | hold |
| s7-rename-low-similarity | PASS. Prompt contains `EDITED_RENAME_LINE`. Judge flag was a false positive (decision 6) | hold |
| s7-rename-old-not-allowed | PASS-REJECTED, no commit | hold |
| s7-swap-two-files | PASS. Bodies swapped. Prompt contains `SWAP_A` and `SWAP_B` | hold |
| s8-unicode-nfc | PASS. `src/café.py` body `N = 1` | hold (base `301f786`) |
| s8-unicode-nfd | PASS. NFD name, body `NFD = 1` | hold |
| s8-nfc-allow-nfd-file | PASS-REJECTED, NFD path outside the allow list, no commit | hold |
| s8-nfc-and-nfd-both | PASS with one directory entry. Host ZFS normalization is formD (decision 7) | hold |
| s8-emoji-name | PASS. `src/lamp💡.py` body `E = 1` | hold |
| s8-unicode-dir | PASS. `src/café/note.py` body `D = 1` | hold |
| bx1-mode-set-x | PASS. Commit mode `100755`. Review prompt had no `100755` | `29da017` |
| bx1-mode-clear-x | PASS. Agent chmod `0755` (prompt saw `100755`), gate cleared the bit, commit mode `100644` | `29da017` |
| bx1-mode-0600 | PASS. Commit mode `100644`. Git does not store `0600` | hold |
| bx1-gate-deletes | FAIL `tests-flaky`, no commit. The second gate import dies after unlink | hold |
| bx1-gate-extra-file | PASS. `src/extra.py` is absent from the commit | hold |
| bx2-hardlink-in-scope | First run INCONCLUSIVE (real bwrap, `os.link` EXDEV). Rerun with fake bwrap: PASS, committed `PFY_HARDLINK_SENTINEL_42`, leaked into `attempt-1/patch.diff` and the review post | `915edf0` |
| bx2-hardlink-out-of-scope | Same rerun: PASS-REJECTED `review-rejected`, no commit, sentinel still in `attempt-1/patch.diff` | `915edf0` |
| bx2-symlink-dir-in-scope | PASS-REJECTED, symlink created, no leak | hold |
| bx2-symlink-dir-out-of-scope | PASS-REJECTED, no leak | hold |
| bx2-symlink-relative-escape | PASS-REJECTED, no leak | hold |
| bx2-replace-src-with-dir-symlink | PASS-REJECTED, no leak | hold |
| m10-error-object-beside-accept | PASS-REJECTED `review-rejected`, no commit | hold (base `1c74003`) |
| m10-empty-choices-with-error | PASS-REJECTED `review-rejected`, no commit | hold (base `1c74003`) |
| m17-no-review-retries-5 | FAIL `tests-failed`, 1 attempt, `review.retries` 0 | hold (base `1c74003`) |
| m18-empty-diff | Mutant not re-applied. Tip test `test_reviewer_prompt_contains_the_changed_line` is on the base and is green in the 38-test run | hold (base `1c74003`) |

## How each change fails and recovers

### Executable bit (`29da017`)

Fails when the gate flips the executable bit on a reviewed file after the digest was taken. The run exits 1 with reason `gate-modified-reviewed-file`, writes no commit and no branch, and leaves origin clean. There is no retry.

Recovers on the next run. A mode the agent set before review still commits (`test_agent_executable_bit_is_what_gets_committed` expects `100755`). A chmod the git tree will still store as `100644` (probe and test: `0600`) still commits. When `core.filemode` is false the digest token stays `100644`, so that host does not false-fail.

### Hardlink (`915edf0`)

Fails when a changed regular file has `st_nlink` higher than the number of names for that inode inside the worktree. The run exits 1 with reason `hardlink-outside`, writes no commit and no branch, and leaves origin clean. There is no retry. `_collect_diff` drops the real hunk and appends the marker line `hardlink-outside`, so the receipt does not keep the host bytes.

Recovers when both names live in the worktree and the allow list includes them (`test_hardlink_inside_the_worktree_is_committed`): both blobs match, and the review prompt contains the text. A working bwrap returns EXDEV for a link that crosses the worktree bind, so that sandboxed attempt never creates the link. The new check is the unsandboxed path (missing bwrap, or `--unsafe-no-sandbox`).

## Skips

- Pregate not run. The lane drop-in says do not run `scripts/pregate.sh`.
- `s7-rename-low-similarity` and `s8-nfc-and-nfd-both` are holds (decisions 6 and 7), not product fixes.
- M18 was not re-applied as a source patch. The existing behavior test is the kill, and a mutated tree must not be committed.
- No further item. After these two findings the named probes have no remaining wrong pass. This lane did not pick up unrelated TODO or catalog work.

## Test evidence

- Scratch CLI at `d2521b5`: `tmp/probe/results.jsonl` (gitignored).
- This session, before `915edf0`: `nice -n 19 python3 -m unittest` on the three hardlink tests, the in-scope symlink test, and `test_gate_executable_bit_does_not_commit`. 5 tests OK in 4.904s.
- This session, before `915edf0`: `nice -n 19 python3 -m unittest tests.test_pfy_build_local_review`. 38 tests OK in 84.393s. `BrokenPipeError` during `test_kill_during_review` is pre-existing; the module still returned OK.

## Cross-lane requests

None.

## Gate

Tester plus Reviewer for the runtime changes in `scripts/pfy_build_local.py`. The handoff commit is docs only. Pregate was not run.

## Next step

Tester re-runs `bx1-mode-set-x`, `bx1-mode-clear-x`, `bx2-hardlink-in-scope`, and `bx2-hardlink-out-of-scope` on `915edf0`. The hardlink cases need the sandbox off (fake or missing bwrap plus `--unsafe-no-sandbox`), because a working bwrap already blocks the cross-bind link. Reviewer reads `bot/mvp-probe-fix2-1031`. Do not merge from this lane.
