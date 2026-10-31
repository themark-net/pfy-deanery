# Handoff: review-loop mutation (mvp-mutate-review-1031)

Branch `bot/mvp-mutate-review-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-mutate-review-1031`. Base `origin/bot/mvp-review-fix2-1031`, merged through `3396ee7` (their `b483166`). No PR. No force push. No merge. Mark gates this branch. This lane is eval and tests only.

`scripts/pfy_build_local.py` was not edited. Its sha256 stayed `15e4f4ae1bafa98c2e109002c1ba72e538c89c1ab665827741abf101d80b110a`. No Ollama process was started. No `--local` run. Tests used stubs.

## Items done

| Item | SHA | Tests |
|------|-----|-------|
| Exit card | `a6fbf18` | docs only |
| Merge eval scratch | `cdcd017` | merge of `23ea0cd` |
| Merge review CI parity | `1ee80a3` | merge of `187efde` |
| Harness | `80b5aec` | `tests.test_mut_review_harness`, 5 tests OK |
| Harness SHA line | `36b152c` | docs |
| Merge sandbox gate | `3396ee7` | merge of `b483166`; harness re-run 5 tests OK |
| First campaign report | `e9e532c` | clone suite, baseline 80 tests in 146.235s OK, exit 0 |
| Campaign SHA line | `2ce5edd` | docs |
| Size-cap survivor tests | `ef554f2` | harness plus size cap, Ran 8 tests in 5.476s OK |
| Size-cap SHA line | `1c332e8` | docs |
| After column | `f62d427` | clone of R7, R8, R9 on `tests.test_mut_review_size_cap` |

## Result

Kills before (suite on `3396ee7`, no `tests.test_mut_review_*`): 11. Survivors before: R7 file cap off by one, R8 line cap off by one, R9 size cap removed.

Kills after: 14. Survivors left: none.

R1 review skipped, R2 verdict inverted, R3 outage as accept, R4 (M4) outage as reject, R5 (M7) missing previous diff, R6 missing gate tail, R10 allow list ignored, R11 `git add -A -f` scope bypass, R12 no-change as PASS, R13 attempts not recorded, and R14 stub env in production were killed by the existing local-runner tests. They were not re-run. `origin/bot/mvp-review-fix2-1031` had not moved after `3396ee7`.

The after run applied R7, R8, and R9 one at a time on a throwaway clone. Module `tests.test_mut_review_size_cap` only. Baseline of that module passed.

| id | result | seconds | first failure |
|----|--------|---------|---------------|
| R7 | killed | 2.669 | `test_four_files_are_rejected_and_three_files_pass` |
| R8 | killed | 2.673 | `test_two_hundred_fifty_one_lines_are_rejected_and_two_hundred_fifty_pass` |
| R9 | killed | 2.296 | `test_four_files_are_rejected_and_three_files_pass` |

No test was excluded. None of the targeted modules call a model. No `expectedFailure`.

## How this fails and how we recover

| Risk | How it fails | Recovery |
|------|--------------|----------|
| Mutant written into this worktree | Harness refuses the protected runner path. The campaign hashes it before and after | Restore from git. The clone file is restored in `finally` |
| Hung suite scored as a kill | A timeout row is `timeout`, not `killed` | The suite process group this run started is stopped. The mutant is re-run or recorded |
| Red baseline scored as a kill | A red module is dropped. An empty usable set skips scoring | Record the red module and skip that area |
| Harness module inside the mutant suite | Anchor checks fail on every mutant, so every mutant looks killed | `survivor_modules` omits `tests.test_mut_review_harness`. `--modules` replaces the long suite instead of appending |
| 4 files or 251 lines are committed | Size-cap test expects `PASS-REJECTED`, no commit, no branch, no reviewer chat | Narrow the same task to 3 files or 250 lines. That half commits and the gate stays green |
| 3 files or 250 lines are rejected | The recovery half expects `PASS` and a commit | The cap is inclusive: 3 files and 250 lines pass |
| Cap case uses new untracked names | The reviewed pathspec does not stage them, so the failure is `scope-commit-mismatch` | Seed those files in the base commit, then modify them |

## Skipped

- Full re-run of R1-R6 and R10-R14. Review-fix2 did not move, and those kills were measured on the runner this branch still has.
- Round 2 (`mvp-dedupe-1031`, `mvp-sandbox-gate-1031`, `mvp-local-t5-1031`, `mvp-daily-card-1031`). Other files. The local trial needs a model. G10 is excluded. No new ADR.
- Official `./scripts/pregate.sh`. pregate not run: host busy (heavy lock held). The script also writes `~/DEVELOP/pfy-mentat/tmp/pg` via the git common dir, which is the main checkout. `Runner.Worker` was idle at 2026-10-31T22:19Z. This lane did not flock-wait and did not create that worktree.

## Cross-lane

None. The size cap already existed. The missing piece was the behavior test, and it kills R7, R8, and R9 without a runner edit.

Integrate can take `eval/mutation-1031/review/` and `tests/test_mut_review_*.py` from this branch. There is no runner diff to merge. If `bot/mvp-review-fix2-1031` changes `_check_size` or the reviewed pathspec before that merge, re-run R7, R8, and R9 on a clone before trusting the after column.

## Gate

Eval and test-only. Needs pregate plus Reviewer at the handoff SHA. Pregate was not run (host busy, and the script writes the main checkout). Owned tests exercised here are green. No Feature GO. No Tester gate for a runtime change: the runner was not edited.

## Next

Reviewer reads `eval/mutation-1031/review/REPORT.md` and `tests/test_mut_review_size_cap.py`. Then integrate merges `bot/mvp-mutate-review-1031`. Survivors left: none. This run stops on lane-empty.
