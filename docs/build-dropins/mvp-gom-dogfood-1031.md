# Lane mvp-gom-dogfood-1031 (MVP 2026-10-31, wave 3)

Branch: `bot/mvp-gom-dogfood-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-gom-dogfood-1031`
Base: `origin/bot/mvp-integrate-1031`
Run log: `docs/ops/RUN-LOG-mvp-gom-dogfood-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-gom-dogfood-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-gom-dogfood-1031.md`
Plan and DoD: `git show origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`. Integration state: `docs/ops/HANDOFF-mvp-integrate-1031.md` on `origin/bot/mvp-integrate-1031`.

Needs a local model: no. Cloud Grok only. Never pass `--local` to a real run.

## Scope: use `./pfy build` on a second real repo, Gom Jobbar (themark-net/gom-jabbar-grok4)

This proves the daily runner works outside pfy-mentat.

Target repo setup (once):
- Mark's checkout `~/DEVELOP/jobbar-master/current` is OFF LIMITS: never edit, checkout, stash, reset or run anything in it, and never touch its `gomjobbar_journal.db` or any real journal.
- Create your own worktree: `git -C ~/DEVELOP/jobbar-master/current fetch origin && git -C ~/DEVELOP/jobbar-master/current worktree add -b bot/gom-dogfood-1031 ~/DEVELOP/jobbar-master/tmp/gom-dogfood-1031 origin/main`. That only adds a worktree; it does not change Mark's tree. All work in the gom repo happens in that worktree. Scratch under `~/DEVELOP/jobbar-master/tmp/gom-dogfood-1031/tmp/` (check it is gitignored, otherwise use `~/DEVELOP/jobbar-master/tmp/gom-dogfood-1031-scratch/`).
- Read its `AGENTS.md`, `docs/DECISIONS.md`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md`. Respect its decisions (for example Decision 0006: no auto-submit, `submitted` stays false). No scrapers, no Playwright, no network job fetches, no real journal.
- Its test command is likely `uv run pytest -q`; confirm, and pass it as the runner's `--test-cmd`. If `uv` needs network to sync and fails, record it and use the existing venv if present; do not install system packages.

Per task (aim for 6 or more, small to medium, from its `docs/TODO.md` and handoffs): run, from THIS pfy-mentat worktree, the real `./pfy build "<task>" --repo <a throwaway clone of the gom worktree under scratch> --test-cmd "<cmd>"`. Record command, wall time, exit, attempts, review verdict, human verdict, redacted receipt and diff under `eval/gom-dogfood-1031/<n>-<slug>/` in THIS pfy-mentat branch. If PASS and human-accept, cherry-pick the commit onto `bot/gom-dogfood-1031` in the gom worktree with a `Built-by: pfy-mentat ./pfy build (cloud)` trailer, run its tests, and push that bot branch to the gom origin. No PR, no merge to its main, no force push.

`eval/gom-dogfood-1031/REPORT.md` with rows, rates, findings (what broke because the repo is not pfy-mentat: test command, venv, paths, review prompt assumptions), each also a cross-lane request for mvp-cloudfix-1031. Also add a dated section to the gom repo's `docs/PENDING-HANDOFF.md` on `bot/gom-dogfood-1031` listing the cherry-picked commits. Test in pfy-mentat: `tests/test_gom_dogfood_1031_report.py` (rows match receipts; a planted mismatch fails).

Owned files: `eval/gom-dogfood-1031/**`, that test, this lane's docs/ops files, and branch `bot/gom-dogfood-1031` in the gom repo.

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

## Exception to the common rules for this lane

You may create and work in the gom worktree `~/DEVELOP/jobbar-master/tmp/gom-dogfood-1031` described above and push its `bot/gom-dogfood-1031` branch. Everything else in the common rules still applies, including never touching `~/DEVELOP/jobbar-master/current`.

## Wave 5 addendum (2026-10-31 16:30 PT)
The earlier goal-met state is superseded. Same worktree and branch rules as above for the gom repo (only `~/DEVELOP/jobbar-master/tmp/gom-dogfood-1031` on bot/gom-dogfood-1031; never Mark's checkout or gomjobbar_journal.db). First merge origin/bot/mvp-integrate-1031 into this pfy branch so you use the latest runner (merge, never rebase). Then do 6 MORE real gom backlog items with real cloud `./pfy build` (different from the six already done), human-review each diff, keep only accepted ones on bot/gom-dogfood-1031, record receipts and a Wave 5 section in the report. Note runner friction as findings for mvp-cloudfix-1031.
