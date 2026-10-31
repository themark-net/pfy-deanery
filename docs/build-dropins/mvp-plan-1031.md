# MVP parallel plan 2026-10-31: plan only, short session

Branch `bot/mvp-plan-1031`, worktree `~/DEVELOP/pfy-mentat/tmp/mvp-plan-1031`, cut from `origin/main` 85c53dc. This is a PLANNING session. Target: finish, commit and push in under 45 minutes. Do not implement product code.

## Goal of the day

Owner goal: by tonight, a FUNCTIONAL pfy-mentat MVP. pfy-mentat becomes Mark's primary LLM dev environment and replaces Grok Build for build-only runs via `./pfy build`. Default is cloud (Grok) `./pfy build`. The MVP-3 review-and-retry loop is available. Local model (`--local`) is an opt-in fallback only, used when Build rate limits bite. The MVP must be usable daily, end to end: Mark runs `./pfy build` on a real small task and gets a gated, reviewed commit on a branch, with a receipt.

Several cloud Grok Build sessions will run IN PARALLEL on this host right after you commit, one per lane. Your plan decides those lanes.

## Inputs to read (read, do not change)

- `origin/main` (85c53dc): `pfy`, `scripts/pfy_build_local.py` and related, `docs/`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `docs/ops/HANDOFF-pfy-local-build-mvp.md`, `docs/ops/HANDOFF-mvp2-trial.md`, `eval/mvp2/REPORT.md`, any RELEASE or DoD files (`git ls-files | grep -iE 'release|dod'`).
- MVP-3: `git diff origin/main origin/bot/mvp3-review-retry` and `git show origin/bot/mvp3-review-retry:eval/mvp3/REPORT.md` plus its handoff under `docs/ops/`. Tip 4428aa3. Result: local 5/6 gate, 5/6 loop accept, 4/6 human accept, 3860s; local stays NO-GO as default.
- Finished overnight branches: `origin/bot/pfy-followups-1030` (654efa7; exited code 3 "no progress"; read `docs/ops/HANDOFF-pfy-followups-1030.md` and its run log for unfinished items) and `origin/bot/backlog-catalog-1030` (e04e926; read its handoff in `docs/ops/`).
- `gh` may not be available. Use `git log`, docs and handoffs for open issues.
- Use `git show origin/<branch>:<path>` to read other branches. Do not check them out and do not touch their worktrees.

## Deliverables (commit and push all on this branch)

1. `docs/plans/MVP-PARALLEL-1031.md` containing:
   - **Functional MVP Definition of Done**: concrete, testable, end to end. Each DoD line names the command Mark runs and the observable result (exit code, receipt file and fields, branch/commit created, gate result, review verdict). Include failure cases that must be handled (cloud rate limit or auth failure, gate red, review reject then retry, dirty tree, interrupted run) and how each recovers.
   - **Gap list**: each gap between (main + MVP-3 + the two overnight branches, assuming they land) and that DoD, with file paths and evidence.
   - **Lanes**: split the gaps into 4 to 6 independent lanes with minimal file overlap. For each lane: name `mvp-<short>-1031` (worktree name, used as the drop-in file name), branch `bot/mvp-<short>-1031`, base (`origin/main` or `origin/bot/mvp3-review-retry` if it builds on the review loop), owned files (and files it must not touch), scope, acceptance tests (behavior/E2E and fail-and-recover, no tautological unit tests), handoff doc path, and whether it needs a local model (avoid; at most one lane, and it must serialize on the lock below).
   - A file-ownership matrix showing no two lanes edit the same file, or naming the single owner and the merge order where overlap is unavoidable.
   - **Integration lane** `mvp-integrate-1031` (branch `bot/mvp-integrate-1031`): merges the lane branches (plus the MVP-3 branch and the two overnight branches) in a stated order, resolves conflicts, runs the full suite under the lock, then runs a real end-to-end cloud `./pfy build` demo on a real small task and records a receipt under `eval/mvp-1031/`.
   - **Round 2**: a list of 3 to 6 MVP-hardening lanes to launch if round 1 finishes early.
2. `docs/plans/MVP-PARALLEL-1031-lanes.tsv`: machine-readable, tab separated, header `name	branch	base	needs_local	dropin`, one row per round-1 lane (NOT the integration lane, NOT round 2). `name` must equal the drop-in file basename. The operator script launches one Build per row from this file.
3. One drop-in per lane, including integration and round 2: `docs/build-dropins/<name>.md`. Each is self-contained (the lane session sees only its drop-in and the repo) and includes:
   - Header: branch, worktree `~/DEVELOP/pfy-mentat/tmp/<name>`, base, run log `docs/ops/RUN-LOG-<name>.md`, decisions file `docs/ops/AUTONOMOUS-DECISIONS-<name>.md`, handoff `docs/ops/HANDOFF-<name>.md`.
   - The lane's DoD, owned files, forbidden files, ordered work items, acceptance tests.
   - The common rules section below, copied verbatim.
   - A tail instruction: after the lane DoD is met, keep picking further MVP gaps from `docs/plans/MVP-PARALLEL-1031.md` that fit the lane's owned files, until an exit fires.
   - Note that `docs/plans/MVP-PARALLEL-1031.md` lives on `origin/bot/mvp-plan-1031` (read it with `git show`) and the drop-in is committed on the lane branch.

## Rules for THIS planning session

- Plan only. No product code changes. Run no test suites, no pregate, no builds, no local models. Light commands only (`git`, `grep`, reading files, `python3 -c` for quick checks).
- Work only in this worktree. Never touch Mark's main checkout `~/DEVELOP/pfy-mentat` working tree, other worktrees, or Mark's processes.
- Scratch under this worktree's `tmp/` (gitignored) with `TMPDIR` there. Never `/tmp`.
- Never print, log or commit secret values. Do not read `~/.grok/auth.json`.
- Push only `bot/mvp-plan-1031`, new commits, no force push, no PR, no merge, no tags.
- No em dashes or en dashes anywhere.
- Do not ask questions. Decide conservatively and record decisions at the bottom of the plan.
- Commit and push as soon as the plan and the tsv exist (even before all drop-ins are done), then commit and push the drop-ins. Finish with one final commit and push, then end your turn. Do not start any lane yourself.

## Common rules (copy verbatim into every lane drop-in)

```
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
```
