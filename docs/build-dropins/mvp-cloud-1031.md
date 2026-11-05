# Lane mvp-cloud-1031

Branch: `bot/mvp-cloud-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-cloud-1031`
Base: `origin/main`
Run log: `docs/ops/RUN-LOG-mvp-cloud-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-cloud-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-cloud-1031.md`

Needs a local model: no. Do not start Ollama. Do not call `127.0.0.1:11434`.

This lane adds the daily cloud build. `./pfy build "<task>"` creates a worktree, runs cloud Grok, gates, reviews, and commits on a `cloud/` branch with a receipt. `./pfy build --local` and `./pfy build -p` stay on their current scripts.

## Definition of Done

`./pfy build "<task>"` with a fake grok in tests, and with the flags below:

- Exit 0 on PASS. Stdout summary: `PASS ok branch=cloud/<slug>-<stamp> receipt=<path>`.
- `<path>/receipt.json` schema `pfy-cloud-build/1` with `status` PASS, `reason` ok, `exit_code` 0, `branch` starting `cloud/`, `commit` 40 hex chars, `base`, `review.verdict` accept, `attempts` length at least 1, `gate.cmd`, `gate.before`, `gate.after`, `recovery` empty, `pushed` false, `worktree_removed` true unless `--keep-worktree`.
- `git rev-parse` of that branch equals `commit`. The caller branch and `git status --porcelain` are unchanged. No stash, reset, or commit in the caller checkout. No push and no PR.
- The commit contains only reviewed paths. A gitignored extra file is not in the commit.
- `--dry-run` exits 0, starts no grok, writes no branch, receipt `status` DRY-RUN and `commit` null.
- No task exits 2 and the help names `./pfy build "<task>"`, points at `-p` as the jev dogfood wrap, and points at `--local` as the opt-in fallback.
- `./pfy build -p` still runs `scripts/pfy_build_p.py`. `tests.test_pfy_build_p` stays green.

Flags: `--repo`, `--base` (origin/main if it exists, else HEAD), `--test-cmd` (default `python3 -m unittest discover -s tests -t .`), `--retries` (default 2 extra, 3 total), `--no-review`, `--receipt-dir`, `--dry-run`, `--reap`, `--keep-worktree`, `--timeout`, `--grok-cmd` (or env `PFY_BUILD_GROK`) for tests.

Exit codes: 0 PASS, dry-run, or `--reap`; 1 FAIL (includes review reject, no-change spent, scope mismatch, unauthenticated, interrupted); 2 usage; 3 TIMEOUT; 4 BLOCKED (rate-limit).

Failure receipts:

- Rate limit (non-zero rc and text matching rate limit, usage limit, quota exceeded, too many requests, or 429): exit 4, `reason` rate-limit, no branch. `recovery` is the exact `./pfy build --local "<task>"` line. Do not start that command.
- Auth (grok missing, or text matching unauthenticated, not logged in, please log in, or auth.json): exit 1, `reason` unauthenticated. `recovery` tells Mark to run `grok` once and rerun the same `./pfy build`. Do not open `auth.json`. Do not suggest `--local` for this case.
- Gate red with retries left: no commit yet, attempt `reason` is the gate reason, next prompt includes the gate tail.
- Gate red, retries spent: exit 1, no branch.
- Review reject with retries left: no commit of that attempt, next prompt gets the reasons and the previous diff.
- Review reject, retries spent: exit 1, `reason` review-rejected, no branch.
- No-change: the gate still runs, the attempt reason is `no-change`, the gate tail is in the feedback. A green gate and an empty diff is still not PASS. Spent retries: exit 1, no branch.
- Staged names differ from the reviewed set: `git reset`, exit 1, `reason` scope-commit-mismatch, no branch. Do not use `git add -A -f`.
- Dirty caller checkout: leave those files dirty. They are not in the new commit. If the worktree cannot be created, exit 1, `reason` worktree-failed, caller status unchanged.
- SIGINT or SIGTERM: exit 1, `reason` interrupted, grok process group signaled, no branch.
- SIGKILL: the next `./pfy build --reap` exits 0 and writes `ABORTED` / `no-receipt` for a cloud pid whose receipt is missing. Reap reads only `<repo>/tmp/cloud-build.pids.json`. It does not signal a pgid listed only in `tmp/local-build.pids.json`.
- Timeout: exit 3, `reason` timeout, no branch.

Redact tokens, bearer values, AKIA keys, and private-key blocks in the receipt. Default protect globs: `auth.json`, `.env`, `*.pem`, `pipelines/dogfood/**/grok-home/**`.

