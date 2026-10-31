# RUN-LOG mvp-mutate-cloud2-1031

Started: 2026-10-31T23:39:33Z
Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-mutate-cloud2-1031`
Branch: `bot/mvp-mutate-cloud2-1031` (tracks `origin/bot/mvp-mutate-cloud2-1031`)
Base: `origin/bot/mvp-cloudfix-1031`
Head at start: `d49b65f303f78dbd9c018219779fe5d5151f1367`
Needs a local model: no. Cloud Grok only. Never pass `--local`. Do not run `scripts/pregate.sh` during the loop. Pregate at most once at the end, and only if the GitHub runner is idle.

Required merges, never rebase: `origin/bot/mvp-integrate-1031`, then `origin/bot/mvp-dogfood-fix-1031`.
Reuse harness: `eval/mutation-1031/cloud/run_mutants.py` from `origin/bot/mvp-mutate-cloud-1031` (16 killed, 0 survived on the old runner). Do not merge that branch wholesale.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     At least 20 new meaningful mutants of the current scripts/pfy_build_cloud.py, aimed at --writable-test, literal pathspec staging, archive recheck, protected paths, redaction, recovery lines, base-missing, and timeouts. The reused harness applies one mutant at a time to a COPY inside a throwaway clone under this worktree tmp/. It never edits the worktree runner. Each survivor is killed by a behavior or fail/recover test, or recorded as equivalent. A mutant that reveals a real runner bug is written up for mvp-cloudfix-1031. Runner behavior is unchanged. eval/mutation-1031/cloud/REPORT.md lists kills before and after.
1 Goal met:                  The report lists every new mutant as killed, survived, equivalent, or not-applied. A fresh run of the new tests/test_mut_cloud2_*.py modules is green. Evaluator is the test runner. A survivor test must fail when its mutant is applied to a copy and pass on the unmutated runner.
2 Turn cap:                  Listed phases below, then further cloud-mutation gaps that fit this lane. Stop when the lane is empty or another exit fires. Each item is one commit and one push. Survivor tests are one commit per survivor or one commit per tightly related survivor group.
3 Budget cap:                Cloud Grok only. No local model. No Ollama. No spend beyond this session. No full unittest discover. No pregate unless the end-of-run host check allows it once. Mutation runs are targeted modules only, nice -n 19, one mutant at a time, bounded timeout.
4 Wall clock:                8 hours from 2026-10-31T23:39:33Z (stop new items by 2026-11-01T07:19:33Z, hard stop 2026-11-01T07:39:33Z) or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Leave 20 minutes to write the handoff. The 8 hour bound fires first.
5 No-progress:               The same failure twice with no new information, or 3 items in a row skipped. Record and stop.
6 Human interrupt:           User stop. No questions. Irreversible actions (force push, merge to main, PR, tags, main checkout, other worktrees, signaling processes this run did not start, editing scripts/pfy_build_cloud.py or tests/test_pfy_build_cloud*.py) are forbidden by the drop-in.
7 Error threshold:           3 consecutive same failure, or the same assertion twice. Stop and record. Do not weaken tests.
8 External event:            If origin/main or another bot branch already closed an item, skip it and say so here. Re-check origin/bot/mvp-integrate-1031 and origin/bot/mvp-dogfood-fix-1031 before the catalog run. This run does not merge to main.
Loop type:                   goal
Human gate:                  Mark merges after pregate plus Reviewer for this eval and test-only lane. Tester plus Reviewer if a later item changes runtime. This run does not change runner behavior, merge, open a PR, or tag.
```

## Drop-in exits (check before every item)

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (PST, 2026-11-02T02:00Z), whichever comes first. Launch 2026-10-31T23:39:33Z, so the 8 hour bound is 2026-11-01T07:39:33Z and it fires first. Stop new items by 2026-11-01T07:19:33Z.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before the change. Record them and skip that area. Do not stop the lane.

Host at start: MemAvailable 41051004 kB (about 39.1 GiB), load 6.58 6.74 5.80, nproc 32. Under the pressure line.

## Plan

Overview: Mutation-test the cloud runner as it stands after the integrate and dogfood-fix merges. Reuse the wave-3 harness. Add at least 20 meaningful mutants on the code that landed after the first cloud mutation pass. Survivors get a behavior test in this lane, or an equivalent-mutant note. The runner file and its existing tests stay untouched. A real bug becomes a findings file for mvp-cloudfix-1031, not a silent fix.

