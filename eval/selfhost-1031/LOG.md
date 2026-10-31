# Selfhost 1031 build log

Each row is one real `./pfy build` from this worktree against a throwaway clone under `tmp/`. Receipts are redacted copies. A human accept is cherry-picked onto `bot/mvp-selfhost-1031` with a `Built-by` trailer.

Columns: n, slug, why, command, wall_s, exit, attempts, review, human, commit, notes.

| n | slug | why | command | wall_s | exit | attempts | review | human | commit | notes |
|---|------|-----|---------|--------|------|----------|--------|--------|--------|-------|
| 01 | receipt-dir | Parked in docs/automation/x-intake-2026-10-16-handoff.md: PFY_SMOKE_RECEIPT_DIR is not required to be absolute, so a relative value can clobber a repo receipt. | `./pfy build --repo tmp/selfhost-clones/target-1 --base HEAD --test-cmd 'python3 -m unittest tests.test_smoke_receipt_absolute' --receipt-dir eval/selfhost-1031/01-receipt-dir` plus the task file | 129 | 0 | 1 | accept | accept | 00dbdd9 | gate before exit 1, after exit 0. Only examples/x-intake-local/smoke.py. |
