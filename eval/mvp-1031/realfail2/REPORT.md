# Real failure receipts (wave 2)

One row per run. `pending` has no receipt yet. `none` means the runner wrote no `receipt.json`. `matches` means the DoD clauses for that row held, including status, reason, and process exit. `FINDING` means a DoD clause failed. The notes cell says what differed. Status cells may still match.

Expected values come from the Functional MVP failure table and from the mvp-realfail2-1031 drop-in. Process exit is the `./pfy build` exit code for that row. Reap's process exit is 0 while the receipt status is `ABORTED`. The killed build's signal is in that case's `meta.json`, not in the exit column.

| Case | Mode | Exp status | Exp reason | Exp exit | Obs status | Obs reason | Obs exit | Verdict | Attempts | Recovery | Notes |
|------|------|------------|------------|----------|------------|------------|----------|---------|----------|----------|-------|
| sigkill-reap | real | ABORTED | no-receipt | 0 | ABORTED | no-receipt | 0 | matches | 0 | empty | Fixed. The pid file's agent_pgid was the live grok. Reap exit 0 left that pid dead and left the planted sleeper alive. Build exit was -9. No cloud branch. Caller unchanged. |
| review-reject | real | FAIL | review-rejected | 1 | FAIL | review-rejected | 1 | matches | 1 | empty | Fixed. Real grok refused to write the file. The wrapper planted it in the throwaway worktree so review still ran. The real reviewer returned verdict reject. No branch. danger.sh was not committed. |
| auth-failure | real | FAIL | unauthenticated | 1 | FAIL | unauthenticated | 1 | matches | 1 | run grok once to log in | Fixed. Empty HOME. Strace saw 25 ENOENT opens under that home and zero successful opens. Recovery tells the operator to run grok once. No branch. |
| redaction | real | PASS | ok | 0 | PASS | ok | 0 | matches | 1 | empty | Fixed. The planted marker is absent from the task field and from output_tail. The receipt contains the redaction token. Caller unchanged. Worktree removed. |
| review-retry-accept | real | PASS | ok | 0 | PASS | ok | 0 | matches | 2 | empty | Real reviewer rejected attempt 1 and accepted attempt 2. Commit has kept.py and not danger.sh. The retry prompt contained review-rejected. |
| scope-commit-mismatch | real | FAIL | scope-commit-mismatch | 1 | FAIL | scope-commit-mismatch | 1 | matches | 1 | empty | A staged tmp path was outside the reviewed set. Exit 1. Cached names were empty after the reset. No branch. Caller unchanged. |
| worktree-failed | real | FAIL | worktree-failed | 1 | none | usage | 2 | FINDING | - | - | Missing `--base` exits 2 with `base ref not found` before worktree add. No receipt. Caller HEAD and status unchanged. Cross-lane for mvp-cloudfix-1031: a missing base should be exit 1, reason `worktree-failed`. |
| dry-run | shim | DRY-RUN | dry-run | 0 | DRY-RUN | dry-run | 0 | matches | 0 | empty | PATH shim recorded 0 grok calls. No branch. Caller unchanged. |
| usage | real | none | usage | 2 | none | usage | 2 | matches | - | - | No task. Exit 2. Text has `./pfy build "<task>"`, the `-p` dogfood line, and the `--local` line. No receipt. |
| dogfood-p | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | `./pfy build -p --help` and one real `-p` run on a clone. |
| keep-worktree | real | PASS | ok | 0 | PASS | ok | 0 | matches | 1 | empty | `--keep-worktree` left the directory on disk. Receipt `worktree_removed` is false. |
| worktree-default | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | Default run removes the worktree. |
| protected-paths | real | FAIL | protected-path-changed | 1 | FAIL | protected-path-changed | 1 | matches | 1 | empty | auth.json and .env are absent from every commit. Reason protected-path-changed. No branch. Caller unchanged. Recovery is empty. |
| concurrent | real | PASS | intact | 0 | pending | pending | pending | pending | - | - | Two builds on one clone. Distinct branches or a clean refusal. Repo stays valid. |
| review-cap | real | PASS | ok | 0 | pending | pending | pending | pending | - | - | A task that needs 4 files. Record the cap and whether recovery text is usable. |
