# RUN-LOG mvp-review-fix2-1031

Started: 2026-10-31T20:42:04Z
Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-review-fix2-1031`
Branch: `bot/mvp-review-fix2-1031` (tracks `origin/bot/mvp-review-fix2-1031`)
Base: `origin/bot/mvp-review-fix-1031` (sits on the MVP-3 review loop). First product step is `git fetch origin && git merge --no-edit origin/bot/mvp3-review-retry` for tip d624535. Merge, do not rebase.
Head at start: `e94a7fc` (lane drop-in on top of the review-fix branch)
Needs a local model: no. Stub or fake seams only. Do not start Ollama. Do not re-run the six MVP-3 tasks.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     Reviewer HTTP error and timeout record their own attempt status (REVIEW-ERROR / review-unavailable), are not retried, and are not counted as a reject. The final receipt says so and includes a recovery line. Behavior tests kill mutants M4 and M7. The commit stages only the reviewed path set and fails closed when git diff --cached --name-only differs, including a gitignored extra file. Help text and the MVP-3 handoff or report state that review is on by default with a 3-file / 250-line cap. A missing allow list adds a warnings entry. PFY_STUB_* is not read in production. eval/mvp3/REPORT.md notes same-model reviewer independence. Trial and eval scratch live under this worktree tmp/. Review tests run with bwrap hidden. --unsafe-no-sandbox does not unsandbox the gate when bwrap works; a missing bwrap still blocks unless the flag is set, and the receipt records unsandboxed only in that case. Owned modules pass. No Ollama process started.
1 Goal met:                  unittest of tests.test_pfy_build_local, tests.test_pfy_build_local_review, and any new tests.test_pfy_build_local_* module, plus tests.test_pfy_local_build_eval when item 9 changes it. Evaluator is the test runner, not a model. Mutant probes must fail on the old code and pass after the fix.
2 Turn cap:                  11 listed items plus further fitting local-runner gaps from the parallel plan. Stop when the lane is empty or another exit fires. Each item is one commit and one push.
3 Budget cap:                Cloud Grok only. No local model. No Ollama. No spend beyond this session. No full unittest discover and no pregate unless the end-of-run host check allows pregate once.
4 Wall clock:                8 hours from 2026-10-31T20:42:04Z (stop new items by 2026-11-01T04:22:04Z, hard stop 2026-11-01T04:42:04Z) or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Leave 20 minutes to write the handoff.
5 No-progress:               The same failure twice with no new information, or 3 items in a row skipped. Record and stop.
6 Human interrupt:           User stop. No questions. Irreversible actions (force push, merge to main, PR, tags, main checkout, other worktrees, signaling processes this run did not start) are forbidden by the drop-in.
7 Error threshold:           3 consecutive same failure, or the same assertion twice. Stop and record. Do not weaken tests.
8 External event:            If origin/main or another bot branch already closed an item, skip it and say so here. Do not check out other branches. Integration note only: merge this branch after bot/mvp-review-fix-1031. This run does not merge.
Loop type:                   goal
Human gate:                  Mark merges after Tester plus Reviewer (runtime). This run does not merge, open a PR, or tag.
```

## Drop-in exits (check before every item)

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (PST, 2026-11-02T02:00Z), whichever comes first. Launch 2026-10-31T20:42:04Z, so the 8 hour bound is 2026-11-01T04:42:04Z and it fires first. Stop new items by 2026-11-01T04:22:04Z.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before the change. Record them and skip that area. Do not stop the lane.

Host at start: MemAvailable 65303036 kB (about 62.3 GiB), load 3.87 3.75 3.60, nproc 32. Under the pressure line.

## Plan

Overview: Close the reviewer follow-ups on the MVP-3 local review loop. A reviewer outage is its own terminal status, not a reject and not a retry. Tests must kill the known surviving mutants. The commit path stays fail-closed on extra staged names. Docs, the stub env seam, scratch paths, Ubuntu skip conditions, and the sandbox gate flag are in scope only where the owned files allow. After the eleven items, take the next local-runner gap from the parallel plan that fits these files.

