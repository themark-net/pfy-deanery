# Real failure receipts

One row per run. `pending` has no receipt yet. `matches` means observed status, reason, and process exit equal the expected cells. `FINDING` means they do not, and the notes cell says what differed.

Expected values come from the Functional MVP failure table. Process exit is the `./pfy build` exit code. Reap's process exit is 0 while the receipt status is `ABORTED`.

| Case | Mode | Exp status | Exp reason | Exp exit | Obs status | Obs reason | Obs exit | Verdict | Attempts | Recovery | Notes |
|------|------|------------|------------|----------|------------|------------|----------|---------|----------|----------|-------|
| interrupted-sigint | real | FAIL | interrupted | 1 | FAIL | interrupted | 1 | matches | 1 | empty | SIGINT after grok started. No cloud branch. Caller HEAD and status unchanged. No orphan from this run. |
| interrupted-sigterm | real | FAIL | interrupted | 1 | FAIL | interrupted | 1 | matches | 1 | empty | SIGTERM after grok started. No cloud branch. Caller HEAD and status unchanged. No orphan from this run. |
| sigkill-reap | real | ABORTED | no-receipt | 0 | ABORTED | no-receipt | 0 | FINDING | 0 | empty | Reap receipt and the planted sleep match. Live grok survived reap. See FINDING.md. |
| timeout | real | TIMEOUT | timeout | 3 | TIMEOUT | timeout | 3 | matches | 1 | empty | Real grok with --timeout 5. Exit 3. No branch. Caller unchanged. Grok session gone. |
| dirty-caller | real | PASS | ok | 0 | PASS | ok | 0 | matches | 1 | empty | Untracked and staged caller files stayed dirty. Commit adds only kept.py. --no-review. |
| gate-red | real | FAIL | tests | 1 | pending | pending | pending | pending | 3 | - | planted failing gate, retries spent, tail in the next prompt |
| review-reject | real | FAIL | review-rejected | 1 | pending | pending | pending | pending | - | - | unsafe instruction, record the verdict |
| auth-failure | real | FAIL | unauthenticated | 1 | pending | pending | pending | pending | - | - | HOME is an empty dir under tmp |
| rate-limit | simulated | BLOCKED | rate-limit | 4 | pending | pending | pending | pending | - | - | fake-grok seam, not a real rate limit |
| gitignored-extra | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | gitignored file absent from the commit |
| redaction | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | planted marker xai-FAKE0000 must not survive in the receipt |
| no-change | real | FAIL | no-change | 1 | pending | pending | pending | pending | 3 | - | table row, real grok asked to leave the tree unchanged |

## Findings

- sigkill-reap: `./pfy build --reap` after SIGKILL writes `ABORTED` / `no-receipt` and does not touch `tmp/local-build.pids.json`, but the live grok pid is not in the cloud pid file, so it keeps running. Suggested fix: `eval/mvp-1031/realfail/sigkill-reap/suggested.patch`. For lane mvp-cloud-1031.
