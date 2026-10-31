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

state: DONE | tests: none (docs only) | files: 2 | err: none

### merge-tip

`git merge --no-edit origin/bot/mvp3-review-retry` brought `d624535` (one-line handoff fix). Merge commit `fbb2835`. No rebase. Pushed.

state: DONE | tests: none (merge) | files: 1 | err: none

### confirm-base

Host at 2026-10-31T20:50Z: MemAvailable about 61 GiB, load 3.60, nproc 32. Under the pressure line. Wall cap still 2026-11-01T04:42:04Z.

Checked on `fbb2835` before the product edit:

- A review HTTP error is written as `{"error": ...}` and parsed as `review-unparseable`, then retried as `PASS-REJECTED`. A review-call timeout is status `TIMEOUT` / reason `timeout` (exit 3), the same bucket as an agent timeout.
- No test feeds an HTTP error or a hung review call.
- The retry prompt puts the previous diff after the reasons. Existing tests assert strings that also appear in the reasons (`src/notes.py`, module names, `review-unparseable`, `tests-failed`). A prompt that drops the diff still passes. That is M7.
- Scope vs commit is already fail-closed on this base (`scope-commit-mismatch`, gitignored extra file test). Item 4 will be confirmed and skipped if that still holds.
- Help text already says review is the default and the file and line caps. The MVP-3 handoff does not.

state: DONE | tests: read-only | files: 0 | err: none

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
item-5-docs | (sha next) | nice python3 -m unittest tests.test_pfy_build_local_review | Ran 15 tests in 29.461s OK