Phases:
- exits | `docs/ops/RUN-LOG-mvp-review-fix2-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-review-fix2-1031.md` | exit card committed before product code | none | lead
- merge-tip | this worktree | `git fetch origin && git merge --no-edit origin/bot/mvp3-review-retry` brings d624535. No rebase, no force push | exits | lead
- confirm-base | read only on owned runner and tests, plus `origin/main` and the plan ref | each listed item is still open, or skipped with a reason | merge-tip | lead
- item-1-outage | `scripts/pfy_build_local.py`, review tests | HTTP error or timeout sets REVIEW-ERROR / review-unavailable, no retry, not a reject, receipt says so with a recovery line | confirm-base | lead
- item-2-m4 | review tests, runner only if the status is not observable | behavior tests for HTTP error and timeout kill mutant M4 | item-1-outage | lead
- item-3-m7 | review tests | previous diff reaches the retry prompt; mutant M7 fails | item-2-m4 | lead
- item-4-scope | runner and review tests | commit only the reviewed path set; cached names must equal it; gitignored extra file fails closed | item-3-m7 | lead
- item-5-docs | local runner help text, MVP-3 handoff or report on this branch | review on by default and the 3-file / 250-line cap are written | item-4-scope | lead
- item-6-allow | runner and tests | missing allow list adds a warnings list entry on the receipt | item-5-docs | lead
- item-7-stub | runner and tests | PFY_STUB_* reads in `_stub_extra_rw` sit behind an explicit test-only flag or seam | item-6-allow | lead
- item-8-report | `eval/mvp3/REPORT.md` only | note that the reviewer is the same model as the agent and what that means for independence | item-7-stub | lead
- item-9-scratch | `scripts/pfy_local_build_eval.py`, `scripts/pfy_build_local.py` if the trial path lives there, `tests/test_pfy_local_build_eval.py` | scratch is under the script repo root `tmp/`, not the main checkout `tmp/pgs`. Behavior test | item-8-report | lead
- item-10-ubuntu | review tests, runner only to remove a bwrap or model skip | review tests run when bwrap is hidden; record run vs skip counts | item-9-scratch | lead
- item-11-sandbox | runner and tests | `--unsafe-no-sandbox` does not unsandbox the gate when bwrap works; missing bwrap still blocks unless the flag is set; receipt records unsandboxed only then. Stub bwrap | item-10-ubuntu | lead
- further-gaps | owned files only | next fitting local-runner row from the parallel plan, or lane-empty | item-11-sandbox | lead
- handoff | `docs/ops/HANDOFF-mvp-review-fix2-1031.md`, this log | handoff committed and pushed. No merge | last, on any exit | lead

Owned files: `scripts/pfy_build_local.py`, `scripts/pfy_local_build_eval.py` (item 9 only), `tests/test_pfy_build_local.py`, `tests/test_pfy_build_local_review.py`, new `tests/test_pfy_build_local_*.py`, `tests/test_pfy_local_build_eval.py` (item 9 only), `eval/mvp3/REPORT.md` (item 8 only), the MVP-3 handoff doc (item 5 only), this lane's three `docs/ops/*-mvp-review-fix2-1031.md` files.

Forbidden: `scripts/pfy_build_cloud.py`, `scripts/pfy`, `scripts/pfy_build_p.py`, `pfylib/build_preflight.py`, `eval/mvp-1031/**`, `docs/ops/pfy-build-daily.md`, `docs/modules/**`.

Risks:
- Treating a reviewer outage as a reject burns a retry or flips the receipt. Mitigation: a distinct status, no retry loop, receipt text plus a recovery line, behavior test with a fake HTTP error and a fake timeout.
- Mutant tests assert the helper name instead of the prompt or the receipt. Mitigation: assert the previous diff text in the retry prompt, and assert status, reason, and that the loop stopped.
- `git add -A -f` still stages a gitignored file. Mitigation: stage only the reviewed set and compare `git diff --cached --name-only`. Mismatch resets and exits 1.
- Hiding `PFY_STUB_*` breaks the stub tests. Mitigation: an explicit test-only flag or seam that production does not set. Tests set it and still fail if the stub files are ignored.
- Scratch path derived from cwd hits the main checkout. Mitigation: derive from the script file's repo root. Test by running the helper from another cwd.
- Review tests skip when bwrap is missing. Mitigation: find the skip, remove it for review tests, simulate ubuntu-parity with bwrap hidden, record counts.
- `--unsafe-no-sandbox` unsandboxes a working bwrap gate. Mitigation: the flag applies only when bwrap is missing. Receipt field only in that case. Stub `bwrap` on PATH and off PATH.

## Phases

### exits

Exit card and phase plan written before the merge and before any product code. Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. The card above plus the drop-in exits stand in for them. Decision logged in `docs/ops/AUTONOMOUS-DECISIONS-mvp-review-fix2-1031.md`.

