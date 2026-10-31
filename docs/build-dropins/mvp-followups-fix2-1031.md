# Lane mvp-followups-fix2-1031 (Tester should-fix items on the followups branch, 2026-10-31)

Branch: `bot/mvp-followups-fix2-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-followups-fix2-1031`
Base: `origin/bot/pfy-followups-1030` at c0d38af (Reviewer B1 bwrap-probe fix and B2 root-length test fix already in).
Run log: `docs/ops/RUN-LOG-mvp-followups-fix2-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-followups-fix2-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-followups-fix2-1031.md`
Context: `docs/ops/HANDOFF-pfy-followups-1030.md` on this base.

Needs a local model: no. Cloud Grok only.

## Listed items (Tester should-fix items 2 to 5, in order)

1. The workflow image-pin lint (`scripts/check_workflow_image_pin.py`) runs in pregate but not in CI. Wire it into the hosted CI job in `.github/workflows/` so a PR that adds `ubuntu-latest` fails CI. Keep the hosted runner pinned to `ubuntu-24.04`. Add a behavior test that the workflow file actually invokes the lint (parse the YAML, do not grep).
2. PyYAML interpreter mismatch: the lint must run with the same interpreter that has PyYAML (pregate and CI may call different `python3`). Make the call sites use one explicit interpreter, and make a missing PyYAML fail closed with a clear message naming the interpreter path. Test both: a PATH with a python3 lacking yaml fails closed with that message.
3. The lint does not check container images or digests. Extend it to `jobs.*.container` (string and `image:` forms) and `services.*.image`: require a pinned tag (no `latest`, no missing tag) and, if the repo already pins digests anywhere, require `@sha256:` digests. Fixture workflows for pass and fail cases, including malformed forms that must fail closed.
4. `pfylib/attach.py` mutants A3, A4, A5, A7, A8 and A10 survive. Find each mutant in the Tester notes or the handoff mutation table (or recreate them from the names: orphan window, lost exit code, no install hint). Write behavior or fail/recover tests that kill each one: (a) orphan window: a spawned process left running if the terminal fails to stay up must be reaped, test that no child outlives the call; (b) lost exit code: the real child exit code must reach the caller and the receipt; (c) no install hint: missing `opencode` must print an install hint and return FAIL without spawning. Fix the code where a test shows a real bug. Re-run the mutants and record kills in the handoff mutation table.

## Owned files

`scripts/check_workflow_image_pin.py`, `tests/test_workflow_image_pin.py`, new fixture dirs under `tests/fixtures/` for workflows, `.github/workflows/*.yml` (lint wiring only), `scripts/pregate.sh` (the lint call only), `pfylib/attach.py`, `tests/test_attach.py`, this lane's three `docs/ops/*-mvp-followups-fix2-1031.md` files.

Must not touch: `scripts/pfy_build_cloud.py`, `scripts/pfy_build_local.py`, `scripts/pfy`, `pfylib/build_preflight.py`, `eval/**`, catalog files.

Gate for the handoff: Tester plus Reviewer (runtime and CI change). Integration note: merge after `bot/pfy-followups-1030`.

After the listed items, take further code or test follow-ups named in `docs/ops/HANDOFF-pfy-followups-1030.md` that fit these owned files.

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

## Round 2 addendum (2026-10-31 14:47 PT): new items from the parent
Continue on this branch with new commits, push after each green item. The earlier `state: DONE` is superseded. Write a new state line when these are done.
- F1: the bwrap probe must also pass `--bind <tmp> <tmp>` and `--die-with-parent`, the same flags the real run uses, so a host where those fail is detected by the probe. Behavior test with a fake bwrap that rejects one of those flags: the probe must report unavailable.
- F2: add a `--tmpfs-only` fake-bwrap twin test, mirroring the existing fake-bwrap test, so the tmpfs-only path is covered.
- P2: test that a failing lint makes scripts/pregate.sh fail (overall FAIL, nonzero exit). Drive it with a fixture repo or an env hook, do not edit real lint rules to fail.
- G1: test the root-length guard (the B2 root-length fix at c0d38af): a root path over the limit is refused with a clear message, and one at the limit works.
Same rules as above. Do not run pregate. Finish by updating docs/ops/HANDOFF-mvp-followups-fix2-1031.md.
