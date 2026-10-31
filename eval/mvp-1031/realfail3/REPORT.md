# Real failure receipts (wave 4)

One row per run. Expected values come from the Functional MVP failure table. `matches` means status, reason, and process exit matched that row and the case invariants held. `FINDING` means a DoD clause failed. Notes say what differed. The runner was not edited.

Rows: partial

| Case | Mode | Exp status | Exp reason | Exp exit | Obs status | Obs reason | Obs exit | Verdict | Attempts | Recovery | Notes |
|------|------|------------|------------|----------|------------|------------|----------|---------|----------|----------|-------|
| detached-head | real | PASS | ok | 0 | PASS | ok | 0 | matches | 1 | empty | HEAD must stay detached at the same SHA review skipped |
| dirty-tree | real | PASS | ok | 0 | PASS | ok | 0 | matches | 1 | empty | dirty porcelain must survive. elapsed 12s review skipped |
| network-down | shim | FAIL | no-change | 1 | FAIL | no-change | 1 | matches | 1 | empty | PATH shim prints Network is unreachable and writes nothing review None |
| no-tests | real | FAIL | tests | 1 | FAIL | tests | 1 | matches | 1 | empty | default gate on a repo with no tests directory before_exit 1 review None |
| non-ascii | real | PASS | ok | 0 | PASS | ok | 0 | matches | 1 | empty | task keeps cafe-acute and the path contains a space review skipped |
| over-cap | real | PASS | ok | 0 | PASS | ok | 0 | matches | 1 | empty | commit files 4 lines 280 names a.py,b.py,c.py,d.py review skipped |
| tmp-unwritable | real | FAIL | worktree-failed | 1 | FAIL | runner-crash | 1 | FINDING | 1 | empty | repo tmp is mode 555 review None |
| two-builds | real | PASS | intact | 0 | PASS | intact | 0 | matches | 0 | empty | left 0 right 0 branches 2 fsck 0 overlap True left_reason ok right_reason ok |
