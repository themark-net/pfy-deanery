# mvp3-fix-1031: fix Tester FAIL on bot/mvp3-review-retry (d624535)

You are in worktree ~/DEVELOP/pfy-mentat/tmp/mvp3 on branch bot/mvp3-review-retry. Tester FAILed d624535 (Reviewer passed). Fix it here as plain new commits on top of d624535. NO rebase, NO amend, NO force push, NO merge to main, NO PR. Push with plain `git push origin bot/mvp3-review-retry` after each green item so it stays a fast-forward.

## Items, in order
B1. A gitignored out-of-scope file gets committed unreviewed. The changed list at scripts/pfy_build_local.py:~854 uses `git status --porcelain -uall`, which skips ignored files. The commit at ~:3204 runs `git add -A -f`, and the scope check at ~:2976 and the review never see that file. Cherry-pick 7bdede7 ("stage only reviewed paths on local build") and then 88ebcae ("no-change runs the gate") from origin/bot/mvp-review-fix-1031 with `git cherry-pick -x`. 7bdede7 conflicts only on docs/ops/*mvp-review-fix-1031.md files that do not exist here: resolve by `git rm` of those docs (keep the code and test changes). If the code does not apply cleanly, port the same behavior by hand. Then ADD an E2E test: a run where the attempt writes a gitignored out-of-scope file (plus an in-scope change) must NOT commit the ignored file, and the committed tree has only reviewed paths.
B2. Behavior tests that the review fails closed. Each of these must NOT commit and must exit nonzero with a clear status: reviewer HTTP error (M10), review timeout (M11), empty diff sent to the reviewer (M18). Fix the code if any test shows it fails open.
Should-fix tests to kill surviving mutants:
- M08: retries spent on scope or wiring checks must exit nonzero.
- M14: the previous diff must reach the retry prompt.
- M17: --no-review must not retry.
S6. Reconcile the mvp3 handoff doc (docs/ops/HANDOFF-*mvp3*). Line 3 must say the review loop code lands on main after Tester and Reviewer PASS, with the local default staying NO-GO. Update the "Do not merge from this run" line to match that.
T6. Fix the t6 receipt end time: it says 04:09Z, but the run ended about 04:07Z. Find it with `rg -n "04:09Z"` and correct it from the run's own log or timestamps if available, else set 04:07Z and note the source.

## Rules
- Tests are behavior or fail-and-recover tests, no tautological units. Mock the reviewer at the HTTP or subprocess boundary, not the function under test.
- Tests and scratch: TMPDIR=$PWD/tmp. Temp files only in this worktree's tmp/. No sudo, no system changes. Never touch ~/DEVELOP/pfy-mentat (main checkout) working tree. Never print secrets or auth.json contents. Do not kill processes you did not start.
- Full suite must run under the heavy lock: `TMPDIR=$PWD/tmp flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .` Targeted test files can run without the lock.
- Do NOT run scripts/pregate.sh. The operator runs it at your final tip.
- Loop exits: stop when all items are done and pushed (write `state: DONE` in docs/ops/RUN-LOG-mvp3-fix-1031.md), or after 3 failed tries on one item (record it as blocked and move on), or at 3h wall time (`state: wall cap`).
- Finish: write docs/ops/HANDOFF-mvp3-fix-1031.md with the final SHA, each item's commit, suite counts, and any open item. Commit and push. Plain short sentences, no em dashes.
