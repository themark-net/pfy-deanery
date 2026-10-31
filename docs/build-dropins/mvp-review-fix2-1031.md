# Lane mvp-review-fix2-1031 (Reviewer follow-ups on the review loop, MVP 2026-10-31)

Branch: `bot/mvp-review-fix2-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-review-fix2-1031`
Base: `origin/bot/mvp-review-fix-1031` (which sits on the MVP-3 review loop). First step: `git fetch origin && git merge --no-edit origin/bot/mvp3-review-retry` to pick up the re-pinned MVP-3 tip d624535 (one-line docs fix). Merge, do not rebase. No force push.
Run log: `docs/ops/RUN-LOG-mvp-review-fix2-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-review-fix2-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-review-fix2-1031.md`
Plan and DoD: `git show origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`. Prior lane handoff: `docs/ops/HANDOFF-mvp-review-fix-1031.md`.

Needs a local model: no. Never load a model. Use the runner's stub or fake seams for all tests.

## Listed items (Reviewer non-blocking follow-ups on the MVP-3 review loop, in order)

1. Reviewer outage (HTTP error or timeout on the review call) gets its own attempt status and reason (for example `REVIEW-ERROR` / `review-unavailable`) that is NOT retried and is NOT counted as a reject. Final receipt says so, with a recovery line.
2. Behavior tests for reviewer HTTP error and reviewer timeout. Mutant M4 currently survives; the new tests must kill it (show the mutant and that it now fails).
3. Test that the previous diff reaches the retry prompt. Mutant M7 currently survives; kill it.
4. The scope check must see every path that `git add -A -f` commits (including gitignored and force-added files). Better: commit only the reviewed path set and assert `git diff --cached --name-only` equals it. Fail closed on mismatch. Test with a gitignored extra file.
5. Document that review is on by default and the 3-file / 250-line cap (help text in the local runner and the MVP-3 handoff or report on this branch).
6. Warn on the receipt (a `warnings` list entry) when there is no allow list.
7. Move the `PFY_STUB_*` env reads in `_stub_extra_rw` behind an explicit test-only flag or seam, so production never reads them. Keep the tests meaningful.
8. Note in `eval/mvp3/REPORT.md` that the reviewer is the same model as the agent, and what that means for independence.
9. Trial scratch files went under the main checkout's `tmp/pgs`. Make the trial and eval runners put scratch under the worktree's own `tmp/` (derive from the script's repo root, not the main checkout). Test it.
10. Ubuntu CI skips 104 tests vs 16 on nimo. Confirm the review tests (`tests/test_pfy_build_local_review.py` and the new ones) actually run on the ubuntu-24.04 CI job: find the skip conditions, and make sure review tests do not depend on bwrap or a model. Simulate with the pregate `ubuntu-parity` style (bwrap hidden) and record run vs skip counts for the review tests.
11. Round-2 item mvp-sandbox-gate-1031 from the plan (this lane replaces it): `--unsafe-no-sandbox` must not leave the test gate unsandboxed when bwrap works; a missing bwrap still blocks unless the flag is set, and the receipt records that the gate was unsandboxed only in that missing-bwrap case. Stub bwrap.

## Owned files

`scripts/pfy_build_local.py`, `scripts/pfy_local_build_eval.py` (item 9 only), `tests/test_pfy_build_local.py`, `tests/test_pfy_build_local_review.py`, new `tests/test_pfy_build_local_*.py`, `tests/test_pfy_local_build_eval.py` (item 9 only), `eval/mvp3/REPORT.md` (item 8 only), the MVP-3 handoff doc (item 5 only), this lane's three `docs/ops/*-mvp-review-fix2-1031.md` files.

Must not touch: `scripts/pfy_build_cloud.py`, `scripts/pfy`, `scripts/pfy_build_p.py`, `pfylib/build_preflight.py`, `eval/mvp-1031/**`, `docs/ops/pfy-build-daily.md`, `docs/modules/**`.

Gate for the handoff: Tester plus Reviewer (runtime change). Integration note: merge `bot/mvp-review-fix2-1031` after `bot/mvp-review-fix-1031`.

After the listed items, pick further local-runner gaps from the plan that fit these owned files.

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

## Wave 4 addendum (2026-10-31 15:40 PT): Tester S-items from mvp3
The earlier `state: DONE` is superseded. Base context: bot/mvp3-review-retry is now at 582414b (B1 staged-paths, fail-closed review, M08/M14/M17 tests). First `git merge origin/bot/mvp3-review-retry` (merge, never rebase) and resolve in favor of 582414b's staging and fail-closed behavior. Then, each with a behavior test:
- S1 outage status: when the reviewer is unreachable, the receipt says a distinct status (reviewer-unavailable), not a generic fail, and nothing commits.
- S2 overall timeout: a wall-clock cap over the whole build plus review loop, with a clear receipt reason when hit.
- S3 crash-as-no-change: an attempt that crashes (nonzero exit, no diff) is recorded as crash, not no-change.
- S4 labels: receipt and log labels match the docs (one source for the label strings).
- S5 stale worktrees: a previous run's leftover worktree under tmp/ is detected and cleaned or reported at start, never reused silently.
New state line when done. Same rules as above.
