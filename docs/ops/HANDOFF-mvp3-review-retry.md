# Handoff: MVP-3 review-and-retry loop for `./pfy build --local`

Branch `bot/mvp3-review-retry`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp3`. Base of the branch is `bot/mvp2-report` `85c53dc`. Trial base for every arm is `997d89264495861a178713ccf7d4447ea828afc4`. No PR. After Tester and Reviewer PASS, the bot fast-forwards main.

## Status (2026-10-30 PT)

Done as a measurement. No-go as the default for build-only runs.

Part 1 is `b25fc35`: the review loop in `scripts/pfy_build_local.py`. Suite after that change: `python3 -m unittest discover -s tests -t .` with bwrap hidden, Ran 955 OK, skipped=100, 501.227 s. Run 2 did not change the runner.

Part 2 re-ran the six MVP-2 tasks locally. Report: `eval/mvp3/REPORT.md`.

| | Gate | Review accept | Wall |
|--|------|---------------|------|
| MVP-3 loop | 5/6 | 5/6 | 3859.9 s |
| MVP-3 human | 5/6 | 4/6 | 3859.9 s |
| MVP-2 local | 5/6 | 4/6 | 1694.0 s |
| MVP-2 cloud | 6/6 | 6/6 | 583.6 s |

t1, t2, t3, t6: loop and human accept. t4: FAIL no-change after 3 attempts, both reject. t5: gate PASS, loop accept, human reject, because commit `4b017e4` also adds gitignored `pipelines/smoke/kander/latest.json`.

The trial ran in two sessions. Run 1 (cap from 2026-10-30T17:50:52Z) died at 11:13 PDT when the grok CLI stopped a background task at 600 s, during t4. t1 to t3 were already committed. Run 2 (cap from 2026-10-31T03:07:13Z to 06:07:13Z) finished t4, t5, and t6. Each session had its own 3 h cap. Details are in the report and in `docs/ops/RUN-LOG-mvp3-review-retry.md`.

## How to run

```bash
python3 eval/mvp3/run_trial.py prove-red
python3 eval/mvp3/run_trial.py arm L t4-timeout-substep
```

Model `qwen3.6:35b` only. Floor is 32 GiB MemAvailable+SwapFree. Unload that model when it is the only one loaded. Raw logs stay under `tmp/mvp3-runs/` (gitignored).

## How this fails / how we recover

| Risk | How it fails | Recovery |
|------|--------------|----------|
| Reviewer too strict | Real tasks end PASS-REJECTED | Receipts name the check. `--no-review` is the one-attempt MVP-1 path |
| Reviewer too loose | t5: loop accepted a commit that contains a gitignored receipt | Read the commit, not only the attempt diff. The scope check uses `git status`, and `git add -A -f` then adds ignored paths |
| Model writes nothing | t4: three no-change attempts, 2203.5 s, gate still red | The review never runs without a diff. A retry does not force a write |
| Host memory or a hung arm | Floor, lockup, or the 3 h cap | The run log records STOPPED or not-run. Kill only process groups this run started |
| CLI ends a background arm | Run 1, 600 s background wait | Run the arm with `setsid` and poll it in the foreground |

## Known gaps

The scope check and the commit do not see the same files. t4's broad-label failure from MVP-2 was not re-measured, because this model never wrote a patch. Wall time is worse than MVP-2 local.

## Gate and what is left

Tester plus Reviewer at the pinned SHA. Part 1 changes runtime. No Feature GO. Do not merge from this run.

Next code fix, not done here: make the scope check include every path `git add -A -f` will commit, then re-run t5. Separately, t4 still needs a local run that writes the sub-step catch.
