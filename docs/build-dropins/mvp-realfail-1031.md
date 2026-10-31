# Lane mvp-realfail-1031 (extra cloud lane, MVP 2026-10-31)

Branch: `bot/mvp-realfail-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-realfail-1031`
Base: `origin/bot/mvp-cloud-1031` (the daily cloud runner `scripts/pfy_build_cloud.py`, still being built by lane mvp-cloud-1031)
Run log: `docs/ops/RUN-LOG-mvp-realfail-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-realfail-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-realfail-1031.md`
Plan: `docs/plans/MVP-PARALLEL-1031.md` on `origin/bot/mvp-plan-1031` (read it with `git show origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`). The Functional MVP Definition of Done and its failure-case table there are the spec.

Needs a local model: no. Never pass `--local`. Cloud Grok only. This lane is meant to exercise the REAL cloud runner with REAL grok calls, so spending Grok Build usage here is expected and fine.

Before each item: `git fetch origin && git merge --no-edit origin/bot/mvp-cloud-1031` so you test the newest runner. Never edit `scripts/pfy_build_cloud.py`, `scripts/pfy`, `tests/test_pfy_build_cloud.py` or any other lane's owned files. A runner bug you find is a FINDING: write it in your report with the exact command, exit code, receipt excerpt and a suggested fix (a patch file under your eval dir is fine), and add it to the handoff "Cross-lane requests" for lane mvp-cloud-1031.

All demo target repos are throwaway clones or fixture repos under this worktree's `tmp/` (for example `git clone --no-hardlinks ~/DEVELOP/pfy-mentat/tmp/mvp-realfail-1031 tmp/target-N` then `git -C tmp/target-N checkout -b demo-base`, or the fixture from `eval/mvp-1031/` on `origin/bot/mvp-eval-1031`). Never point `./pfy build` at Mark's main checkout or any other worktree. Use `--repo` (or whatever the runner's real flag is; read its `--help`). Nothing is pushed from target repos.

Redact receipts before committing: no token, bearer, key or auth values. Check with grep before every commit.

## Lane DoD

Exercise every row of the DoD "Failure cases" table against the REAL runner with REAL grok where the case can be produced for real, and with the runner's documented fake-grok seam only where a real case cannot be produced safely (say which). Each case gets a recorded receipt under `eval/mvp-1031/realfail/<case>/` and a verdict: matches DoD (exit code, status, reason, recovery text, no branch, caller unchanged) or FINDING.

Cases, in order:

1. Interrupted run: start a real `./pfy build` on a throwaway clone, send SIGINT to the runner after the first grok call starts, then separately SIGTERM. Expect exit 1, `reason` `interrupted`, no branch, no orphan grok process (check with `pgrep` that only processes you started are gone; never signal anything you did not start).
2. SIGKILL then `./pfy build --reap`: expect `ABORTED`, `no-receipt`, no stray processes, and reap does not touch `tmp/local-build.pids.json` entries (plant a fake local entry pointing at a sleep process YOU start, and assert it survives).
3. Timeout: real run with a very short `--timeout`. Expect exit 3, `TIMEOUT`.
4. Dirty caller: target clone with an uncommitted file and a staged file. Expect both still dirty after, not in the commit.
5. Gate red with real grok: a task whose requested change cannot pass a planted failing test (state it), retries spent, exit 1, no branch, attempts length 3, gate tail in later prompts.
6. Review reject: use a real task with a deliberately unsafe instruction the reviewer should reject (for example "also delete the tests directory"). Record the verdict.
7. Auth failure: run with `HOME` pointed at an empty dir under `tmp/` so grok is not logged in. Expect exit 1, `unauthenticated`, recovery text, and no read of `auth.json` by the runner. Do not copy or read `~/.grok/auth.json`.
8. Rate limit: do not try to trigger a real rate limit. Use the fake-grok seam and record that it is simulated.
9. Gitignored extra file and scope mismatch: a task that also creates a gitignored file. Expect it absent from the commit.
10. Redaction: a task whose output prints a fake token-like string you plant (for example `xai-FAKE0000`). Expect the receipt redacted.

`eval/mvp-1031/realfail/REPORT.md`: one row per case, real or simulated, expected vs observed, verdict, and finding details with suggested fixes.

## Owned files

`eval/mvp-1031/realfail/**`, `tests/test_mvp_1031_realfail_receipts.py`, this lane's three `docs/ops/*-mvp-realfail-1031.md` files.

## Acceptance tests

`tests/test_mvp_1031_realfail_receipts.py`: loads every committed receipt, asserts its status and reason match the REPORT row, and asserts no secret-like strings. One fail case with a planted bad receipt in a temp dir.

After the table is done, repeat any FINDING case after each new `origin/bot/mvp-cloud-1031` commit and record whether it is fixed.

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
