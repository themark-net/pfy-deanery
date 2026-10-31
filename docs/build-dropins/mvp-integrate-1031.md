# Lane mvp-integrate-1031

Branch: `bot/mvp-integrate-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-integrate-1031`
Base: `origin/main`
Run log: `docs/ops/RUN-LOG-mvp-integrate-1031.md`
Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-integrate-1031.md`
Handoff: `docs/ops/HANDOFF-mvp-integrate-1031.md`

Needs a local model: no. Do not start Ollama. Do not pass `--local` on the demo.

This lane merges the round-1 branches plus MVP-3 and the two overnight branches, runs the suite once under the lock, then runs one real cloud `./pfy build` on the fixture task and records the receipt. It is not in the lane TSV. Launch it when the round-1 branches have been pushed, or when you were started as the integration session. Do not poll for hours. A missing branch is recorded and skipped.

## Definition of Done

1. This branch contains merge commits, in the order below, for every listed branch that exists on origin. No rebase, no force push, no merge to main, no PR, no tag.
2. The full suite was run once: `nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .`. Counts are in the handoff. A failure that also fails on the pre-merge base is recorded and that area is skipped. A failure introduced by a conflict you resolved is fixed only inside that conflict. Do not rewrite a lane's feature.
3. If `scripts/pfy_build_cloud.py` and `eval/mvp-1031/check_receipt.py` are both present, one real `./pfy build` demo ran against a temp fixture repo. The receipt is committed at `eval/mvp-1031/demo-receipt.json`. `eval/mvp-1031/REPORT.md` records the command, the exit code, the branch, the commit, the review verdict, and the receipt path.
4. PASS demo: `check_receipt.py` exits 0, and `git -C` the fixture repo shows the `cloud/` branch at the receipt commit. The integrate checkout's own branch was not the task target.
5. If the demo hits rate limit or auth failure: commit that receipt anyway, `REPORT.md` says the demo did not PASS, and this lane does not start `--local` and does not invent a green result.
6. `docs/TODO.md` has one MVP note. `docs/PENDING-HANDOFF.md` has one new dated section at the top. `docs/modules/README.md` has one row for `docs/modules/pfy-build.md` when that file exists. No Feature GO. Catalog HOLD unchanged. No GitHub issue opened or closed.

## Owned files

Merge resolution on the files the incoming branches already touch, plus these writes:

- `eval/mvp-1031/demo-receipt.json`
- `eval/mvp-1031/REPORT.md`
- `docs/TODO.md` (one MVP note only; do not delete rows)
- `docs/PENDING-HANDOFF.md` (one new section at the top)
- `docs/modules/README.md` (one row, after the backlog merge)
- `docs/ops/HANDOFF-mvp-integrate-1031.md`
- `docs/ops/RUN-LOG-mvp-integrate-1031.md`
- `docs/ops/AUTONOMOUS-DECISIONS-mvp-integrate-1031.md`
- `scripts/pfy_build_cloud.py` only for the optional classifier import below, under 40 lines

## Forbidden files

Do not edit a lane feature except to resolve a merge conflict or to do the under-40-line import. Do not edit `scripts/pfy_build_p.py`. Do not edit catalog scores, `TOOLS.md`, or `data/tools.json` except where a merge already brought those changes in. Do not read `~/.grok/auth.json`.

## Ordered work

1. Write the loop exits into the run log before merging.
2. `git fetch origin`. Merge in this order (merge commits):
   1. `origin/bot/backlog-catalog-1030`
   2. `origin/bot/pfy-followups-1030`
   3. `origin/bot/mvp3-review-retry`
   4. `origin/bot/mvp-review-fix-1031`
   5. `origin/bot/mvp-preflight-1031`
   6. `origin/bot/mvp-surface-1031`
   7. `origin/bot/mvp-eval-1031`
   8. `origin/bot/mvp-cloud-1031`
   If a branch is missing, log it and continue. Push after each successful merge.
3. Conflict rule: the round-1 owner of a file wins when the plan's matrix names one. For `docs/TODO.md` and `docs/modules/pfylib.md`, keep both sides' facts. Do not drop a done row. Record each conflict as one decisions-file line.
4. If `classify_cloud_failure` exists in `pfylib/build_preflight.py` and `scripts/pfy_build_cloud.py` has an inline copy, switch the runner to the import when the edit is under 40 lines, then run `tests.test_pfy_build_cloud` and `tests.test_build_preflight`. If the edit is bigger, leave the inline copy and name `mvp-dedupe-1031` as the next step.
5. Run the full suite under the flock as in the DoD. Targeted modules that must be green when those files exist: `tests.test_pfy_build_p`, `tests.test_pfy_build_cloud`, `tests.test_pfy_build_local`, `tests.test_pfy_build_local_review`, `tests.test_build_preflight`, `tests.test_pfy_build_docs`, `tests.test_mvp_1031_receipt`, `tests.test_docs_hygiene`.
6. Demo, only when both the cloud runner and the checker exist. From this worktree:

```text
mkdir -p tmp
bash eval/mvp-1031/init_fixture.sh "$PWD/tmp/mvp-fixture-repo"
./pfy build "Make add return the sum of its two arguments so the fixture test passes." \
  --repo "$PWD/tmp/mvp-fixture-repo" \
  --base main \
  --test-cmd "python3 -m unittest test_add" \
  --receipt-dir "$PWD/tmp/mvp-fixture-receipt"
