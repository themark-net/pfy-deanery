# Lane mvp-selfhost-1031 (extra cloud lane, MVP 2026-10-31)

Branch: `bot/mvp-selfhost-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-selfhost-1031`
Base: `origin/bot/mvp-cloud-1031`
Run log: `docs/ops/RUN-LOG-mvp-selfhost-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-selfhost-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-selfhost-1031.md`
Plan and DoD: `git show origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`.

Needs a local model: no. Cloud Grok only. Real grok calls are expected; spending Build usage here is fine.

## Scope: use `./pfy build` the way Mark will, to ship real small backlog items

This lane is daily-use proof. YOU do not hand-edit product code. You pick real small items and drive them through the real cloud runner, then keep only the commits that pass gate and review AND that you would accept as a careful human reviewer.

Loop per item:
1. Pick a real small item: `docs/TODO.md` open rows, recent `docs/ops/HANDOFF-*.md` Known gaps and Next step (code, test or docs work; not catalog, not `sources/entries/`, not `TOOLS.md`, not `data/tools.json`). Skip anything touching files another MVP lane owns: `scripts/pfy_build_cloud.py`, `scripts/pfy_build_local.py`, `scripts/pfy_build_p.py`, `scripts/pfy`, `pfylib/build_preflight.py`, `docs/ops/pfy-build-daily.md`, `docs/modules/**`, `eval/mvp-1031/**`, `eval/mvp3/**`. Log why you picked it.
2. Make a throwaway clone of this worktree under `tmp/target-<n>` and run the real `./pfy build "<task>"` from your worktree against it (use the runner's `--repo` flag; read `--help`). Never point it at Mark's checkout or another worktree.
3. Record command, wall time, exit code, receipt path, attempts, review verdict and your human verdict in `eval/selfhost-1031/LOG.md` and copy the redacted receipt to `eval/selfhost-1031/<n>-<slug>/receipt.json`.
4. If PASS and human-accept: `git fetch` the `cloud/` branch from the clone and cherry-pick that commit onto `bot/mvp-selfhost-1031`, keeping the original message plus a trailer `Built-by: ./pfy build (cloud) receipt eval/selfhost-1031/<n>-<slug>/receipt.json`. Run the affected tests niced. Push.
5. If not accepted: record why (that is a finding for the runner) and move on. Never hand-fix the produced code.

Target: as many items as the wall cap allows, at least 8. `eval/selfhost-1031/REPORT.md`: items tried, PASS, human accept, cherry-picked SHAs, median wall time, findings for the runner (add them as cross-lane requests for lane mvp-cloudfix-1031).

## Acceptance tests

`tests/test_selfhost_1031_log.py`: every cherry-picked commit on this branch with a `Built-by` trailer points at an existing receipt whose status is PASS and commit subject matches; one fail case with a planted bad trailer in a temp repo.

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
