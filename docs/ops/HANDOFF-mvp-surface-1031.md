# Handoff: mvp-surface-1031

Branch `bot/mvp-surface-1031`. Base `origin/main` `85c53dc`. Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-surface-1031`. Not a Feature GO. No PR. Do not merge to main. Catalog HOLD was not touched.

Compare: https://github.com/themark-net/pfy-mentat/compare/main...bot/mvp-surface-1031

Decisions: `docs/ops/AUTONOMOUS-DECISIONS-mvp-surface-1031.md`. Run log: `docs/ops/RUN-LOG-mvp-surface-1031.md`.

## Items done

| Item | SHA | What |
|------|-----|------|
| Loop exits before the card | `a2302df` | Exit card and phase plan in the run log. |
| Operator card | `c73ef00` | `docs/ops/pfy-build-daily.md` and `docs/modules/pfy-build.md`. Same daily command, exit codes, schema, and failure recoveries. |
| Contract test | `b56285e` | `tests/test_pfy_build_docs.py`. Reads both docs. Does not start a build. |

Head after the handoff commit is the SHA of that commit. A commit cannot record its own SHA.

## Items skipped

| Item | Why |
|------|-----|
| Round 2 `mvp-daily-card-1031` (append the integrate demo to `docs/ops/pfy-build-daily.md`) | `origin/bot/mvp-integrate-1031` does not exist (`git fetch` returned no remote ref). The plan says to append the real demo and not invent a green transcript. |
| README row for `pfy-build.md` | `docs/modules/README.md` is forbidden on this lane. Backlog edits it. Integration adds the row. |
| `scripts/pfy` help text | Cloud lane owns that dispatch. This card does not change it. |
| Local model, full discover, eval | This lane needs no local model. Targeted unittest only, until pregate. |

Lane empty after those skips. No third skip in a row that was an attempted item. Exit: lane empty, with the DoD met.

## Test evidence

`nice -n 19 python3 -m unittest tests.test_pfy_build_docs -v`

5 tests, OK, about 0.001 s, at `b56285e` (2026-10-31T19:58:31Z). Host then: MemAvailable about 62 GiB, load under 3, 32 cores.

The suite fails if either card drops `./pfy build`, an exit row (0 PASS, 1 FAIL, 2 usage, 3 TIMEOUT, 4 BLOCKED), schema `pfy-cloud-build/1`, the sentence that `--local` is opt-in and not the default, the sentence that `-p` remains the jev dogfood wrap, or a failure name (`rate-limit`, `unauthenticated`, `review-rejected`, `no-change`, `scope-commit-mismatch`, `interrupted`, `ABORTED`, plus gate red and dirty caller). It also fails if a recovery sentence is missing, if `scripts/pfy_build_cloud.py` is a markdown link, or if any relative link target is not a file in this repo. A synthetic missing target is rejected. An `https://` link is ignored.

A one-off check, not committed: stripping the TIMEOUT row makes that exit regex miss, and a relative link to `scripts/pfy_build_cloud.py` is reported missing.

## How this fails and how to recover

The cards are the contract. If a reader cannot see a PASS or a named failure, `tests.test_pfy_build_docs` goes red. Put the sentence or the table row back. If a relative link dangles, the same test goes red. Mention `scripts/pfy_build_cloud.py` as inline code until that file is on the branch, or link a file that exists.

Product recoveries live in the card, not in this lane's code. A cloud `rate-limit` stays exit 4 and does not start `--local`. `unauthenticated` tells the operator to log in with grok. The runner does not read `auth.json`. Gate red and `review-rejected` retry, then exit 1 with no branch. `no-change` is not a PASS. `scope-commit-mismatch` resets the index. A dirty caller is left dirty. `interrupted` signals the grok process group. After SIGKILL, `./pfy build --reap` exits 0 and the receipt `status` is `ABORTED`.

## Cross-lane requests

- Integration: add one row in `docs/modules/README.md` for `docs/modules/pfy-build.md` after the backlog merge. Do not do it on this branch.
- Cloud lane (`bot/mvp-cloud-1031`): wire `scripts/pfy` so a bare `./pfy build "<task>"` runs `scripts/pfy_build_cloud.py`, and keep `-p` on `scripts/pfy_build_p.py`. This card already describes that contract.
- Round 2 `mvp-daily-card-1031`: after `origin/bot/mvp-integrate-1031` has a pushed handoff, append the real demo command, exit code, branch, and receipt path to `docs/ops/pfy-build-daily.md`. If the demo did not PASS, write that. Do not invent a green transcript.

## Gate

Docs and one test. No runtime change. Gate is pregate plus Reviewer. Tester is not required for this lane.

Pregate ran once on `b56285e` (the card and the test, before this handoff commit). Runner was idle. The run waited on `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` because other lanes were already in pregate. Command: `nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock ./scripts/pregate.sh`. Wall 1067 s after the lock. Summary: `/home/mark/DEVELOP/pfy-mentat/tmp/pregate-runs/b56285e-20261031T202132Z-1625691/pregate-summary.md`.

OVERALL=FAIL. pass=4 fail=2 skip=1.

| Check | Result |
|-------|--------|
| lint | PASS |
| ci-parity | PASS |
| gate-hash | PASS (73 protected paths; no committed gate-file change vs `origin/main`) |
| ubuntu-parity | FAIL. 953 tests, 1 failure, 100 skipped, 435.944 s |
| eval-structural | FAIL. Same unittest failure inside `pfylib_unittests` (953 tests, 617.255 s, 16 skipped). Other structural checks PASS |
| suite | SKIP |
| orphans | PASS |

Both fails are `tests.test_pfylib_tmp_cleanup.PfylibTmpCleanupTests.test_module_run_leaves_no_new_tmp_dirs`. The new `/tmp` names were `pfy-xintake-122-receipts-m961lhe3`, `pfy-xintake-140-receipts-reprmzla`, `pfy-xintake-146-receipts-gez8edcw`, `pfy-xintake-143-receipts-cax56yib`, `pfy-xintake-128-receipts-mgecizmt`, `pfy-xintake-137-receipts-zafyna3h`, and `pfy-xintake-131-receipts-34fs5enc`. This lane does not use `/tmp` and does not edit that test. A neighboring pregate on `0fbf426` reported ubuntu-parity OK (956 tests, 100 skipped) a few minutes earlier. Not rerun. This lane's contract test is not the failure.

This handoff commit is docs only, after `b56285e`. Reviewer gates the card and `tests/test_pfy_build_docs.py` at `b56285e`, plus this handoff.

## Next step

Merge this branch in the plan's order (after review-fix, preflight, and before eval and cloud), then run the integrate demo. Do not make `--local` the default.