Worktree: `<repo>/tmp/cloud-build/<stamp>/`, removed on PASS. Branch prefix `cloud/`. Default receipt dir: `<caller-repo>/pipelines/dogfood/build-cloud/<stamp>/receipt.json`. Add `pipelines/dogfood/build-cloud/` to `.gitignore` (that one line only).

Review is a second cloud grok call whose reply contains `verdict: accept` or `verdict: reject`. Tests use a fake grok. Never a local model.

Dispatch in `scripts/pfy` `cmd_build` only:

- Arg `--local` anywhere: exec `scripts/pfy_build_local.py` unchanged.
- First arg `-p` or `p`: stay on `scripts/pfy_build_p.py` (`p` shifted to `-p`).
- First arg `--prompt` or `--prompt-file`: stay on `scripts/pfy_build_p.py`.
- Every other invocation, including `--help` and `-h`, execs `scripts/pfy_build_cloud.py`.

## Owned files

- `scripts/pfy_build_cloud.py` (new)
- `tests/test_pfy_build_cloud.py` (new)
- `scripts/pfy`, build help paragraph and `cmd_build` only
- `.gitignore`, one added line: `pipelines/dogfood/build-cloud/`
- `docs/ops/HANDOFF-mvp-cloud-1031.md`
- `docs/ops/RUN-LOG-mvp-cloud-1031.md`
- `docs/ops/AUTONOMOUS-DECISIONS-mvp-cloud-1031.md`

## Forbidden files

`scripts/pfy_build_local.py`, `scripts/pfy_build_p.py`, `scripts/pfy_local_build_eval.py`, `tests/test_pfy_build_local.py`, `tests/test_pfy_build_local_review.py`, `tests/test_pfy_build_p.py` (run it, do not edit), `tests/test_pfy_local_build_eval.py`, `pfylib/build_preflight.py`, `pfylib/attach.py`, `eval/mvp-1031/`, `eval/mvp3/`, `docs/modules/pfy-build.md`, `docs/ops/pfy-build-daily.md`, `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `docs/modules/README.md`, `docs/modules/pfylib.md`, `data/tools.json`, `TOOLS.md`, `sources/`. Do not import `pfylib.build_preflight`. Inline the same classifier regexes so this branch tests alone.

## Ordered work

1. Write the loop exits into the run log before any code.
2. Confirm `origin/main` still has no `scripts/pfy_build_cloud.py`. If it does, read it and skip work that is already done.
3. Skeleton: argparse, usage exit 2, dry-run receipt, no grok. Commit and push.
4. Dispatch in `scripts/pfy` as specified. A test proves `-p` still reaches the dogfood script and a positional task reaches the new script. Commit and push.
5. PASS path: worktree from `--base`, fake grok writes a file, gate runs, review accepts, commit of reviewed paths only, branch `cloud/`, caller porcelain unchanged, receipt fields match the DoD. Commit and push.
6. Retries: gate red then PASS; review reject then accept; final reject leaves no branch. Commit and push.
7. No-change runs the gate and does not PASS on an empty diff. Gitignored extra file is not committed. Commit and push.
8. Rate limit, auth with an empty HOME, dirty caller, SIGTERM, and reap versus a local-only pid. Commit and push.
9. `.gitignore` line. Re-run `tests.test_pfy_build_p` and the new module. Commit and push.
10. Handoff on any exit.

## Acceptance tests

All in `tests/test_pfy_build_cloud.py`, temp git repos, fake grok, no network, no auth file:

1. PASS: branch and commit match the receipt, caller porcelain unchanged.
2. Gate red then retry then PASS, attempts length 2, no commit before the green attempt.
3. Review reject then retry then accept.
4. Final review reject: exit 1, `reason` review-rejected, no branch.
5. No-change: gate text appears in the second prompt; spent retries exit 1 with no branch.
6. Gitignored extra file is absent from the commit tree.
7. Rate-limit text: exit 4, recovery contains `./pfy build --local`, no branch.
8. `not logged in` and a missing grok binary: exit 1, `reason` unauthenticated. Empty HOME does not raise on a missing auth.json.
9. Dirty caller file stays dirty and is not in the new commit.
10. SIGTERM: exit 1, `reason` interrupted, no branch. `--reap` writes ABORTED for a cloud pid with no receipt and does not signal a subprocess listed only in the local pid file.
11. `pfy build -p --help` still shows the dogfood help. `pfy build --help` names the daily command. `tests.test_pfy_build_p` passes.

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
