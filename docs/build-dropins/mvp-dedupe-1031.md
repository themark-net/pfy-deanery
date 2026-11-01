# Lane mvp-dedupe-1031

Branch: `bot/mvp-dedupe-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-dedupe-1031`
Base: `origin/bot/mvp-integrate-1031`
Run log: `docs/ops/RUN-LOG-mvp-dedupe-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-dedupe-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-dedupe-1031.md`

Needs a local model: no.

Round 2. If `origin/bot/mvp-integrate-1031` does not exist, write the handoff as blocked and stop. Do not branch from main.

This lane removes the inline cloud failure classifier and calls `pfylib.build_preflight.classify_cloud_failure`. Skip if integration already did that and no inline copy remains. Say so in the run log.

## Definition of Done

`scripts/pfy_build_cloud.py` calls `classify_cloud_failure` and does not contain a second copy of the rate-limit and auth regexes. `tests.test_pfy_build_cloud` and `tests.test_build_preflight` pass. Rate-limit still exits 4. Auth failure still exits 1 and still does not open `auth.json`.

## Owned files

- `scripts/pfy_build_cloud.py`
- `tests/test_pfy_build_cloud.py`
- `pfylib/build_preflight.py` (only if the import needs a one-line re-export; prefer not to change behavior)
- `docs/ops/HANDOFF-mvp-dedupe-1031.md`
- `docs/ops/RUN-LOG-mvp-dedupe-1031.md`
- `docs/ops/AUTONOMOUS-DECISIONS-mvp-dedupe-1031.md`

## Forbidden files

`scripts/pfy_build_local.py`, `scripts/pfy_build_p.py`, `scripts/pfy` (unless an import path forces a one-line change, which it should not), `eval/mvp-1031/`, `docs/ops/pfy-build-daily.md`, `docs/TODO.md`, catalog files.

## Ordered work

1. Write the loop exits into the run log. If the integrate branch is missing, hand off and stop.
2. If the inline copy is already gone, record that and stop after the handoff.
3. Switch the call. Keep the public exit codes and receipt reasons. Commit and push.
4. Run the two test modules. Handoff.

## Acceptance tests

The existing cloud tests, not new tautological units:

1. `tests.test_pfy_build_cloud` rate-limit case still exits 4 with `reason` rate-limit and a recovery line that contains `./pfy build --local`.
2. The auth case still exits 1 with `reason` unauthenticated on an empty HOME.
3. `tests.test_build_preflight` still passes.
4. A grep of `scripts/pfy_build_cloud.py` finds `classify_cloud_failure` and does not find a private copy of the phrase list. Put that assertion in the cloud test module if it is not already there, as a fail-closed check: a duplicated phrase list means the dedupe did not finish.

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
