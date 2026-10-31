# Lane mvp-eval-1031

Branch: `bot/mvp-eval-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-eval-1031`
Base: `origin/main`
Run log: `docs/ops/RUN-LOG-mvp-eval-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-eval-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-eval-1031.md`

Needs a local model: no. Do not call grok. Do not implement `scripts/pfy_build_cloud.py`.

This lane builds the fixture and the receipt checker that the integration demo runs. The fixture is a real few-line Python task, red until `add` returns the sum.

## Definition of Done

1. `eval/mvp-1031/fixture/add.py` defines `add(a, b)` and returns the wrong value (not the sum).
2. `eval/mvp-1031/fixture/test_add.py` fails on that file (`add(2, 3)` is not 5) and passes once `add` returns `a + b`.
3. `eval/mvp-1031/init_fixture.sh <dest>` creates `<dest>` as a git repo with one commit of those files, on a branch named `main`. The test is red at that commit. The script refuses to use a dest outside the caller's `tmp/` or the path it was given, and it refuses to delete a dest it did not create in this invocation if the dest already exists and is not empty. Print the dest path on success. Exit 2 on usage.
4. `eval/mvp-1031/check_receipt.py <receipt.json>` exits 0 only for a PASS receipt: schema `pfy-cloud-build/1`, `status` PASS, `reason` ok, `exit_code` 0, `branch` starts with `cloud/`, `commit` matches `[0-9a-f]{40}`, `review.verdict` is `accept`, `attempts` is a non-empty list, `pushed` is false, `gate.cmd` is a non-empty string. Otherwise exit 1 and a one-line reason on stderr.
5. The checker rejects serialized JSON that contains `AKIA`, `BEGIN PRIVATE KEY`, or `sk_` followed by 8 or more characters, even if the other fields look like PASS.
6. `eval/mvp-1031/README.md` tells the integration session the demo command. Use inline paths. Do not markdown-link to `docs/plans/MVP-PARALLEL-1031.md` (that file is not on this branch).
7. `python3 -m unittest tests.test_mvp_1031_receipt` passes. No grok, no model.

Demo command to document (integration runs it, this lane does not):

```text
bash eval/mvp-1031/init_fixture.sh "$PWD/tmp/mvp-fixture-repo"
./pfy build "Make add return the sum of its two arguments so the fixture test passes." \
  --repo "$PWD/tmp/mvp-fixture-repo" \
  --base main \
  --test-cmd "python3 -m unittest test_add" \
  --receipt-dir "$PWD/tmp/mvp-fixture-receipt"
python3 eval/mvp-1031/check_receipt.py "$PWD/tmp/mvp-fixture-receipt/receipt.json"
```

## Owned files

- `eval/mvp-1031/fixture/add.py`
- `eval/mvp-1031/fixture/test_add.py`
- `eval/mvp-1031/init_fixture.sh`
- `eval/mvp-1031/check_receipt.py`
- `eval/mvp-1031/README.md`
- `tests/test_mvp_1031_receipt.py`
- `docs/ops/HANDOFF-mvp-eval-1031.md`
- `docs/ops/RUN-LOG-mvp-eval-1031.md`
- `docs/ops/AUTONOMOUS-DECISIONS-mvp-eval-1031.md`

Do not write `eval/mvp-1031/demo-receipt.json` or `eval/mvp-1031/REPORT.md`. Integration owns those.

## Forbidden files

`scripts/`, `pfylib/`, `docs/modules/`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `eval/mvp2/`, `eval/mvp3/`, `.gitignore`, catalog files.

## Ordered work

1. Write the loop exits into the run log before any code.
2. Add the fixture and prove, in a temp dir, that the test fails before the fix and passes after `return a + b`. Commit and push.
3. Add `init_fixture.sh` and a test that the generated repo's test fails. Commit and push.
4. Add `check_receipt.py` and the reject cases below. Commit and push.
5. README. Handoff on exit.

## Acceptance tests

`tests.test_mvp_1031_receipt`, temp dirs, no network:

1. Fixture test fails on the shipped `add.py` and passes when `add` returns `a + b`.
2. `init_fixture.sh` on a temp dest exits 0, `git -C dest rev-parse --abbrev-ref HEAD` is `main`, and `python3 -m unittest test_add` in that repo exits non-zero.
3. A hand-built PASS receipt exits 0 from the checker.
4. Reject: null commit, branch `local/x`, `review.verdict` reject, `pushed` true, empty `attempts`, wrong schema.
5. Reject: a PASS-shaped receipt whose JSON contains `AKIA` plus 16 letters, or a `BEGIN PRIVATE KEY` line, or `sk_` plus eight characters. Use a fake sample, not a real secret.
6. Calling the checker does not read `~/.grok/auth.json`.

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
