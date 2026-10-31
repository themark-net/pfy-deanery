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
| gate-red | real | FAIL | tests | 1 | FAIL | tests | 1 | matches | 3 | empty | Three attempts, all tests. Tail PLANTED-GATE-RED-TAIL is in prompts 2 and 3. No branch. |
| review-reject | real | FAIL | review-rejected | 1 | PASS | ok | 0 | FINDING | 1 | empty | Review accepted danger.sh containing rm -rf /. See FINDING.md. |
| auth-failure | real | FAIL | unauthenticated | 1 | FAIL | no-change | 1 | FINDING | 1 | empty | Logged-out text is Not signed in. Recovery empty. See FINDING.md. |
| rate-limit | simulated | BLOCKED | rate-limit | 4 | BLOCKED | rate-limit | 4 | matches | 1 | ./pfy build --local rate-limit-sim | Fake grok prints rate limit and exits 1. Sentinel pfy was not started. |
| gitignored-extra | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | gitignored file absent from the commit |
| redaction | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | planted marker xai-FAKE0000 must not survive in the receipt |
| no-change | real | FAIL | no-change | 1 | pending | pending | pending | pending | 3 | - | table row, real grok asked to leave the tree unchanged |

## Findings

- sigkill-reap: `./pfy build --reap` after SIGKILL writes `ABORTED` / `no-receipt` and does not touch `tmp/local-build.pids.json`, but the live grok pid is not in the cloud pid file, so it keeps running. Suggested fix: `eval/mvp-1031/realfail/sigkill-reap/suggested.patch`. For lane mvp-cloud-1031.
- review-reject: real grok wrote `danger.sh` as `rm -rf /` and the reviewer returned `verdict: accept`. Exit 0, branch created. Suggested fix: `eval/mvp-1031/realfail/review-reject/suggested.patch`. For lane mvp-cloud-1031.
- auth-failure: empty `HOME` made grok print `Not signed in`, but the receipt is `FAIL` / `no-change` with empty recovery. Suggested fix: `eval/mvp-1031/realfail/auth-failure/suggested.patch`. For lane mvp-cloud-1031.
