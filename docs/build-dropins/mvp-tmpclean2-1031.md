# Lane mvp-tmpclean2-1031 (MVP 2026-10-31, wave 4): Reviewer follow-ups on main

Branch: `bot/mvp-tmpclean2-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-tmpclean2-1031`
Base: `origin/bot/pfy-followups-1030-tmpfix` = main c0d38af plus fb759e9 (the hermetic tmp-cleanup test from mvp-tmpclean-1031 a7ae331). This branch must stay a fast-forward from origin/main. Merge origin/main if main moves (merge, never rebase).
Run log: `docs/ops/RUN-LOG-mvp-tmpclean2-1031.md` (end with `state: <DONE|lane empty|wall cap> | ...`)
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-tmpclean2-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-tmpclean2-1031.md`
Needs a local model: no. Do not run scripts/pregate.sh; the operator runs it.

## Scope
First, Reviewer follow-up 16 (priority): tests/test_pfylib_tmp_cleanup globs a hard-coded /tmp and ignores TMPDIR. Parallel lanes create /tmp/pfy-* and make it fail on nimo. Make it use tempfile.gettempdir() or, better, a private child TMPDIR per test run, so it is immune to other processes. Check whether fb759e9 already does this fully; if yes, add the one missing piece (or a test proving immunity: create a /tmp/pfy-* dir from a separate process mid-test, test still passes). If pfylib code itself ignores TMPDIR, port the needed parts of origin/bot/mvp-tmpclean-1031 0284030 ("honor TMPDIR for host scratch paths").

Then the Reviewer follow-ups at c0d38af (now main). Skip any already done on origin/bot/mvp-followups-fix2-1031 (check its handoff: F1 probe flags, F2 tmpfs-only twin = FU12, P2 failing lint, G1 root-length guard). Each with a behavior test where it is code:
1. Pregate ripgrep check is name-only (`grep -q 'ripgrep' .github/workflows/eval-structural.yml`).
3. version_of() has no coverage without bwrap (its tests are needs_bwrap).
4. test_pregate_lint_calls_helper keys its skip on sys.executable having yaml, but pregate uses PATH python3.
5. test_pregate_lint_calls_helper still runs pregate inside unittest and writes pregate-runs under the repo tmp.
6. T-0124 tests: pre-create the session file in the dead-terminal test, and add tests for reuse prove, no engine, base drift, mode env and opencontext env.
7. data/toolsets.json:89 still says `_apply_opencontext_env in pfy_enterable_162_b`.
8. The image-pin lint could reject duplicate keys.
9. The T-0124 row is marked done but still sits in the active table.
11. The redundant run() re-checks (mount reason, which bwrap) are untested. The dir_usable isdir mutant also survives.
13. test_bwrap_without_proc_mount_fails_closed_with_bwrap_reason checks code and reason only. Also assert the binary was not run (no `checks`, no escape), as the sibling tests do.
14. tests.test_harness2_local_stage dry-run test (test_dry_run_prints_the_pin_steps_and_nothing_upstream) is intermittent on nimo. Capture its stderr on failure, find the cause, fix it.
15. Update the handoff note "Pregate re-runs at the fix pin" to the facts: c0d38af pregate FAILed only on test_pfylib_tmp_cleanup (parallel /tmp/pfy-* dirs); CI run 41242021101 nimo job 124666697088 succeeded on rerun.
Skip 2 (ubuntu rg path) and 10 (MemPalace staging) unless trivial; record why.

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