Parallel sub-agents are not used for the listed items. They share the runner and the review tests. The lead implements them in order on this branch.

prior-state: DONE | tests: none (docs only) | files: 2 | err: none

### merge-tip

`git merge --no-edit origin/bot/mvp3-review-retry` brought `d624535` (one-line handoff fix). Merge commit `fbb2835`. No rebase. Pushed.

prior-state: DONE | tests: none (merge) | files: 1 | err: none

### confirm-base

Host at 2026-10-31T20:50Z: MemAvailable about 61 GiB, load 3.60, nproc 32. Under the pressure line. Wall cap still 2026-11-01T04:42:04Z.

Checked on `fbb2835` before the product edit:

- A review HTTP error is written as `{"error": ...}` and parsed as `review-unparseable`, then retried as `PASS-REJECTED`. A review-call timeout is status `TIMEOUT` / reason `timeout` (exit 3), the same bucket as an agent timeout.
- No test feeds an HTTP error or a hung review call.
- The retry prompt puts the previous diff after the reasons. Existing tests assert strings that also appear in the reasons (`src/notes.py`, module names, `review-unparseable`, `tests-failed`). A prompt that drops the diff still passes. That is M7.
- Scope vs commit is already fail-closed on this base (`scope-commit-mismatch`, gitignored extra file test). Item 4 will be confirmed and skipped if that still holds.
- Help text already says review is the default and the file and line caps. The MVP-3 handoff does not.

prior-state: DONE | tests: read-only | files: 0 | err: none

### item-1-outage

Reviewer HTTP error and reviewer-call timeout set attempt and final status `REVIEW-ERROR`, reason `review-unavailable`, exit 1. They are not retried and not `PASS-REJECTED` or `TIMEOUT`. The receipt `recovery` line says this is not a reject, was not retried, and names the recovery (run again, or `--no-review`).

How it fails: the review service returns HTTP 500, or the review call exceeds the attempt timeout. There is no verdict.

How we recover: no branch, origin unchanged. The receipt tells the operator to run again when the reviewer answers, or to pass `--no-review`.

item | commit | tests | result
item-1-outage | e685f70 | nice python3 -m unittest tests.test_pfy_build_local tests.test_pfy_build_local_review | Ran 74 tests in 109.054s OK

### item-2-m4

M4 is one return in `_run_model_review`: the outage returns `"reject"` with reason `review-unparseable` instead of `"unavailable"`. That is the pre-fix classification. The caller then retries it as a normal reject.

RED: M4 -> `test_reviewer_http_error_is_not_a_reject_and_is_not_retried`, `test_reviewer_timeout_is_not_a_reject_and_is_not_retried`. Both failed: `PASS-REJECTED != REVIEW-ERROR`. Ran 2 tests in 39.471s, FAILED (failures=2). The runner was restored before this commit. `git diff scripts/pfy_build_local.py` was empty.

item | commit | tests | result
item-2-m4 | d5f4812 | mutant run above, then the two tests on the restored runner (item 1, 14.063s OK) | M4 fails, restored tree passes

### item-3-m7

M7 is `_agent_prompt` setting `shown = ""` so the retry prompt keeps the reasons and drops the previous diff. Existing tests still pass under that mutant because they assert strings that also appear in the reasons.

RED: M7 -> `test_previous_diff_reaches_the_retry_prompt`. Failed: `return a + b + 1` was not in the retry prompt. The prompt still contained `Reasons:\ntoo broad` and an empty `Previous diff:` section. Ran 1 test in 1.495s, FAILED. The runner was restored before this commit.

On the restored runner the same test passed in 1.512s. The removed line is absent from the first prompt and sits after `Previous diff:` on the retry.

item | commit | tests | result
item-3-m7 | 5079532 | nice python3 -m unittest tests.test_pfy_build_local_review | Ran 14 tests in 29.210s OK

### item-4-scope

Already done on this branch. `7bdede7` (`fix: stage only reviewed paths on local build`) is an ancestor. `_stage_reviewed` stages only the reviewed names and requires `git diff --cached --name-only` to match. A mismatch resets the index, sets `scope-commit-mismatch`, exits 1, and creates no branch. `test_gitignored_extra_file_is_absent_from_the_commit` uses a gitignored extra file. `origin/main` has no `scope-commit-mismatch`. Skipped. No second copy.

item | commit | tests | result
item-4-scope | skipped | already on base 7bdede7 | no code change

