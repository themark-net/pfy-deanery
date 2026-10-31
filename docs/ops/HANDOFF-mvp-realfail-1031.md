# Handoff mvp-realfail-1031

Status: in progress. Exit card is written. Failure runs have not started.

Branch: `bot/mvp-realfail-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-realfail-1031`
Base: `origin/bot/mvp-cloud-1031`

## Done

None yet.

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

Merge `origin/bot/mvp-cloud-1031`, then the interrupted-run case on a throwaway repo under `tmp/`.
