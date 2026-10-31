# Handoff mvp-realfail3-1031

Lane empty. Nine real `./pfy build` cases ran on throwaway clones under this worktree's `tmp/`. The runner was not edited. Two cases are FINDINGs for mvp-cloudfix-1031. Seven match the failure table.

Branch: `bot/mvp-realfail3-1031`. Base: `origin/bot/mvp-integrate-1031` at `0c3f133`. Report: `eval/mvp-1031/realfail3/REPORT.md` (`Rows: complete`).

## Items done

| Item | SHA | Result |
|------|-----|--------|
| Exit card | `d213794` | Exits and expected rows committed before any build |
| Harness | `5a7ea04` | `drive.py`, gates, PATH shim, receipt test |
| tmp-unwritable | `2836356` | FINDING. `runner-crash` instead of `worktree-failed` |
| network-down | `40049ad` | MATCH. `FAIL` / `no-change` / exit 1. Shim text kept in the attempt tail |
| dirty-tree | `998d4af` | MATCH. PASS in 12s. Dirty porcelain kept. Commit is `app.py` only |
| detached-head | `19eafd3` | MATCH. PASS. HEAD stayed detached at the same SHA |
| no-tests | `3b1c126` | MATCH. `FAIL` / `tests` / exit 1. No branch |
| non-ascii | `ba55764` | MATCH. PASS. Receipt kept the non-ASCII task. Commit includes `my app.py` |
| over-cap | `0511b60` | MATCH. PASS with 4 files and 280 lines |
| two-builds | `91ce285` | MATCH. Both PASS, two `cloud/` branches, fsck 0, overlap true |
| gate-hang and handoff | `5ab61c2` | FINDING. `FAIL` / `tests` / exit 1. After-gate exit 124 |

Every probe used `--retries 0`, `--no-review`, and `--base HEAD` on a throwaway clone. No `--local`.

## Skipped

No listed case was skipped.

No further case was started. A real rate-limit run would spend the shared cloud budget on purpose, and a second PATH shim is outside the one shim this drop-in allows. Interrupt and SIGKILL were already recorded by realfail and realfail2.

Pregate not run: this drop-in says the operator runs `scripts/pregate.sh`. `Runner.Worker` was also active (`pgrep` saw `/home/mark/actions-runner/bin.2.338.0/Runner.Worker`), so the host was not idle.

`docs/TODO.md` and `docs/PENDING-HANDOFF.md` were not edited. Other lanes share them.

## Test evidence

`nice -n 19 python3 -m unittest tests.test_mvp_1031_realfail3_receipts`

6 tests, ok, after every case and again with `Rows: complete`. The test reads `REPORT.md` and each `receipt.json`. It rejects a status or reason mismatch, a MATCH row whose meta lists invariant problems, a FINDING without `FINDING.md` containing `Suggested fix`, a missing case when the report says complete, and secret-like text (AKIA, private key, bearer, `sk_` / `ghp_`, `xai-`).

## How this fails and how we recover

The checker fails if a committed row drifts from its receipt, or if a FINDING file drops the suggested fix. Recover by fixing that file and re-running the unittest. Throwaway clones stay under `tmp/realfail3-targets/` and are not committed.

Product failures, not fixed here:

- Unwritable `tmp/` (`mode 555`) raises `PermissionError` on `tmp/cloud-build` and the receipt says `runner-crash`. Caller HEAD and porcelain stayed unchanged, and grok was not called. Recover after the cloudfix: the same setup should exit 1 with `worktree-failed`.
- A gate that sleeps is killed at `--timeout` (after-gate exit 124, tail `gate timeout`) and stored as `tests` with exit 1 and an empty recovery. The before-gate had already passed, and the implement call had edited `app.py`. No branch. Recover after the cloudfix: exit 3, `TIMEOUT` / `timeout`, recovery telling the operator to rerun with a longer `--timeout`.

Observations that match the table, so they are not FINDINGs:

- Network shim (`Network is unreachable`) is `no-change` after a green gate. The attempt tail keeps the shim text.
- A repo with no `tests/` directory fails the default discover (`ImportError: Start directory is not importable: 'tests'`). The before-gate was already exit 1 and the runner still called grok. Final reason `tests`, no branch.
- Four files and 280 lines were committed. The cloud failure table has no size row. The local runner's 3-file / 250-line cap was not applied.
- Dirty files in the target stayed dirty and were not in the new commit. Detached HEAD stayed detached. Two overlapping builds both passed. A path with a space and a non-ASCII task both survived a PASS.

## Cross-lane requests

mvp-cloudfix-1031:

1. `eval/mvp-1031/realfail3/tmp-unwritable/FINDING.md`. Catch `OSError` in `prepare_worktree` and return `worktree-failed`.
2. `eval/mvp-1031/realfail3/gate-hang/FINDING.md`. A gate `timeout` from `run_command` should fail as `TIMEOUT` / `timeout` / exit 3, with recovery that mentions a longer `--timeout`.

Not requests: the over-cap PASS, the no-tests grok call after a red before-gate, and the network `no-change` reason. The counts and the before-gate exit are in the report notes if that lane wants them.

## Gate

Eval and test only. No runtime change. Gate: operator pregate, plus Reviewer. Tester plus Reviewer is not required for a runner change on this branch.

## Next step

mvp-cloudfix-1031 reads the two FINDING files and adds the behavior tests named there. This branch should merge as receipts and tests only, after the cloud runner branch.
