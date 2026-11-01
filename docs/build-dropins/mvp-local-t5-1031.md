# Lane mvp-local-t5-1031

Branch: `bot/mvp-local-t5-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-local-t5-1031`
Base: `origin/bot/mvp-integrate-1031`
Run log: `docs/ops/RUN-LOG-mvp-local-t5-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-local-t5-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-local-t5-1031.md`

Needs a local model: yes. This is the only lane that may load one.

Model `qwen3.6:35b` only. Every local-model command runs under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`. Unload the model when done (`ollama stop qwen3.6:35b` or a keep-alive of 0). If another model is already loaded, do not start, record "host busy", and stop. If MemAvailable plus SwapFree is under 32 GiB, do not load, and stop.

Round 2. If `origin/bot/mvp-integrate-1031` does not exist, write the handoff as blocked and stop. Do not branch from main.

This lane reruns MVP-3 t5, and t4 if time remains, on the fixed `./pfy build --local`. It does not change the default to local. It does not edit product code. A product bug is a cross-lane request in the handoff.

## Definition of Done

1. `eval/mvp-1031/rerun_local.py` can run one named MVP-3 task (`t5-receipts-outside-repo`, and `t4-timeout-substep` only if t5 finished) via `./pfy build --local` with review on and `--retries 2`. It refuses to run without the flock (document the wrapper command; do not try to detect the flock from inside if that is racy: the drop-in command is the contract).
2. t5 ran once. Receipt and a short note are under `eval/mvp-1031/local-rerun/`. The note says whether a gitignored file landed in the commit (it must not) and the gate result.
3. t4 ran only if t5 is recorded and the wall cap still has room. If t4 is skipped, the note says why.
4. The model is unloaded at the end. `ollama ps` does not list `qwen3.6:35b` when the handoff is written, unless it was loaded by someone else before this lane started (record that and do not unload a model this lane did not load).
5. No edit under `scripts/` or `pfylib/`.

Wrapper:

```text
flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock \
  nice -n 19 python3 eval/mvp-1031/rerun_local.py t5-receipts-outside-repo
```

## Owned files

- `eval/mvp-1031/rerun_local.py` (new)
- `eval/mvp-1031/local-rerun/` (receipts and NOTE.md)
- `docs/ops/HANDOFF-mvp-local-t5-1031.md`
- `docs/ops/RUN-LOG-mvp-local-t5-1031.md`
- `docs/ops/AUTONOMOUS-DECISIONS-mvp-local-t5-1031.md`

## Forbidden files

`scripts/`, `pfylib/`, `docs/ops/pfy-build-daily.md`, `docs/TODO.md`, `eval/mvp-1031/demo-receipt.json`, `eval/mvp-1031/REPORT.md`, `eval/mvp-1031/fixture/`, `eval/mvp-1031/check_receipt.py`, `eval/mvp3/`, catalog files.

## Ordered work

1. Write the loop exits into the run log. Stop if the base branch is missing.
2. Confirm the review-fix commits are in this base (`scope-commit-mismatch` or an equivalent staged-set check exists in `scripts/pfy_build_local.py`). If they are not, record a cross-lane request and stop. Do not patch the runner yourself.
3. Add `rerun_local.py` so it shells the local runner and copies the receipt. Unit-test the argument parse and the "missing task" exit with no model. Commit and push.
4. Run t5 under the flock. Commit the receipt and the note. Push.
5. Run t4 only if the clock allows. Unload. Handoff.

## Acceptance tests

Without a model: `rerun_local.py` with no task exits 2. With an unknown task name it exits 2 and does not call ollama.

With the model, under the flock: the t5 note in `eval/mvp-1031/local-rerun/NOTE.md` names the receipt path, the exit code, and whether the commit contains a gitignored path. A landed gitignored path is a failed rerun, recorded honestly, not edited away.

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
