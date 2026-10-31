# Handoff mvp-realfail-1031

Status: in progress. Interrupted SIGINT and SIGTERM match the DoD. Later cases are not run yet.

Branch: `bot/mvp-realfail-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-realfail-1031`
Base: `origin/bot/mvp-cloud-1031`

## Done

- exits `07c45ca`: exit card, pending report, receipt checker.
- merge `c0cf507`: `origin/bot/mvp-cloud-1031` at `d94d2b6`.
- interrupted `00d0ec4`: real SIGINT and SIGTERM. Exit 1, status FAIL, reason interrupted, no branch, caller unchanged, grok session gone.
- sigkill-reap: receipt `ABORTED` / `no-receipt`, reap exit 0, planted local sleep survived. FINDING: live grok was still running after reap. See `eval/mvp-1031/realfail/sigkill-reap/FINDING.md`.

## Skipped

None yet.

## Test evidence

None yet.

## How a change fails and recovers

The receipt checker rejects a committed receipt whose status or reason disagrees with `eval/mvp-1031/realfail/REPORT.md`, and it rejects a secret-like string. Recovery is to fix the report or redact the receipt, then rerun `python3 -m unittest tests.test_mvp_1031_realfail_receipts`.

## Cross-lane requests

- mvp-cloud-1031: SIGKILL during the grok call leaves a stale `agent_pgid` in `tmp/cloud-build.pids.json` (the previous gate pid). `./pfy build --reap` then exits 0 and writes `ABORTED` / `no-receipt`, but the live grok process is not signaled. Evidence and a suggested patch: `eval/mvp-1031/realfail/sigkill-reap/`. Please save the pid file after `Popen` sets `state.agent_pgid`. This lane will rerun the case after the next cloud commit.

## Gate

Docs, eval, and test only. Pregate plus Reviewer when the lane finishes. Pregate has not been run.

## Next

Real run with a very short `--timeout`. Expect exit 3 and `TIMEOUT`.
