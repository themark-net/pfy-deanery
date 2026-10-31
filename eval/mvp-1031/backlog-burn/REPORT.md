# Backlog burn report (mvp-backlog-burn-1031)

Daily-use proof: real cloud `./pfy build` on small backlog items, then a human read of the diff. Cloud only. No `--local`. Caller checkout is this worktree. The build target is a throwaway clone under `tmp/`.

Columns: item, receipt status, attempts, wall seconds, verdict, landed SHA.

Rows are appended as each item finishes. A missing row means that item has not finished.

| Item | Receipt | Attempts | Wall s | Verdict | Landed SHA |
|------|---------|----------|--------|---------|------------|
| enterable not-ok: store stripped next_steps | PASS ok, review accept, gate 1 then 0 | 1 | 53 | accept | c354d9c |
| catalog apply: keep live receipts and the stage stamp | PASS ok, review accept, gate 1 then 0 | 2 | 784 | accept | 5f7ce36 |
| entry 149: publish the live stub-test count | PASS ok, review accept, gate 1 then 0 | 1 | 28 | accept | 42fc4e1 |
