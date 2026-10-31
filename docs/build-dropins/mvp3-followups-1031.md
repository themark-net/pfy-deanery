# Lane mvp3-followups-1031 (MVP 2026-10-31, wave 4): Reviewer follow-ups on mvp3 582414b/6664713

Branch: `bot/mvp3-followups-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp3-followups-1031`
Base: `6664713` (bot/mvp3-review-retry, now pinned for Tester and Reviewer). NEVER push to bot/mvp3-review-retry. Keep this branch a fast-forward of 6664713 and of origin/main: if main moves, merge it (never rebase).
Run log: `docs/ops/RUN-LOG-mvp3-followups-1031.md` (end with `state: <DONE|lane empty|wall cap> | ...`)
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp3-followups-1031.md`
Handoff: `docs/ops/HANDOFF-mvp3-followups-1031.md`
Needs a local model: tests only use stubs. Do NOT run real `--local` trials. Do not run scripts/pregate.sh; the operator runs it.

## Scope: Reviewer follow-ups 1 to 10 (verdict on 582414b)
Each code item gets a behavior test. Docs items need no test.
1. Review is on by default with a 3-file / 250-line cap, which can PASS-REJECT larger legitimate diffs. Document it in the user-facing --local docs.
2. The scope check is skipped when there is no files: line and no --allow-path. Put a visible "scope check skipped: no allow list" on the receipt (and a stderr warning). Test it.
3. `_stub_extra_rw` reads PFY_STUB_* env in production code, and `_stage_reviewed` reads PFY_LOCAL_BUILD_INJECT_EXTRA_STAGE and writes a file. Gate both test hooks behind one explicit test-only switch (one env var, documented, off by default). Test that with the switch off the hooks do nothing.
4. Document that the reviewer is the same local model as the agent (self-review) in the docs and the receipt.
5. Empty-reviewed-set edge (only excluded paths changed) fails closed as commit-failed. Give it a clear reason (for example no-reviewable-change) and a test.
6. test_ignored_helper_is_not_committed asserts either of two reasons. Pin the expected one. Note in the handoff that this existing test was inverted on purpose.
7. A poster crash with no out file (for example python missing in the sandbox) reads as review-unparseable, a reject that is retried. Make it fail closed as a reviewer error (review-http-error or a distinct review-crashed), not retried. Test it.
8. docs/ops/HANDOFF-mvp3-review-retry.md lines 38, 45, 51 still describe the scope and commit mismatch as open ("Next code fix, not done here"). Mark them superseded by mvp3-fix-1031 (582414b).
9. The ubuntu job skips about 104 tests against 16 on nimo. Find which modules skip on ubuntu and why, and whether the review E2E tests run on ubuntu at all. Write the explanation into the handoff; if the review E2E tests do not run on ubuntu, make them run there (fake tools) if feasible.
10. Update the previous TMPDIR-under-main-checkout process note to the current practice (TMPDIR=$PWD/tmp in each worktree).

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
