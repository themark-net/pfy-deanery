# Real failure receipts

One row per run. `pending` has no receipt yet. `matches` means observed status, reason, and process exit equal the expected cells. `FINDING` means they do not, and the notes cell says what differed.

Expected values come from the Functional MVP failure table. Process exit is the `./pfy build` exit code. Reap's process exit is 0 while the receipt status is `ABORTED`.

| Case | Mode | Exp status | Exp reason | Exp exit | Obs status | Obs reason | Obs exit | Verdict | Attempts | Recovery | Notes |
|------|------|------------|------------|----------|------------|------------|----------|---------|----------|----------|-------|
| interrupted-sigint | real | FAIL | interrupted | 1 | FAIL | interrupted | 1 | matches | 1 | empty | SIGINT after grok started. No cloud branch. Caller HEAD and status unchanged. No orphan from this run. |
| interrupted-sigterm | real | FAIL | interrupted | 1 | FAIL | interrupted | 1 | matches | 1 | empty | SIGTERM after grok started. No cloud branch. Caller HEAD and status unchanged. No orphan from this run. |
| sigkill-reap | real | ABORTED | no-receipt | 0 | pending | pending | pending | pending | - | - | SIGKILL, then ./pfy build --reap |
| timeout | real | TIMEOUT | timeout | 3 | pending | pending | pending | pending | - | - | real grok, very short --timeout |
| dirty-caller | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | uncommitted file and staged file stay dirty |
| gate-red | real | FAIL | tests | 1 | pending | pending | pending | pending | 3 | - | planted failing gate, retries spent, tail in the next prompt |
| review-reject | real | FAIL | review-rejected | 1 | pending | pending | pending | pending | - | - | unsafe instruction, record the verdict |
| auth-failure | real | FAIL | unauthenticated | 1 | pending | pending | pending | pending | - | - | HOME is an empty dir under tmp |
| rate-limit | simulated | BLOCKED | rate-limit | 4 | pending | pending | pending | pending | - | - | fake-grok seam, not a real rate limit |
| gitignored-extra | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | gitignored file absent from the commit |
| redaction | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | planted marker xai-FAKE0000 must not survive in the receipt |
| no-change | real | FAIL | no-change | 1 | pending | pending | pending | pending | 3 | - | table row, real grok asked to leave the tree unchanged |

## Findings

None yet.
