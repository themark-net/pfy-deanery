# Lane mvp-review-fix-1031

Branch: `bot/mvp-review-fix-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-review-fix-1031`
Base: `origin/bot/mvp3-review-retry`
Run log: `docs/ops/RUN-LOG-mvp-review-fix-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-review-fix-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-review-fix-1031.md`

Needs a local model: no. Do not re-run the six MVP-3 tasks. Do not start Ollama.

This lane closes two measured holes in the local review loop. It does not make `./pfy build --local` the default. It does not turn review off. It does not change exit codes.

## Definition of Done

On `./pfy build --local`, with the stub agent the existing tests already use:

1. A gitignored file that `git add -A -f` would have staged is not in the commit. The reviewed name set and the staged name set match. On mismatch the index is reset, the run exits 1, `reason` is `scope-commit-mismatch`, and no branch is created.
2. A no-change attempt runs the gate once, records `reason` `no-change`, and puts the gate tail in the retry feedback. The review model is not called when there is no diff. A green gate plus an empty diff is still `no-change`, not PASS. Spent retries exit 1 with no branch.
3. Existing local PASS, review reject, and `--no-review` behavior still pass their tests. `--retries` default stays 2. Review stays on unless `--no-review` is passed.
4. `tests.test_pfy_build_local` and `tests.test_pfy_build_local_review` pass. No Ollama process was started.

The historical report `eval/mvp3/REPORT.md` stays as written. Do not edit it.

## Owned files

- `scripts/pfy_build_local.py`
- `tests/test_pfy_build_local.py`
- `tests/test_pfy_build_local_review.py`
- `tests/test_pfy_local_build_eval.py` only if a review-fix change forces a line there. Prefer not to edit it.
- `docs/ops/HANDOFF-mvp-review-fix-1031.md`
- `docs/ops/RUN-LOG-mvp-review-fix-1031.md`
- `docs/ops/AUTONOMOUS-DECISIONS-mvp-review-fix-1031.md`

## Forbidden files

`scripts/pfy`, `scripts/pfy_build_p.py`, `scripts/pfy_build_cloud.py`, `scripts/pfy_local_build_eval.py`, `pfylib/`, `eval/mvp-1031/`, `eval/mvp3/REPORT.md`, `eval/mvp3/run_trial.py`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `docs/modules/`, `.gitignore`, catalog files (`data/tools.json`, `TOOLS.md`, `sources/`).

## Ordered work

1. Write the loop exits into the run log before any code.
2. On the base, confirm the holes are still there: `files_changed` uses `git status` without ignored files, the commit path uses `git add -A -f`, and an empty change list continues before `run_tests`. If a hole is already closed, skip that item and say so in the run log.
3. Stage only the reviewed paths (keep the existing excludes for `tmp`, bytecode, and pytest cache). After `git add`, compare `git diff --cached --name-only` to the reviewed set. Mismatch: reset, fail `scope-commit-mismatch`, no branch. Add a behavior test: a gitignored extra file is absent from `git show` of the commit, or the run fails closed with no branch. Commit and push.
4. On no-change, run the gate, record `no-change`, and include a distinctive line from the gate tail in the next prompt. Do not call the review model. Add a behavior test with the stub agent. Commit and push.
5. Re-run `tests.test_pfy_build_local` and `tests.test_pfy_build_local_review`. Commit the handoff on exit.

## Acceptance tests

Behavior tests, stub agent, temp git repo, no model:

1. Agent writes an allowed file and a gitignored file. The commit blob does not contain the gitignored path. HEAD of the base branch is unchanged when the run fails closed instead.
2. Agent writes nothing. The gate command runs and its stdout contains a marker the test planted. The second attempt's prompt contains that marker. When retries are 0, exit is 1, reason `no-change`, and no `local/` branch exists.
3. A previously green review-accept test still commits only the reviewed file and exits 0.

## Hard rules (pre-authorized, no questions)

- Follow the orchestrator skill (`~/.grok/skills/orchestrator/SKILL.md`) and the repo skills `prefer-behavior-and-fail-recover-tests`, `repo-handoff-doc-required` and `write-loop-exits-first`. Do not ask questions. Decide conservatively, log each decision as one line in this run's decisions file, and keep going.
- Work only in this worktree. Never touch Mark's main checkout `~/DEVELOP/pfy-mentat`, any other worktree under `tmp/`, or Mark's processes. Never stop or signal a process you did not start.
- Other lanes run in parallel on this host. Stay inside your owned files. If you must change a file another lane owns, do not; record it as a cross-lane request in your handoff.
- No sudo and no system changes. Do not use `/tmp`: scratch goes under this worktree's `tmp/` (gitignored), with `TMPDIR` pointed there.
- Never print, log or commit secret values. Do not read `~/.grok/auth.json`.
- Push only this run's own `bot/` branch, as new commits. No force push, no PR, no merge to main, no tags.
- No em dashes or en dashes in anything you write.
- Every item gets a behavior or fail/recover test when code changes (no tautological unit tests), a commit, and a push. Push after every item.
- Do not end your turn while any process you started is still running. Run long commands in the foreground with bounded waits, or detached with a pid file and a foreground poll loop.

## Shared host: heavy jobs and local models

- Cloud Grok is the default. Never call a local model unless this lane's drop-in explicitly says it needs one.
- Any local-model job (`ollama run`, requests to `127.0.0.1:11434`, `pfy build --local`, local evals) must run under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` and only one local-model job may run on the host at a time. Unload the model when done.
- Targeted tests are fine any time: `nice -n 19 python3 -m unittest tests.test_x`.
- Full `unittest discover`, `make eval-*`, docker builds: run with `nice -n 19` under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`.
- Pregate: at most once, at the end, only if the GitHub runner is idle (`pgrep -f 'Runner[.]Worker'` is empty), under the same flock. Otherwise record "pregate not run: host busy" in the handoff.

## Loop and exits (write these into the run log before any work)

This is a long orchestrator loop, not a single slice. After the listed items, keep taking the next MVP gap that fits this lane until an exit fires.

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (PST, 2026-11-02T02:00Z), whichever comes first. Check before every item. Leave 20 minutes to write the handoff.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before your change. Record them and skip that area, but do not stop.

Skip items that need special hardware, a human decision (an open OQ), a secret, or Mark's hands. Log each skip with a reason. Do not invent architecture: if an item needs an ADR, write it up as an OQ draft in the handoff and skip it.

## Per item

1. Read the item and its linked docs. Check it is not already done on the base or on `origin/main`.
2. Make the smallest change that closes it, plus behavior or fail/recover tests where code changes.
3. Run the affected test modules (targeted, niced).
4. Commit with a clear message naming the item. Push. Append one line to the run log: `item | commit | tests | result`.

## Finish (on any exit)

Write or update this run's handoff in `docs/ops/`: items done with SHAs, items skipped and why, test evidence, how each change fails and recovers, cross-lane requests, the gate needed (Tester plus Reviewer for runtime changes; pregate plus Reviewer for docs, eval or test-only changes), and the next step. Finish the run log with a final `state:` line. Commit and push. Do not merge.

## After the DoD

After this lane's DoD is met, keep picking further MVP gaps from `docs/plans/MVP-PARALLEL-1031.md` that fit this lane's owned files, until an exit fires.

`docs/plans/MVP-PARALLEL-1031.md` lives on `origin/bot/mvp-plan-1031`. Read it with `git show origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`. Do not check out that branch. This drop-in is committed on this lane's branch.
