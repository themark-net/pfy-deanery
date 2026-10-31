# Lane mvp-surface-1031

Branch: `bot/mvp-surface-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-surface-1031`
Base: `origin/main`
Run log: `docs/ops/RUN-LOG-mvp-surface-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-surface-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-surface-1031.md`

Needs a local model: no. Docs and one test. No product code.

This lane writes the operator card for the daily command. It does not change `scripts/pfy` (the cloud lane owns that help text). It does not edit `docs/modules/README.md` (the backlog branch edits it; integration adds the row).

## Definition of Done

`docs/ops/pfy-build-daily.md` and `docs/modules/pfy-build.md` exist and agree. A reader can run the daily command and know what a PASS and each failure look like, without opening the runner source.

The card includes:

- Daily command: `./pfy build "<task>"`. Default is cloud Grok. Review is on. Nothing is pushed.
- `./pfy build --local "<task>"` is opt-in, for when a cloud receipt says `rate-limit`. It is not the default. MVP-2 and MVP-3 measured local as NO-GO for the default (cloud 6/6 in 583.6 s; local loop 5/6 gate, 4/6 human accept, 3859.9 s).
- `./pfy build -p "<prompt>"` stays the jev dogfood wrap (`scripts/pfy_build_p.py`, receipt.jsonl under `pipelines/dogfood/build/`).
- Exit codes: 0 PASS, dry-run, or `--reap`; 1 FAIL; 2 usage; 3 TIMEOUT; 4 BLOCKED. `--reap` exits 0 while the receipt `status` is `ABORTED`.
- Receipt: `pipelines/dogfood/build-cloud/<stamp>/receipt.json`, schema `pfy-cloud-build/1`. PASS fields: `status`, `reason` ok, `branch` starting `cloud/`, `commit`, `review.verdict` accept, `attempts`, `gate`, `pushed` false.
- Failure names and the recovery for each: rate-limit, unauthenticated, gate red, review-rejected, no-change, scope-commit-mismatch, dirty caller, interrupted, ABORTED after SIGKILL plus `--reap`.
- The runner does not read `auth.json`. A rate limit does not auto-start `--local`.

Mention `scripts/pfy_build_cloud.py` as inline code, not as a markdown link. That file is not on this branch. Link only files that exist on `origin/main`. `tests.test_pfy_build_docs` passes.

## Owned files

- `docs/modules/pfy-build.md` (new)
- `docs/ops/pfy-build-daily.md` (new)
- `tests/test_pfy_build_docs.py` (new)
- `docs/ops/HANDOFF-mvp-surface-1031.md`
- `docs/ops/RUN-LOG-mvp-surface-1031.md`
- `docs/ops/AUTONOMOUS-DECISIONS-mvp-surface-1031.md`

## Forbidden files

`scripts/`, `pfylib/`, `eval/`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `docs/modules/README.md`, `docs/modules/pfylib.md`, `.gitignore`, catalog files.

## Ordered work

1. Write the loop exits into the run log before any code.
2. Write the two docs from the DoD above. Commit and push.
3. Add `tests/test_pfy_build_docs.py`. Commit and push.
4. Handoff. Gate for this lane is pregate plus Reviewer, and pregate only if the runner is idle. Otherwise record "pregate not run: host busy".

## Acceptance tests

`tests.test_pfy_build_docs` fails when either doc is missing any of:

- the daily command `./pfy build`
- exit codes 0, 1, 2, 3, and 4
- schema `pfy-cloud-build/1`
- the sentence that `--local` is opt-in and not the default
- the sentence that `-p` remains the jev dogfood wrap
- these reason names: `rate-limit`, `unauthenticated`, `review-rejected`, `no-change`, `scope-commit-mismatch`, `interrupted`, `ABORTED`

It also fails when either new doc has a relative markdown link whose target does not exist on this branch. The test reads the files. It does not start a build.

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
