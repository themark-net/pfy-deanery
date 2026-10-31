# Lane mvp-intfix-1031 (MVP 2026-10-31, wave 3)

Branch: `bot/mvp-intfix-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-intfix-1031`
Base: `origin/bot/mvp-integrate-1031`
Run log: `docs/ops/RUN-LOG-mvp-intfix-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-intfix-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-intfix-1031.md`
Plan and DoD: `git show origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`. Integration state: `docs/ops/HANDOFF-mvp-integrate-1031.md` on `origin/bot/mvp-integrate-1031`.

Needs a local model: no. Cloud Grok only. Never pass `--local` to a real run.

## Scope: the two suite failures on the integration branch (do this fast; it unblocks integration pass 2)

1. `tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same` fails because bare `./pfy build --help` is now the cloud card (plan decision D1). Change the test so it expects the dogfood flags on `./pfy build -p --help` and the cloud card on bare `./pfy build --help`. Keep it a behavior test (run the real `scripts/pfy`). Edit only that test class in that file; lane mvp-review-fix2-1031 owns the rest of `tests/test_pfy_build_local.py`.
2. `tests/test_local_bench.py`: `log_path_for_receipt` returns a relative path when the log is inside the repo, and with `TMPDIR` under the worktree the temp dir is inside the repo. Decide the correct contract (read the receipt consumers), then fix the test or the helper so the suite passes with `TMPDIR` inside the repo AND outside it. Add a fail/recover test for both placements.
3. Run the full suite once under the lock with `TMPDIR=$PWD/tmp` and record counts. Any other failure: record it, fix only if it is in these files.

## Owned files

The `CloudBuildUnchangedTests` class in `tests/test_pfy_build_local.py`, `tests/test_local_bench.py`, the `log_path_for_receipt` helper and its module (find it; do not touch the cloud or local runners otherwise), this lane's docs/ops files.

Integration note for the handoff: merge after `bot/mvp-review-fix2-1031`. Push as soon as each fix is green. After that, take other suite failures on the integration branch that fit these files, then stop with LANE EMPTY.

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