```

Copy `tmp/mvp-fixture-receipt/receipt.json` to `eval/mvp-1031/demo-receipt.json`. Run `python3 eval/mvp-1031/check_receipt.py` on it. Write `eval/mvp-1031/REPORT.md`. Commit and push. Do not commit `tmp/`.
7. TODO note, PENDING-HANDOFF section, README row. Handoff. Final run-log `state:` line.

## Acceptance tests

This lane does not add a new test module. The acceptance is the suite counts plus the demo:

- Suite command above, recorded in the handoff.
- `python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt.json` exit code recorded. Exit 0 is the PASS demo. Exit 1 with a rate-limit or unauthenticated receipt is an honest blocked demo, not a lane failure to hide.
- `tests.test_pfy_build_p` still passes after the merges (dogfood path unchanged).

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

## Pass 2 addendum (operator, 2026-10-31 afternoon)

This is integration pass 2. Your branch already has pass 1; read your own handoff and run log first. Merge, never rebase, never force push, never touch main.

1. `git fetch origin`. Merge the new tips of the pass-1 branches, including the re-pinned `origin/bot/mvp3-review-retry` (d624535 or newer) and `origin/bot/pfy-followups-1030` (c0d38af or newer: Reviewer B1 bwrap-probe fix and B2 root-length test fix).
2. Then merge these lane branches in this order when they exist on origin: `bot/mvp-cloudfix-1031` (after cloud and preflight), `bot/mvp-review-fix2-1031` (after review-fix), `bot/mvp-intfix-1031` (after review-fix2), `bot/mvp-followups-fix2-1031` (after followups), `bot/mvp-tmpclean-1031`, `bot/mvp-docs-1031`, then the test and eval lanes `bot/mvp-mutate-cloud-1031`, `bot/mvp-mutate-review-1031`, `bot/mvp-realfail-1031`, `bot/mvp-realfail2-1031`, `bot/mvp-sixtask-1031`, `bot/mvp-dogfood-1031`, `bot/mvp-dogfood2-1031`, `bot/mvp-gom-dogfood-1031`. Do NOT merge `bot/mvp-selfhost-1031` (Mark cherry-picks from it). A branch whose lane is still running is merged at its current pushed tip; record the SHA.
3. Classifier overlap: your pass-1 commit d966e83 imported `classify_cloud_failure` into the cloud runner, and lane mvp-cloudfix-1031 did the same dedupe on its branch. Resolve in favor of cloudfix's version of `scripts/pfy_build_cloud.py` (it has later fixes), keep exactly one import and no inline duplicate classifier, and prove it with `tests.test_pfy_build_cloud*` and `tests.test_build_preflight`.
4. Full suite once: `TMPDIR=$PWD/tmp nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .`. Record counts. Fix only conflict-caused failures; record the rest with the owning lane.
5. Demo 2 on a slightly bigger REAL task: pick one real small backlog item from pfy-mentat (`docs/TODO.md` or a handoff Known gap) that needs 2 or 3 files (code plus a behavior test), not in any MVP lane's owned files. Make a throwaway clone of this worktree under `tmp/demo2-target`, run the real cloud `./pfy build "<task>" --repo tmp/demo2-target` from this worktree, and check it with `eval/mvp-1031/check_receipt.py`. Commit the redacted receipt as `eval/mvp-1031/demo-receipt-pass2.json` and add a Pass 2 section to `eval/mvp-1031/REPORT.md`: command, task and why picked, wall time, exit, attempts, branch, commit, review verdict, your human verdict, and each DoD PASS line (1 to 6) checked. If it does not PASS, commit the receipt anyway and say so; never invent a green result.
6. Do NOT run pregate yourself; the operator runs it on your final tip after you exit. Update the handoff with the final tip SHA and push.
