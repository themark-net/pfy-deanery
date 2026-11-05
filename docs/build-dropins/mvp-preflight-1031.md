# Lane mvp-preflight-1031

Branch: `bot/mvp-preflight-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-preflight-1031`
Base: `origin/main`
Run log: `docs/ops/RUN-LOG-mvp-preflight-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-preflight-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-preflight-1031.md`

Needs a local model: no.

This lane adds a pure function that classifies a failed cloud grok exit. It does not edit the build runner. The cloud lane inlines the same rules so it can test alone. Integration, or round 2 `mvp-dedupe-1031`, is what connects them.

## Definition of Done

`pfylib/build_preflight.py` exports:

```text
classify_cloud_failure(rc, stdout, stderr) -> "rate-limit" | "unauthenticated" | "other"
```

Rules, in order, over `stdout + "\n" + stderr`, case insensitive, only when `rc` is not 0:

1. `rate-limit` if the text matches `rate limit`, `usage limit`, `quota exceeded`, `too many requests`, or `429`.
2. `unauthenticated` if the text matches `unauthenticated`, `not logged in`, `please log in`, or `auth.json`.
3. Otherwise `other`.

`rc` 0 is always `other`, even when the text contains those phrases. The function takes no path, opens no file, and returns only the enum. It does not echo grok text.

`python3 -m unittest tests.test_build_preflight` passes.

## Owned files

- `pfylib/build_preflight.py` (new)
- `tests/test_build_preflight.py` (new)
- `docs/ops/HANDOFF-mvp-preflight-1031.md`
- `docs/ops/RUN-LOG-mvp-preflight-1031.md`
- `docs/ops/AUTONOMOUS-DECISIONS-mvp-preflight-1031.md`

## Forbidden files

`scripts/`, `eval/`, `docs/modules/`, `docs/ops/pfy-build-daily.md`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `.gitignore`, `pfylib/attach.py`, catalog files.

## Ordered work

1. Write the loop exits into the run log before any code.
2. If `pfylib/build_preflight.py` already exists on the base with this contract, do not rewrite it. Extend tests only where a rule has no test.
3. Add the function and the tests below. Commit and push.
4. Handoff on exit.

## Acceptance tests

In `tests/test_build_preflight.py`:

1. Each rate-limit phrase, with rc 1, returns `rate-limit`. A phrase that also contains "not logged in" still returns `rate-limit` (first rule wins).
2. Each auth phrase, with rc 1 and no rate-limit phrase, returns `unauthenticated`.
3. rc 1 and unrelated text returns `other`.
4. rc 0 and the text "rate limit" returns `other`.
5. A body that contains `BEGIN PRIVATE KEY` or `sk_` plus eight characters returns `other` or `unauthenticated` or `rate-limit`, and the return value does not contain that secret text.
6. The test does not create or read `auth.json`.

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
