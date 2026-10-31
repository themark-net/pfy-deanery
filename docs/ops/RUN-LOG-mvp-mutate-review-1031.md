# RUN-LOG mvp-mutate-review-1031

Started: 2026-10-31T21:16:00Z
Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-mutate-review-1031`
Branch: `bot/mvp-mutate-review-1031` (tracks `origin/bot/mvp-mutate-review-1031`)
Base: `origin/bot/mvp-review-fix2-1031`. Before each round: `git fetch origin && git merge --no-edit origin/bot/mvp-review-fix2-1031`. Merge, do not rebase.
Head at start: `13cc7b4` (lane drop-in). `origin/bot/mvp-review-fix2-1031` was `23ea0cd` at planning time (one commit ahead: eval scratch path). That merge is the next phase, after this card.
Needs a local model: no. Cloud Grok only. Tests use stubs. Do not pass `--local` to a real run. Do not start Ollama.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     eval/mutation-1031/review/run_mutants.py runs one mutant at a time on a copy of scripts/pfy_build_local.py inside a throwaway clone under this worktree tmp/. It runs tests.test_pfy_build_local_review, tests.test_pfy_build_local, and tests.test_pfy_build_local_* there, niced and bounded. This worktree's runner file is never mutated. Mutants R1-R14 cover the drop-in list, including Reviewer M4 (R4) and M7 (R5). A test that would call a model is excluded and recorded. Each survivor has a behavior or fail/recover test in a new tests/test_mut_review_*.py. A kill that needs a runner edit is a cross-lane request to mvp-review-fix2-1031, with the test attached (expectedFailure only with a stated reason). eval/mutation-1031/review/REPORT.md has the table, kills before and after, and survivors left. The suite is re-run after each new review-fix2 commit seen this session.
1 Goal met:                  The harness report lists every R mutant as killed, survived, or not-applied, and a fresh run of the new tests/test_mut_review_*.py modules is green. Evaluator is the test runner, not a model. A survivor test must fail when its mutant is applied to a copy and pass on the unmutated runner.
2 Turn cap:                  4 listed items (harness, mutant catalog and first run, survivor tests, report re-run) plus further fitting review-mutation gaps. Stop when the lane is empty or another exit fires. Each item is one commit and one push. Survivor tests are one commit per survivor.
3 Budget cap:                Cloud Grok only. No local model. No Ollama. No spend beyond this session. No full unittest discover and no pregate unless the end-of-run host check allows pregate once. Mutation runs are targeted modules only, nice -n 19, one mutant at a time.
4 Wall clock:                8 hours from 2026-10-31T21:16:00Z (stop new items by 2026-11-01T04:56:00Z, hard stop 2026-11-01T05:16:00Z) or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Leave 20 minutes to write the handoff. The 8 hour bound fires first.
5 No-progress:               The same failure twice with no new information, or 3 items in a row skipped. Record and stop.
6 Human interrupt:           User stop. No questions. Irreversible actions (force push, merge to main, PR, tags, main checkout, other worktrees, signaling processes this run did not start, editing scripts/pfy_build_local.py or tests/test_pfy_build_local*.py) are forbidden by the drop-in.
7 Error threshold:           3 consecutive same failure, or the same assertion twice. Stop and record. Do not weaken tests.
8 External event:            If origin/main or another bot branch already closed an item, skip it and say so here. Re-run the mutant suite when origin/bot/mvp-review-fix2-1031 moves. This run does not merge to main.
Loop type:                   goal
Human gate:                  Mark merges after pregate plus Reviewer for this eval and test-only lane. Tester plus Reviewer if a later item changes runtime (it should not; runner edits are cross-lane). This run does not merge, open a PR, or tag.
```

## Drop-in exits (check before every item)

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (PST, 2026-11-02T02:00Z), whichever comes first. Launch 2026-10-31T21:16:00Z, so the 8 hour bound is 2026-11-01T05:16:00Z and it fires first. Stop new items by 2026-11-01T04:56:00Z.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before the change. Record them and skip that area. Do not stop the lane.

Host at start: MemAvailable 62512888 kB (about 59.6 GiB), load 4.98 4.24 4.00, nproc 32. Under the pressure line.

## Plan

Overview: Mutation-test the local review-and-retry loop without editing it. A harness applies one source mutant at a time to a copy inside a throwaway clone under tmp/, runs the local-runner test modules with stubs only, and writes which mutants the tests kill. Survivors get a new behavior test in this lane. If the kill needs a runner change, the test is attached as a cross-lane request for mvp-review-fix2-1031. After each new commit on that branch, merge and re-run.

