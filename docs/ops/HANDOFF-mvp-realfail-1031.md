# Handoff mvp-realfail-1031

Status: in progress. Interrupted SIGINT and SIGTERM match the DoD. Later cases are not run yet.

Branch: `bot/mvp-realfail-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-realfail-1031`
Base: `origin/bot/mvp-cloud-1031`

## Done

- exits `07c45ca`: exit card, pending report, receipt checker.
- merge `c0cf507`: `origin/bot/mvp-cloud-1031` at `d94d2b6`.
- interrupted: real SIGINT and SIGTERM. Exit 1, status FAIL, reason interrupted, no branch, caller unchanged, grok session gone. Receipts under `eval/mvp-1031/realfail/interrupted-sigint/` and `interrupted-sigterm/`.

## Skipped

None yet.

## Test evidence

None yet.

## How a change fails and recovers

The receipt checker rejects a committed receipt whose status or reason disagrees with `eval/mvp-1031/realfail/REPORT.md`, and it rejects a secret-like string. Recovery is to fix the report or redact the receipt, then rerun `python3 -m unittest tests.test_mvp_1031_realfail_receipts`.

## Cross-lane requests

None yet.

## Gate

Docs, eval, and test only. Pregate plus Reviewer when the lane finishes. Pregate has not been run.

## Next

SIGKILL a real run, then `./pfy build --reap`, with a planted local sleep that must survive.