### item-5-docs

`./pfy build --local --help` states that review is on by default and that a green patch is rejected above 3 changed files or 250 added plus removed lines. The same sentence is in `docs/ops/HANDOFF-mvp3-review-retry.md` under Review defaults.

How it fails: an operator reads `--help` or the MVP-3 handoff and does not learn the default or the cap.

How we recover: the help test fails if the sentence is dropped. `--no-review` remains the one-attempt path. `--max-files` and `--max-lines` still override the cap.

item | commit | tests | result
item-5-docs | 34a6eaf | nice python3 -m unittest tests.test_pfy_build_local_review | Ran 15 tests in 29.461s OK

### item-6-allow

A task with no `files:` line and no `--allow-path` adds a `warnings` entry that says `no allow list`. A `files:` line or `--allow-path` leaves that entry out. The run still PASSes. This is a warning, not a reject.

How it fails: scope is skipped, so a wide patch can be accepted and the receipt looks clean.

How we recover: the warning names the gap. The operator adds `files:` or `--allow-path` and runs again. The branch from the warned run is still a normal PASS when the gate is green.

item | commit | tests | result
item-6-allow | cef308c | nice python3 -m unittest tests.test_pfy_build_local tests.test_pfy_build_local_review | Ran 77 tests in 113.162s OK

### item-7-stub

`_stub_extra_rw` returns no paths unless `PFY_LOCAL_BUILD_TEST_SEAM=1`. Production does not read `PFY_STUB_PLAN`, `PFY_STUB_COUNT`, or `PFY_STUB_PROMPTS`. The receipt lists `sandbox_extra_rw`. Review tests set the seam, so prompt and retry checks still see the stub files.

How it fails: a process with those env vars set, and the seam unset, does not bind the stub directory. With the seam on, the directory is bound and the review tests can record prompts.

How we recover: leave the seam unset. The receipt `sandbox_extra_rw` is empty. Set the seam only in the test harness that needs the binds.

item | commit | tests | result
item-7-stub | 8dd5baf | review module Ran 17 in 32.132s OK; local module Ran 61 in 81.253s OK | OK

### item-8-report

`eval/mvp3/REPORT.md` notes that the reviewer is the same model as the agent (`qwen3.6:35b` on the same endpoint). A shared blind spot is not an independent review. The human column is the independent read. Deterministic checks do not call the model. The trial numbers were not re-run.

item | commit | tests | result
item-8-report | db3dfcb | none (docs only) | note added

### item-9-scratch

The eval runner pins `TMPDIR` to `<repo>/tmp` and creates fixture copies there. The default repo is the directory that contains `scripts/pfy_local_build_eval.py`, not the process cwd. `--repo` that resolves into the main checkout (the git common dir parent) outside this worktree is refused before any directory is created, with a recovery line. `eval/mvp3/run_trial.py` already sets scratch from its own file path; a usage run from a hostile cwd and `TMPDIR` still creates `tmp/mvp3-trial-tmp` under this worktree and leaves the foreign directory empty.

`scripts/pregate.sh` still writes `tmp/pgs` via the git common dir so socket paths stay short. That file is not owned. Not edited. Cross-lane request.

How it fails: a shell whose `TMPDIR` or cwd points at the main checkout does not move eval copies or the trial scratch there. A `--repo` of the main checkout exits 2 and writes nothing.

How we recover: run the script from its worktree, or pass `--repo` under that worktree. The refusal names the main checkout and the recovery.

item | commit | tests | result
item-9-scratch | 23ea0cd | nice python3 -m unittest tests.test_pfy_local_build_eval | Ran 19 tests in 47.288s OK

### item-10-ubuntu

Skip conditions that explain a larger ubuntu-24.04 count live outside the review module. `tests/test_pfy_build_local.py` skips five confinement tests when `bwrap_works()` is false, plus `grok-missing` and `opencode-missing`. Harness2 sandbox tests and several x-intake smokes skip when bwrap is missing or a tool is absent. The G0 job `.github/workflows/eval-structural.yml` (`structural-github`, ubuntu-24.04) runs `python3 -m unittest discover -s tests -t .` and does not install bwrap. nimo's 16 skips are the host set that remains when bwrap works.

`tests/test_pfy_build_local_review.py` has no `skipTest`, `skipUnless`, or `skipIf`. It uses the stub opencode and the stub HTTP reviewer (`fixture:small`). It does not call a model.

