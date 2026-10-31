# Handoff: mvp-eval-1031

Branch `bot/mvp-eval-1031`. Base `origin/main` `85c53dc`. Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-eval-1031`. Not a Feature GO. No PR. Do not merge to main. No local model. No grok. `scripts/pfy_build_cloud.py` was not implemented.

Run log: `docs/ops/RUN-LOG-mvp-eval-1031.md`. Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-eval-1031.md`.

Exit: lane empty after the definition of done. Wall cap was 2026-11-01T03:56:27Z. Host stayed above 16 GiB free and load stayed near 3 on 32 cores.

## Items done

| Item | SHA | What landed |
|------|-----|-------------|
| exits | `75a5f7782f21f69fe96fa91076ac570674453646` | Exit card and phase plan before any fixture code |
| fixture | `837107604d5003a5465b2c89618a6f93a651c523` | `eval/mvp-1031/fixture/add.py` returns 0. `test_add.py` expects `add(2, 3) == 5` |
| init | `4ebb99ec92a9d8ffa9b2a7068a386ba6b3707a58` | `eval/mvp-1031/init_fixture.sh` seeds one `main` commit under the caller's `tmp/` |
| checker | `f742dbf9830d9c68c51e63a394617df0541ce2eb` | `eval/mvp-1031/check_receipt.py` accepts only a drop-in PASS receipt |
| readme | `4a76204b1886009e8e5c4be6cc7356ecd2229d46` | Demo command, inline paths, no markdown link to the plan file |

Log commits that only record those SHAs: `95670cf`, `b262813`, `8b92c67`, `3445e29`, `99ad762`.

## Skipped

- Round 2 `eval/mvp-1031/rerun_local.py` and `eval/mvp-1031/local-rerun/`. Owner is mvp-local-t5-1031. That lane needs a local model. This lane must not call one.
- `eval/mvp-1031/demo-receipt.json` and `eval/mvp-1031/REPORT.md`. Integration writes those after a real `./pfy build`.
- G10 overnight leftovers (T-0070 scorer, T-0081 docker cage, T-0074 model run, and the rest listed in the plan). The plan excludes them from round 1.
- No ADR. The checker does not change architecture.
- pregate not run: host busy. Runner.Worker was not running. The heavy lock was already held by other `scripts/pregate.sh` processes.

## Test evidence

Command: `nice -n 19 python3 -m unittest tests.test_mvp_1031_receipt`

Result: 12 tests, OK. No network. Scratch under `tmp/mvp-eval-1031` with `TMPDIR` set there.

Manual proof before the fixture commit, in a temp dir under that scratch: shipped `test_add` exit 1 (`AssertionError: 0 != 5`); after `return a + b`, exit 0.

`tests.test_mvp_1031_receipt` covers:

1. Shipped fixture fails. A copy of `test_add.py` with `add` returning `a + b` passes.
2. `init_fixture.sh` on a temp dest exits 0, `HEAD` is `main`, one commit, and `python3 -m unittest test_add` in that repo exits non-zero.
3. A hand-built PASS receipt exits 0, with empty stdout and stderr.
4. Reject: null commit, branch `local/x`, `review.verdict` `reject`, `pushed` true, empty `attempts`, schema `pfy-local-build/1`. Each exits 1 with one stderr line.
5. Reject: PASS-shaped JSON whose text contains `AKIA` plus 16 letters `a`, a `BEGIN PRIVATE KEY` line, or `sk_` plus eight letters `b`. Samples are fake. Stderr does not echo the sample.
6. `strace -f -e trace=file` of the checker on a PASS receipt does not mention `auth.json` or `.grok/`. The checker does not open `~/.grok/auth.json`.

Also covered, same module: usage exits 2 and writes nothing; a dest outside the caller's `tmp/` is not created; a pre-existing non-empty dest is not deleted; a symlink dest is refused; an existing empty dest is initialized in place. The README contains the three demo commands and has no markdown link to `MVP-PARALLEL-1031.md`.

## How it fails and how it recovers

- Fixture: if `add` already returned the sum, the demo would start green. Recovery: the tree returns 0, so `add(2, 3)` is not 5. The same test file passes once `add` returns `a + b`.
- Init: a dest outside `tmp/`, a symlink, or a non-empty directory would write or delete the wrong tree. Recovery: exit 1, leave that tree unchanged, and remove a dest this invocation created if a later step fails. Usage (no dest, or two dests) exits 2. An empty directory is initialized in place.
- Checker: a null commit, a `local/` branch, a reject verdict, `pushed` true, empty attempts, or the wrong schema would look like a cloud PASS. Recovery: exit 1 and one stderr reason. `exit_code` must be a JSON integer 0, `pushed` must be JSON false, and `commit` must be 40 lowercase hex characters. Extra keys are ignored, so a cloud receipt that also has `review.reasons` or `gate.before` still passes when the drop-in fields match.
- Secrets: a PASS-shaped file whose raw text contains `AKIA`, `BEGIN PRIVATE KEY`, or `sk_` plus 8 characters is rejected before it can be treated as success. The stderr line names the marker class and does not print the matched text.
- README: a markdown link to `docs/plans/MVP-PARALLEL-1031.md` would 404 on this branch. Recovery: the demo command is inline.

## Cross-lane requests

None. No file outside this lane's owned set was changed.

## Gate

Docs, eval, and tests only. No product runtime change under `scripts/` or `pfylib/`. Gate: pregate plus Reviewer. Pregate was not run (host busy), so there is no `pregate-summary.md` to attach. Reviewer should expect a gate-hash NOTE for the new `tests/test_mvp_1031_receipt.py`. Tester is not required for a product runtime change.

## Next step

Integration, after `scripts/pfy_build_cloud.py` is on the integrate branch, runs the command in `eval/mvp-1031/README.md` and then `python3 eval/mvp-1031/check_receipt.py` on the receipt. A PASS from that demo is integration's result, not this lane's. When the heavy lock is free, run `./scripts/pregate.sh` once on this branch's HEAD and attach that summary to the Reviewer request.
