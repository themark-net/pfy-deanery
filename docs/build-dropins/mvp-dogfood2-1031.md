# Lane mvp-dogfood2-1031 (MVP 2026-10-31, wave 3)

Branch: `bot/mvp-dogfood2-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-dogfood2-1031`
Base: `origin/bot/mvp-integrate-1031`
Run log: `docs/ops/RUN-LOG-mvp-dogfood2-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-dogfood2-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-dogfood2-1031.md`
Plan and DoD: `git show origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`. Integration state: `docs/ops/HANDOFF-mvp-integrate-1031.md` on `origin/bot/mvp-integrate-1031`.

Needs a local model: no. Cloud Grok only. Never pass `--local` to a real run.

## Scope: dogfood the daily runner on MEDIUM real pfy-mentat tasks

Lanes mvp-dogfood-1031 and mvp-selfhost-1031 already run small tasks. This lane picks medium ones: 2 to 3 files and 60 to 250 changed lines (the review cap edge), from `docs/TODO.md` open rows and recent `docs/ops/HANDOFF-*.md` Known gaps or Next step. Not catalog, `sources/entries/`, `TOOLS.md`, `data/tools.json`, and not files owned by MVP lanes (`scripts/pfy_build_cloud.py`, `scripts/pfy_build_local.py`, `scripts/pfy`, `pfylib/build_preflight.py`, `eval/mvp-1031/**`). Check `eval/mvp-1031/dogfood/REPORT.md` on `origin/bot/mvp-dogfood-1031` and `eval/selfhost-1031/LOG.md` on `origin/bot/mvp-selfhost-1031` so you do not repeat their tasks.

Per task: fresh throwaway clone of this worktree under `tmp/target-<n>`, run the real `./pfy build "<task>" --repo tmp/target-<n>` from this worktree, record command, wall time, exit, attempts, review verdict, human verdict and why, the receipt (redacted) at `eval/dogfood2-1031/<n>-<slug>/receipt.json` and `diff.patch`. If PASS and human-accept, cherry-pick the `cloud/` commit onto this branch with trailer `Built-by: ./pfy build (cloud) receipt eval/dogfood2-1031/<n>-<slug>/receipt.json`, run the affected tests, push. Never hand-fix produced code. Never point the runner at Mark's checkout or another worktree.

`eval/dogfood2-1031/REPORT.md`: rows, pass rates, median wall, and findings against the DoD (especially the review cap and multi-file scope), each also a cross-lane request for mvp-cloudfix-1031. Aim for 8 or more tasks. Test: `tests/test_dogfood2_1031_report.py` (rows match receipts, trailers match receipts, a planted mismatch fails).

Before each task: `git fetch origin && git merge --no-edit origin/bot/mvp-cloudfix-1031` to use the newest runner (record its SHA per row).

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