Simulation: `tests/test_pfy_build_local_review_ci.py` builds a PATH with every executable except `bwrap` (pregate `ubuntu-parity` / `nobwrap_env` style) and runs the review module. Result file `tmp/review-ci-parity/result.txt`: `ran=17 skipped=0`. The parity test itself: Ran 1 test in 31.601s OK.

How it fails: a review test that starts skipping when bwrap is hidden fails the parity test. A review test that needs a real model fails it too, because the hidden PATH run does not start one.

How we recover: keep the review tests on the stub HTTP reviewer and the stub opencode. Confinement tests in other modules stay skipped when bwrap is absent, so they do not pretend the sandbox was shown.

item | commit | tests | result
item-10-ubuntu | 187efde | nice python3 -m unittest tests.test_pfy_build_local_review_ci | Ran 1 test in 31.601s OK; inner review module ran=17 skipped=0

### item-11-sandbox

`--unsafe-no-sandbox` does not unsandbox the test gate when bwrap works. `prepare_sandbox` returns `unsafe-no-sandbox` only when `bwrap_works()` is false. The receipt field `gate_unsandboxed` is true only after a gate run took that path. A missing bwrap without the flag is still `BLOCKED` `no-sandbox` and `gate_unsandboxed` is false. Help text says a working bwrap still sandboxes the agent and the gate.

The proof uses a stub `bwrap` that logs its argv and execs the command after `--`. With the flag set, the receipt stays `gate_unsandboxed` false, `sandbox` starts with `bwrap`, and a log line contains both `--unshare-net` and `unittest`. The failing stub (exit 1) still blocks unless the flag is set, and then `gate_unsandboxed` is true.

How it fails: a flag that unsandboxes a working bwrap makes the stub log miss the wrapped unittest line, or sets `gate_unsandboxed` true. A missing bwrap without the flag still blocks. Recovery: install bwrap, or pass the flag and accept `gate_unsandboxed` true plus the stderr WARN. Re-run the build. The blocked receipt did not claim the gate ran unsandboxed.

item | commit | tests | result
item-11-sandbox | b483166 | nice python3 -m unittest tests.test_pfy_build_local tests.test_pfy_build_local_review | Ran 79 tests in 115.311s OK

## Finish

Checked 2026-10-31T21:26:33Z. MemAvailable about 59 GiB. Load about 3.84 on 32 cores. Wall cap 2026-11-01T04:22:04Z has not fired. `pgrep -f 'Runner[.]Worker'` found pid 2242260. The heavy lock was held by two `unittest discover` runs (pids 2291979 and 2294586). pregate not run: host busy.

No further row in `docs/plans/MVP-PARALLEL-1031.md` fits these owned files. G1 through G3 and G6 through G9 are other lanes. G4 and G5 are already on the base. G10 is excluded. Round 2 `mvp-local-t5-1031` needs a local model and `eval/mvp-1031/`, which this lane must not touch. Lane empty.

prior-state: DONE | exit: lane empty | product: b483166 | pregate not run: host busy

## Wave 4 (Tester S-items)

The earlier `prior-state: DONE` is superseded. Wave 4 start: 2026-10-31T22:39:04Z. Head at reopen: `620941c`. Base to merge: `origin/bot/mvp3-review-retry` at `582414b` (B1 staged paths, fail-closed review, M08/M14/M17). Merge, do not rebase. Resolve staging and fail-closed conflicts in favor of `582414b`. Then S1 through S5.

Host at wave 4 start: MemAvailable about 55.3 GiB, load 3.41 3.21 3.35, nproc 32. Under the pressure line. `Runner.Worker` pid 3199955 is live, so pregate stays deferred.

### LOOP EXIT CARD (wave 4)

