# Real failure receipts (wave 4)

One row per run. Expected values come from the Functional MVP failure table. `matches` means status, reason, and process exit matched that row and the case invariants held. `FINDING` means a DoD clause failed. Notes say what differed. The runner was not edited.

Rows: partial

| Case | Mode | Exp status | Exp reason | Exp exit | Obs status | Obs reason | Obs exit | Verdict | Attempts | Recovery | Notes |
|------|------|------------|------------|----------|------------|------------|----------|---------|----------|----------|-------|
| tmp-unwritable | real | FAIL | worktree-failed | 1 | FAIL | runner-crash | 1 | FINDING | 1 | empty | repo tmp is mode 555 review None |
