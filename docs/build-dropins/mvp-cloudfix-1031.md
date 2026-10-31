# Lane mvp-cloudfix-1031 (extra cloud lane, MVP 2026-10-31)

Branch: `bot/mvp-cloudfix-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-cloudfix-1031`
Base: `origin/bot/mvp-cloud-1031` (lane mvp-cloud-1031 has exited LANE EMPTY; this lane now owns the cloud runner)
Run log: `docs/ops/RUN-LOG-mvp-cloudfix-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-cloudfix-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-cloudfix-1031.md`
Plan and DoD: `git show origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md`.

Needs a local model: no. Cloud Grok only.

## Scope

Harden the daily cloud runner until it meets every line of the Functional MVP DoD and its failure-case table, driven by real evidence.

Inputs, re-read with `git fetch origin` before every item:
- `docs/ops/HANDOFF-mvp-cloud-1031.md` known gaps on your base.
- Findings in `eval/mvp-1031/dogfood/REPORT.md` on `origin/bot/mvp-dogfood-1031`, `eval/mvp-1031/realfail/REPORT.md` on `origin/bot/mvp-realfail-1031`, `eval/mvp-1031/sixtask/REPORT.md` on `origin/bot/mvp-sixtask-1031`, and their handoffs' "Cross-lane requests" (these lanes run in parallel and push often; read with `git show`, do not merge them).
- Round-2 item from the plan: mvp-dedupe-1031 (replace the inline classifier with `classify_cloud_failure` from `pfylib/build_preflight.py` on `origin/bot/mvp-preflight-1031`; you may `git merge origin/bot/mvp-preflight-1031` for that, it owns only that module and its test). This lane replaces the round-2 dedupe lane.
- `docs/ops/HANDOFF-mvp-review-fix-1031.md` on `origin/bot/mvp-review-fix-1031` for local-runner fixes (G4, G5) that the cloud runner should mirror.

Order: real findings with severity high first, then DoD lines not yet covered by a behavior test, then dedupe, then the rest.

## Owned files

`scripts/pfy_build_cloud.py`, `tests/test_pfy_build_cloud.py`, new `tests/test_pfy_build_cloud_*.py` files, the build paragraph and `cmd_build` in `scripts/pfy`, this lane's three `docs/ops/*-mvp-cloudfix-1031.md` files. After merging preflight: `pfylib/build_preflight.py` read only.

Must not touch: `scripts/pfy_build_local.py`, `scripts/pfy_build_p.py`, `eval/**`, `docs/ops/pfy-build-daily.md`, `docs/modules/**`, other lanes' docs.

## Per finding

Write a failing behavior or fail/recover test first (temp git repo, fake grok seam), fix, run `tests.test_pfy_build_cloud*` and `tests.test_pfy_build_p` niced, commit, push. Then, where the finding came from a real run, reproduce it once with real grok on a throwaway clone under `tmp/` and record the before and after receipt paths in the run log. Never point `./pfy build` at Mark's checkout or another worktree.

Integration note for the handoff: `bot/mvp-cloudfix-1031` must be merged after `bot/mvp-cloud-1031` and `bot/mvp-preflight-1031`.

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