```text
LOOP EXIT CARD
Goal (success criteria):     Merge 582414b. S1: an unreachable reviewer (HTTP error or review-call timeout) sets receipt status reviewer-unavailable, exits nonzero, retries nothing, and commits nothing. S2: a wall-clock cap covers the whole build plus review loop and the receipt reason names it when hit. S3: a nonzero agent exit with no diff is crash, and an exit 0 with no diff stays no-change. S4: the receipt status and the stdout summary use one label table and the same token. S5: a leftover tmp/local-build-* worktree is removed or the run stops with stale-worktree, and it is never the tree the new attempt edits. Owned modules pass. No Ollama process started.
1 Goal met:                  unittest of tests.test_pfy_build_local and tests.test_pfy_build_local_review (and a new tests.test_pfy_build_local_* module if one is added). Evaluator is the test runner. Each S item's test fails if the old behavior is still present.
2 Turn cap:                  5 S items plus the merge and the handoff. Stop when those are done or another exit fires. Each item is one commit and one push.
3 Budget cap:                Cloud Grok only. No local model. No Ollama. No spend beyond this session. No full unittest discover and no pregate unless the end-of-run host check allows pregate once.
4 Wall clock:                Original launch cap still applies. Stop new items by 2026-11-01T04:22:04Z. Hard stop 2026-11-01T04:42:04Z, which is before Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z). Leave 20 minutes to write the handoff.
5 No-progress:               The same failure twice with no new information, or 3 items in a row skipped. Record and stop.
6 Human interrupt:           User stop. No questions. No force push, no merge to main, no PR, no tags, no edits outside this worktree.
7 Error threshold:           3 consecutive same failure, or the same assertion twice. Stop and record. Do not weaken tests.
8 External event:            If origin already has an S item, skip it and say so. This run does not merge to main. Integration remains: merge this branch after bot/mvp-review-fix-1031.
Loop type:                   goal
Human gate:                  Mark merges after Tester plus Reviewer. This run does not merge, open a PR, or tag.
```

### Plan (wave 4)

Overview: Pick up the re-pinned MVP-3 tip, keep its staging and fail-closed review, then give the Tester S-items their own receipt behavior. Outage, overall timeout, crash versus no-change, one label source, and stale worktrees. The lead edits the shared runner in order in this worktree.

Phases:
- wave4-exits | this run log and the decisions file | card committed before the merge | none | lead
- wave4-merge | this worktree | `git merge --no-edit origin/bot/mvp3-review-retry` brings 582414b. Staging and fail-closed hunks follow that tip. No rebase | wave4-exits | lead
- S1-outage | `scripts/pfy_build_local.py`, review tests | receipt status reviewer-unavailable, nothing committed, not retried | wave4-merge | lead
- S2-overall | runner and tests | wall-clock cap over build plus review. Receipt reason overall-timeout when hit. Nothing committed | S1-outage | lead
- S3-crash | runner and tests | nonzero agent exit and no diff records crash. Exit 0 and no diff stays no-change | S2-overall | lead
- S4-labels | runner and tests | receipt status and stdout summary are the same token from one label table. The module docstring lists that table | S3-crash | lead
- S5-stale | runner and tests | leftover tmp/local-build-* is cleaned and named, or the run stops with stale-worktree. The new attempt does not edit that tree | S4-labels | lead
- handoff | `docs/ops/HANDOFF-mvp-review-fix2-1031.md`, this log | handoff committed and pushed. No merge | last, on any exit | lead

Risks:
- The merge drops this lane's REVIEW-ERROR path or 582414b's empty-diff stop. Mitigation: keep 582414b fail-closed (no commit on http error, review timeout, empty diff). S1 then renames the unreachable case to reviewer-unavailable without opening a commit.
- An overall cap smaller than the suite's stub runs fails healthy tests. Mitigation: default cap is 7200 seconds. The behavior test passes a tiny --overall-timeout.
- A clean noop becomes crash. Mitigation: only a nonzero agent exit with an empty diff is crash. The existing noop test must stay no-change.
- Label constants imported by the test hide a drift. Mitigation: the test hardcodes the operator words and compares the receipt to the stdout line.
- Cleaning a live worktree. Mitigation: only paths under this repo's tmp/ named local-build-*, after the lock is held, and a path that remains on disk aborts the run.

prior-state: IN PROGRESS | tests: none yet | files: 0 | err: none

### wave4-merge

`git merge --no-edit origin/bot/mvp3-review-retry` conflicted in `scripts/pfy_build_local.py` and `tests/test_pfy_build_local_review.py`. Staging stays `_stage_reviewed`. Fail-closed matches 582414b: HTTP error is `FAIL` / `review-http-error`, a review-call timeout is `TIMEOUT` / `timeout` (exit 3), an empty diff is `review-empty-diff`, and none of those commit. The no-change gate still goes through `_watch_gate` so `gate_unsandboxed` is recorded. Both previous-diff tests stay. S1 will replace the generic outage statuses.

item | commit | tests | result
wave4-merge | this commit | nice python3 -m unittest tests.test_pfy_build_local_review tests.test_pfy_build_local | Ran 85 tests in 148.861s OK