Phases:
- exits | `docs/ops/RUN-LOG-mvp-mutate-cloud2-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-mutate-cloud2-1031.md` | exit card committed and pushed before product code | none | lead
- fetch-merge | this worktree | `git fetch origin` then merge `origin/bot/mvp-integrate-1031` and `origin/bot/mvp-dogfood-fix-1031`, never rebase | exits | lead
- reuse-harness | `eval/mutation-1031/cloud/run_mutants.py` copied from `origin/bot/mvp-mutate-cloud-1031`, plus a behavior test that the harness refuses to edit the worktree runner | file present and the old catalog is intact | fetch-merge | lead
- confirm-anchors | read only | anchors for writable-test, literal pathspec staging, archive recheck, protected paths, redaction, recovery lines, base-missing, timeouts still exist; origin/main has no second copy of this wave's mutants | reuse-harness | lead
- catalog | harness catalog, at least 20 new mutants | each mutant changes observable behavior (not a comment or whitespace); ids continue the existing series | confirm-anchors | lead
- first-run | `eval/mutation-1031/cloud/REPORT.md` | one bounded run; table of killed / survived / equivalent / not-applied | catalog | lead
- survivor-tests | `tests/test_mut_cloud2_*.py` | each survivor fails on a copy with that mutant and passes on the real runner, or is recorded equivalent. No runner edit | first-run | lead
- rerun | REPORT.md, run log | re-run after the new tests; record kills before and after | survivor-tests | lead
- further-gaps | owned files only | next cloud-mutation gap that fits, or lane-empty | rerun | lead
- handoff | `docs/ops/HANDOFF-mvp-mutate-cloud2-1031.md`, this log | handoff committed and pushed. No merge | last, on any exit | lead

Owned files: `eval/mutation-1031/cloud/**` (extend, do not wipe the wave-3 table), `tests/test_mut_cloud2_*.py`, this lane's `docs/ops/*-mvp-mutate-cloud2-1031.md` files, and a findings note if a mutant exposes a real bug.

Forbidden: `scripts/pfy_build_cloud.py`, `tests/test_pfy_build_cloud*.py`, the wave-3 files `tests/test_mut_cloud_*.py` (leave them as reused, do not rewrite), other lanes' files, Mark's main checkout, other worktrees, `/tmp`.

Risks:
- A mutant edit lands in this worktree's runner. Mitigation: the harness clones under `tmp/` and a harness test asserts the worktree file hash is unchanged. The lead never opens that file for write.
- Reusing the harness by merging the whole mutate-cloud branch drags that lane's handoff into this branch. Mitigation: copy the harness file only. Decision logged.
- A full cloud suite per mutant blows the wall clock. Mitigation: one mutant at a time, nice -n 19, a per-mutant timeout, stop new items 20 minutes before the cap. Record a partial table if the clock fires.
- An anchor misses after an integrate edit and is reported as a false kill. Mitigation: a miss is `not-applied`, not killed and not survived.
- A survivor test only checks that a string was replaced. Mitigation: the test runs the mutant copy and asserts an observable outcome (exit code, receipt field, staged path set, redacted text, recovery line, timeout result).
- A real bug is "fixed" inside this lane. Mitigation: write a findings file and leave the runner alone.
- Parallel coding sub-agents race on the one harness file. Mitigation: the lead runs the phases in order. Only the project-map subagent runs beside the lead, and it writes `.project-map/` only.

## Phases

### exits

Exit card and phase plan written before the fetch, the merges, and any product code. Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. The card above plus the drop-in exits stand in for them. Decision logged in `docs/ops/AUTONOMOUS-DECISIONS-mvp-mutate-cloud2-1031.md`.

Parallel coding sub-agents are not used. They would share this branch and the harness. The lead implements the phases in order. The project-map subagent may write `.project-map/` only.

state: DONE | tests: none (docs only) | files: 2 | err: none

item | 71b4705 | none (docs only) | pushed

### fetch-merge

Checked host before the merge: MemAvailable about 39 GiB, load about 7 on 32 cores. Under the pressure line. Clock 2026-10-31T23:41:21Z, inside the window.

`git fetch origin`. Then `git merge --no-edit origin/bot/mvp-integrate-1031`. Clean ort merge, no conflicts. Tip `f877c7d` is an ancestor of HEAD. `origin/bot/mvp-dogfood-fix-1031` (`1fa9fd3`) was already inside that integrate tip, so `git merge --no-edit origin/bot/mvp-dogfood-fix-1031` reported already up to date. Both required merges are done. No rebase.

Merge commit: `97632630b888038573f1a58ddde2381177241096`. `scripts/pfy_build_cloud.py` is 1562 lines on this HEAD.

state: DONE | tests: merge only, suite not run yet | files: merge | err: none

item | 9763263 | merge only | integrate f877c7d and dogfood-fix 1fa9fd3 are ancestors

### reuse-harness

Copied `eval/mutation-1031/cloud/run_mutants.py`, `tests/test_mut_cloud_harness.py`, and `tests/test_mut_cloud_survivors.py` from `origin/bot/mvp-mutate-cloud-1031` at `9f707fd`. Did not merge that branch. Did not edit those three files. C1-C16 anchors still match this runner: `tests.test_mut_cloud_harness` and `tests.test_mut_cloud_survivors` passed (6 tests, 3.933s).

state: DONE | tests: nice -n 19 python3 -m unittest tests.test_mut_cloud_harness tests.test_mut_cloud_survivors | files: 3 | err: none

item | pending-sha | 6 tests OK in 3.933s | anchors C1-C16 apply on the merged runner
