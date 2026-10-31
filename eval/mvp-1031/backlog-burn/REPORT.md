# Backlog burn report (mvp-backlog-burn-1031)

Daily-use proof: real cloud `./pfy build` on small backlog items, then a human read of the diff. Cloud only. No `--local`. Caller checkout is this worktree. The build target is a throwaway clone under `tmp/`.

Columns: item, receipt status, attempts, wall seconds, verdict, landed SHA.

Rows are appended as each item finishes. A missing row means that item has not finished.

| Item | Receipt | Attempts | Wall s | Verdict | Landed SHA |
|------|---------|----------|--------|---------|------------|
