# RUN-LOG mvp-crosslane-1031

Started: 2026-10-31T23:25:35Z
Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-crosslane-1031`
Branch: `bot/mvp-crosslane-1031` (tracks `origin/bot/mvp-crosslane-1031`)
Base: `origin/bot/mvp-integrate-1031` (drop-in named `0c3f133`; ref may have moved; merge it, do not rebase)
Head at start: `4ede517` (lane drop-in)
Needs a local model: no. Cloud Grok only. Never pass `--local`. Do not run `scripts/pregate.sh` as a work step. Pregate at most once at the end, and only if the GitHub runner is idle.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     Every open cross-lane request from origin/bot/mvp-*-1031 handoffs is either fixed on this branch with a behavior or fail/recover test, already fixed on origin/bot/mvp-cloudfix-1031 or origin/bot/mvp-integrate-1031, or left with a reason. The handoff table names request, source lane, and status (fixed SHA / already fixed / left, why). Edits to live-owned scripts stay in one function each. No other worktree is touched. No merge, no PR, no tag.
1 Goal met:                  The handoff table covers every collected note. Code changes have a targeted unittest that fails if the bug is present. Evaluator is the test runner, not a model.
2 Turn cap:                  One pass over the collected requests, then the next MVP gap that fits this lane and these files. Stop when the lane is empty or another exit fires. Each item is one commit and one push.
3 Budget cap:                Cloud Grok only. No local model. No Ollama. No spend beyond this session. No full unittest discover and no pregate unless the end-of-run host check allows pregate once.
4 Wall clock:                8 hours from 2026-10-31T23:25:35Z (stop new items by 2026-11-01T07:05:35Z, hard stop 2026-11-01T07:25:35Z) or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Leave 20 minutes to write the handoff.
5 No-progress:               The same failure twice with no new information, or 3 items in a row skipped. Record and stop.
6 Human interrupt:           User stop. No questions. Irreversible actions (force push, merge to main, PR, tags, main checkout, other worktrees, signaling processes this run did not start) are forbidden by the drop-in.
7 Error threshold:           3 consecutive same failure, or the same assertion twice. Stop and record. Do not weaken tests.
8 External event:            If origin/bot/mvp-cloudfix-1031, origin/bot/mvp-integrate-1031, or origin/main already closed an item, skip it and say so here. Do not check out other branches. This run does not merge to main.
Loop type:                   goal
Human gate:                  Mark merges after Tester plus Reviewer for runtime changes, or pregate plus Reviewer for docs, eval, or test-only changes. This run does not merge, open a PR, or tag.
```

## Drop-in exits (check before every item)

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (PST, 2026-11-02T02:00Z), whichever comes first. Launch 2026-10-31T23:25:35Z, so the 8 hour bound is 2026-11-01T07:25:35Z and it fires first. Stop new items by 2026-11-01T07:05:35Z.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before the change. Record them and skip that area. Do not stop the lane.

Host at start: MemAvailable 54454664 kB (about 51.9 GiB), load 4.81 4.33 4.32, nproc 32. Under the pressure line.

## Plan

Overview: Read every `origin/bot/mvp-*-1031` handoff, list each cross-lane request, "for mvp-...", and "not owned here" note, and close the ones that are still open. Known seeds are gom-dogfood's five requests for cloudfix, selfhost's `:target` content-hash review miss, ci-cover's help test that skips when grok is not on PATH, and review-fix2's note that `scripts/pregate.sh` writes `tmp/pgs`. A fix lands here only when cloudfix and the current integrate do not already have it, and only as a small one-function edit plus a behavior test. Anything that needs a file this lane must not touch is left in the handoff table.

Phases:
- exits | `docs/ops/RUN-LOG-mvp-crosslane-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-crosslane-1031.md` | exit card committed before product code | none | lead
- merge-base | this worktree | `git merge --no-edit origin/bot/mvp-integrate-1031` so the base is the current integrate tip. No rebase | exits | lead
- collect | read only, `git show` of remote handoffs | every cross-lane note is listed in this log with source branch and a one-line ask | merge-base | lead
- triage | read only on cloudfix and integrate | each note is already fixed (cite SHA) or still open | collect | lead
- fix-open | `scripts/pfy_build_cloud.py` and `scripts/pfy_build_local.py` review code, one function each, plus the matching existing test module | each still-open note that fits those files has a behavior test and a pushed commit. Notes that need another file are left | triage | lead
- further-gaps | same files only | next fitting MVP gap from the parallel plan, or lane-empty | fix-open | lead
- handoff | `docs/ops/HANDOFF-mvp-crosslane-1031.md`, this log | table of request, source lane, status. Final `state:` line. Pushed. No merge | last, on any exit | lead

