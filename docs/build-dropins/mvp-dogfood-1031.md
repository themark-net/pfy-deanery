# Lane mvp-dogfood-1031 (extra cloud lane, MVP 2026-10-31)

Branch: `bot/mvp-dogfood-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-dogfood-1031`
Base: `origin/bot/mvp-cloud-1031` (the daily cloud runner `scripts/pfy_build_cloud.py`, still being built by lane mvp-cloud-1031)
Run log: `docs/ops/RUN-LOG-mvp-dogfood-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-dogfood-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-dogfood-1031.md`
Plan: `docs/plans/MVP-PARALLEL-1031.md` on `origin/bot/mvp-plan-1031` (read it with `git show origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`). The Functional MVP Definition of Done and its failure-case table there are the spec.

Needs a local model: no. Never pass `--local`. Cloud Grok only. This lane is meant to exercise the REAL cloud runner with REAL grok calls, so spending Grok Build usage here is expected and fine.

Before each item: `git fetch origin && git merge --no-edit origin/bot/mvp-cloud-1031` so you test the newest runner. Never edit `scripts/pfy_build_cloud.py`, `scripts/pfy`, `tests/test_pfy_build_cloud.py` or any other lane's owned files. A runner bug you find is a FINDING: write it in your report with the exact command, exit code, receipt excerpt and a suggested fix (a patch file under your eval dir is fine), and add it to the handoff "Cross-lane requests" for lane mvp-cloud-1031.

All demo target repos are throwaway clones or fixture repos under this worktree's `tmp/` (for example `git clone --no-hardlinks ~/DEVELOP/pfy-mentat/tmp/mvp-dogfood-1031 tmp/target-N` then `git -C tmp/target-N checkout -b demo-base`, or the fixture from `eval/mvp-1031/` on `origin/bot/mvp-eval-1031`). Never point `./pfy build` at Mark's main checkout or any other worktree. Use `--repo` (or whatever the runner's real flag is; read its `--help`). Nothing is pushed from target repos.

Redact receipts before committing: no token, bearer, key or auth values. Check with grep before every commit.

## Lane DoD

1. At least 5 real small tasks run through the real cloud `./pfy build "<task>"` end to end, each on its own fresh throwaway clone of this repo. Pick real, small, verifiable tasks from `docs/TODO.md`, recent `docs/ops/HANDOFF-*.md` "Known gaps" and "Next step" sections (code or test work, not catalog), for example a missing behavior test, a small error-text fix, a doc link fix plus a link-check test. Record why each task was picked.
2. For each run: the command, wall time, exit code, receipt (committed under `eval/mvp-1031/dogfood/<n>-<slug>/receipt.json`), the resulting `cloud/` branch diff (saved as `diff.patch`), gate result, review verdict, and your own human-style verdict (would Mark accept this commit: yes or no and why).
3. `eval/mvp-1031/dogfood/REPORT.md`: table of all runs, pass rate (gate, review accept, human accept), median wall time, and every finding against the DoD with severity.
4. If a run hits rate limit or auth failure, commit that receipt, record it honestly, and continue with the next task later. Never fabricate a PASS.
5. After the first 5, keep running more real tasks (aim for 10 or more) until an exit fires, rotating task types (code fix, new test, docs plus test, refactor under 50 lines).

## Owned files

`eval/mvp-1031/dogfood/**`, this lane's three `docs/ops/*-mvp-dogfood-1031.md` files.

## Acceptance tests

`eval/mvp-1031/dogfood/check_reports.py` plus `tests/test_mvp_1031_dogfood_reports.py`: every run dir has a receipt whose status and exit code match the REPORT row, and no receipt contains secret-like strings. Include one fail case (a planted mismatched fixture under the test's temp dir must make the checker exit 1).

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