Phases:
- exits | `docs/ops/RUN-LOG-mvp-mutate-review-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-mutate-review-1031.md` | exit card committed before product code | none | lead
- merge-base | this worktree | `git fetch origin && git merge --no-edit origin/bot/mvp-review-fix2-1031` | exits | lead
- confirm-base | read only | each mutant anchor still exists on the merged runner; origin/main has no `eval/mutation-1031/review/`; model-calling tests named | merge-base | lead
- harness | `eval/mutation-1031/review/run_mutants.py`, `tests/test_mut_review_harness.py` | fixture run classifies killed vs survived, refuses to edit the worktree copy, excludes a model-calling test and records it | confirm-base | lead
- catalog-and-first-run | harness catalog R1-R14, `eval/mutation-1031/review/REPORT.md` | one bounded run; table of kill / survive / not-applied | harness | lead
- survivor-tests | `tests/test_mut_review_*.py` (one new file per survivor) | each survivor test fails on a copy with that mutant and passes on the real runner. Runner edits stay a cross-lane request | catalog-and-first-run | lead
- rerun | REPORT.md, run log | if review-fix2 moved, merge and re-run; record kills before and after | survivor-tests | lead
- further-gaps | owned files only | next review-mutation gap that fits, or lane-empty | rerun | lead
- handoff | `docs/ops/HANDOFF-mvp-mutate-review-1031.md`, this log | handoff committed and pushed. No merge | last, on any exit | lead

Owned files: `eval/mutation-1031/review/**`, `tests/test_mut_review_*.py`, this lane's three `docs/ops/*-mvp-mutate-review-1031.md` files.

Forbidden: `scripts/pfy_build_local.py`, `tests/test_pfy_build_local.py`, `tests/test_pfy_build_local_review.py`, any other `tests/test_pfy_build_local*.py`, other lanes' files, Mark's main checkout, other worktrees.

Risks:
- A mutant edit lands in this worktree's runner. Mitigation: the harness clones under `tmp/` and the harness test asserts the worktree file hash is unchanged. The lead never opens that file for write.
- A test starts Ollama or calls a model. Mitigation: exclude by name when the test would call a model, record the exclusion, stubs only.
- The full local suite per mutant blows the wall clock. Mitigation: one mutant at a time, nice -n 19, a per-mutant timeout, stop new items 20 minutes before the cap. Record a partial table if the clock fires.
- An anchor misses after a review-fix2 edit and is reported as a false kill. Mitigation: a miss is `not-applied`, not killed and not survived.
- A survivor test only checks that a string was replaced. Mitigation: the test runs the mutant copy and asserts the observable review outcome (verdict, receipt, prompt text, commit set).
- `expectedFailure` hides a real gap. Mitigation: use it only when the kill needs a runner change the other lane owns, and write the reason on the test and in the handoff.

## Phases

### exits

Exit card and phase plan written before the merge and before any product code. Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. The card above plus the drop-in exits stand in for them. Decision logged in `docs/ops/AUTONOMOUS-DECISIONS-mvp-mutate-review-1031.md`.

Parallel coding sub-agents are not used. They would share this branch. The lead implements the phases in order.

state: DONE | tests: none (docs only) | files: 2 | err: none

### merge-base

`git fetch origin && git merge --no-edit origin/bot/mvp-review-fix2-1031` at planning time brought `23ea0cd` (eval scratch stays in the script repo). Merge commit `cdcd017`. Pushed.

The tip moved during the exit card. A second merge brought `187efde` (review module runs with bwrap hidden). Merge commit `1ee80a3`. Pushed. The runner file did not change. `tests/test_pfy_build_local_review_ci.py` is now in the required glob.

Host still under the pressure line at the harness item (the long suite has not started). Wall cap remains 2026-11-01T05:16:00Z.

state: DONE | tests: none (merge) | files: merge | err: none

### harness

`eval/mutation-1031/review/run_mutants.py` applies one catalog mutant at a time on a clone under this worktree `tmp/`. Default invocation only checks anchors. `--run` clones and executes the suite, niced, with `TMPDIR` under `tmp/`. A missing anchor is `not-applied`. A timeout is not a kill. A red baseline is skipped per module and is not scored as kills. The worktree runner is a protected file.

How it fails: a mutant is written into the worktree runner, a hung suite is called killed, or a red baseline is scored as a kill.

How we recover: the harness refuses a protected path and a clone outside `tmp/`. The campaign restores the clone file in `finally`. A timeout kills only the suite process group this run started. A red baseline records the module and skips scoring.

item | commit | tests | result
harness | 80b5aec | nice python3 -m unittest tests.test_mut_review_harness | Ran 5 tests in 2.414s OK

state: DONE | tests: tests.test_mut_review_harness OK | files: 4 | err: none

### merge-before-campaign

`origin/bot/mvp-review-fix2-1031` moved to `b483166` (gate_unsandboxed only when bwrap is missing) plus its handoff. Merge commit `3396ee7`. Anchors still match. Harness tests re-run: 5 tests OK in 2.439s. Pushed.

Host before the campaign: MemAvailable about 57.6 GiB, load 4.09, nproc 32. Under the pressure line.

state: DONE | tests: tests.test_mut_review_harness OK | files: merge | err: none

### catalog-and-first-run

One clone under `tmp/mutation-1031/review-clone`. Baseline 80 tests in 146.235s OK. No module was red. No test was excluded (none call a model). 14 mutants, about 147s each. Wall about 38 minutes. The worktree runner matched HEAD after the run. The clone file was restored.

Killed: R1, R2, R3, R4 (M4), R5 (M7), R6, R10, R11, R12, R13, R14.
Survived: R7 file cap off by one, R8 line cap off by one, R9 size cap removed.

item | commit | tests | result
catalog-and-first-run | e9e532c | nice python3 eval/mutation-1031/review/run_mutants.py --run --timeout 420 | baseline OK, 11 killed, 3 survived, exit 0

state: DONE | tests: mutation campaign exit 0 | files: 2 | err: none