Owned for edits: this lane's three `docs/ops/*-mvp-crosslane-1031.md` files. The drop-in also allows a one-function edit in `scripts/pfy_build_cloud.py` (live owner mvp-cloudfix-1031) and in the review code of `scripts/pfy_build_local.py` (live owner mvp3-followups-1031), plus a behavior test in the existing test module for that file. Any other path is a cross-lane request, not an edit.

Forbidden to run: `scripts/pregate.sh` until the end-of-run idle check. Never `--local`. Never a local model.

Risks:
- A live lane commits the same function while this branch edits it. Mitigation: one function, smallest diff, merge integrate first, and do not edit a file once the triage shows the live branch already fixed it.
- A test asserts a helper name instead of observable receipt or process behavior. Mitigation: behavior tests that fail when the bug is present (fake grok on PATH, content-hash miss, fail/recover).
- Re-implementing a fix already on cloudfix or integrate. Mitigation: `git show` / `git grep` that tip before any edit, and record "already fixed" with the SHA.
- `scripts/pregate.sh` path change breaks `sun_path` length. Mitigation: do not edit pregate unless triage shows a one-function fix inside an owned file. Otherwise leave it with the reason.
- Host pressure or a red base. Mitigation: check memory and load before each item. A red test on the base is recorded and that area is skipped.

## Phases

### exits

Exit card and phase plan written before the merge and before any product code. Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. The card above plus the drop-in exits stand in for them. Decision logged in `docs/ops/AUTONOMOUS-DECISIONS-mvp-crosslane-1031.md`.

state: DONE | tests: none (docs only) | files: 2 | err: none

### merge-base

`git merge --no-edit origin/bot/mvp-integrate-1031` at tip `cf5a11c` (pass 3 exit card). Merge commit `34b1de1`. Only integrate docs changed (`mvp-integrate-1031` drop-in, decisions, run log). No rebase.

Host before merge: MemAvailable 43805728 kB (about 41.8 GiB), load 6.65 5.14 4.61. Under the pressure line.

item | 34b1de1 | tests: none (merge) | result: merged cf5a11c, docs only

### later merges

Merged `origin/bot/mvp-cloudfix-1031` at `d78ed00` and then `origin/bot/mvp-integrate-1031` at `b6db528` before the help-test commit. Those merges are in the history under `7d12860`. A later integrate tip `d078de6` was not merged. See decisions 4, 5, and 7.

### fixes

Host stayed above the pressure line (MemAvailable about 35 to 40 GiB, load about 6 to 9, nproc 32).

ci-cover help skip | 7d12860 | tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same, plus five cloud tests in the same run, 2.608s OK | pass
selfhost :target review miss | 10328e3 | CloudBuildRetryTests.test_target_marker_is_rejected_even_when_review_accepts and test_root_delete_is_rejected_even_when_review_accepts, 0.830s OK | pass
recheck TMPDIR | 7667b2e | CloudBuildNoChangeTests.test_recheck_tmpdir_stays_inside_the_extract, plus CloudBuildFailureTests secret-env tests, 0.624s OK | pass
followups item 6 pin | bae035f | LocalBuildTests.test_ignored_helper_is_not_committed, 1.898s OK | pass
followups item 3 inject seam | 351cf1d | ReviewLoopTests inject-off, staged-mismatch, and stub-bind seam, 5.093s OK | pass
followups item 5 empty reviewed set | 0e49e1c | first run failed because the stand-in gate printed no summary (tests-failed). Rerun of test_excluded_only_change_does_not_commit 1.320s OK, then inject-off and staged-mismatch 3.318s OK | pass
followups item 2 scope phrase | f46d726 | ReviewLoopTests.test_missing_allow_list_warns_and_a_named_list_does_not, 3.442s OK | pass
followups item 4 same_model | f93e120 | ReviewLoopTests.test_no_review_is_one_attempt_and_a_green_gate_passes, 1.594s OK | pass
followups item 7 review crash | d6c5390 | test_unparseable_review_is_a_reject_and_the_reason_is_fed_back passed with the runner change. The new test then passed after the fake python path was fixed, 1.396s OK | pass

handoff | 10fd155 | docs only | lane empty, pushed

state: lane empty | tests: targeted unittest modules above, all final runs OK | files: cloud runner, local runner, their test modules, this log, decisions, handoff | err: none | pregate not run: host busy
