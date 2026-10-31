# Real failure receipts (wave 2)

One row per run. `pending` has no receipt yet. `none` means the runner wrote no `receipt.json`. `matches` means the DoD clauses for that row held, including status, reason, and process exit. `FINDING` means a DoD clause failed. The notes cell says what differed. Status cells may still match.

Expected values come from the Functional MVP failure table and from the mvp-realfail2-1031 drop-in. Process exit is the `./pfy build` exit code for that row. Reap's process exit is 0 while the receipt status is `ABORTED`. The killed build's signal is in that case's `meta.json`, not in the exit column.

| Case | Mode | Exp status | Exp reason | Exp exit | Obs status | Obs reason | Obs exit | Verdict | Attempts | Recovery | Notes |
|------|------|------------|------------|----------|------------|------------|----------|---------|----------|----------|-------|
| sigkill-reap | real | ABORTED | no-receipt | 0 | pending | pending | pending | pending | - | - | Re-check of the realfail FINDING. Reap must kill the live grok and must leave the planted sleeper alone. |
| review-reject | real | FAIL | review-rejected | 1 | pending | pending | pending | pending | - | - | Re-check. `--retries 0` so attempt 1 cannot hide an accept. |
| auth-failure | real | FAIL | unauthenticated | 1 | pending | pending | pending | pending | - | - | Re-check. Empty HOME. Recovery must tell the operator to run grok once. |
| redaction | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | Re-check. Planted marker must be absent from the receipt task and output_tail. |
| review-retry-accept | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | Real reviewer. Attempt 1 rejected, attempt 2 accepted. |
| scope-commit-mismatch | real | FAIL | scope-commit-mismatch | 1 | pending | pending | pending | pending | - | - | Staged path outside the reviewed set. Index reset. No branch. |
| worktree-failed | real | FAIL | worktree-failed | 1 | pending | pending | pending | pending | - | - | `--base` is a ref that does not exist. Caller unchanged. |
| dry-run | shim | DRY-RUN | dry-run | 0 | pending | pending | pending | pending | - | - | PATH shim records grok calls. Expect zero calls and no branch. |
| usage | real | none | usage | 2 | pending | pending | pending | pending | - | - | No task. Daily command plus the `-p` and `--local` pointers. |
| dogfood-p | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | `./pfy build -p --help` and one real `-p` run on a clone. |
| keep-worktree | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | `--keep-worktree` keeps the worktree and the receipt records that. |
| worktree-default | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | Default run removes the worktree. |
| protected-paths | real | FAIL | protected-path-changed | 1 | pending | pending | pending | pending | - | - | `auth.json` and `.env` stay out of the commit. Reason recorded. |
| concurrent | real | PASS | intact | 0 | pending | pending | pending | pending | - | - | Two builds on one clone. Distinct branches or a clean refusal. Repo stays valid. |
| review-cap | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | A task that needs 4 files. Record the cap and whether recovery text is usable. |
