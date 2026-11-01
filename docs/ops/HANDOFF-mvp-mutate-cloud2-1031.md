# Handoff: mvp-mutate-cloud2-1031

Exit: lane empty. C17 through C43 are killed. The eight baseline survivors are killed by new behavior tests. No runner edit. Wall clock and host pressure did not fire. No question was asked. No merge, no PR, no tag.

Launch: 2026-10-31T23:39:33Z. Stop new items by 2026-11-01T07:19:33Z. Wall 2026-11-01T07:39:33Z. This handoff is inside the cap.

Branch: `bot/mvp-mutate-cloud2-1031`. Base: `origin/bot/mvp-cloudfix-1031`. Required merges, never rebase: `origin/bot/mvp-integrate-1031` `f877c7d` (merge `9763263`). `origin/bot/mvp-dogfood-fix-1031` `1fa9fd3` was already an ancestor of that tip.

Runner sha256 on both mutation rounds: `f2dd898417eafaf99a70562a36ca0f31e3db7a8112af936b4359d757a05e5c00`. The harness recorded `origin/bot/mvp-cloudfix-1031` as `80470185e9bfccadef83ae19401344e8dcd0d945` at those runs.

## Items done

| Item | SHA | Result |
|------|-----|--------|
| Exit card | 71b4705 | loop exits written before the merges |
| Merge integrate | 9763263 | clean ort merge; dogfood-fix already inside `f877c7d` |
| Record the merges | e053b1e | docs only |
| Reuse the harness | 03bce4f | copied from mutate-cloud `9f707fd`; C1-C16 still apply; that branch was not merged |
| Catalog C17-C43 | 1dd23ee | 27 mutants, each anchor once; cloud suite 61 OK in 24.938s |
| Kill tests, first cut | 7ded452 | eight behavior tests; the bracket-filename case did not kill C21 |
| Kill C21 | dd0c34e | a file named `*` plus a root `extra.pyc` |
| Score and report | f8487a6 | before 19 killed, 8 survived; after 27 killed, 0 survived |

## Skipped

- `scripts/pfy_build_cloud.py` and `tests/test_pfy_build_cloud*.py`. The survivors did not need a runner change.
- `tests/test_mut_cloud_*.py` after the copy. Wave-3 owns those files. New tests are `tests/test_mut_cloud2_*.py`.
- C1-C16 were not re-run. Wave-3 scored them 16 killed, 0 survived on the older runner (sha256 `d4f28f2e...`). This lane does not rescore them.
- A further mutant round on classify, reap, or dry-run. Those sites are the wave-3 score. The drop-in sites for this lane are covered.
- `docs/TODO.md` and `docs/PENDING-HANDOFF.md`. Other lanes write them.
- No findings file. No mutant showed a runner bug.
- No ADR. No open question blocked a fit item. No secret was read. No local model. `scripts/pregate.sh` was not run during the loop.
- Pregate not run: host busy. At 2026-11-01T00:37:04Z `pgrep -f 'Runner[.]Worker'` was empty, and `flock -n ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` failed. Holders included `./scripts/pregate.sh` on `1f3b1a3` (pid 252212) and on `1dee0b9` (flock pid 333069), `python3 -m unittest discover -s tests -t .` (flock pid 318463), and `python3 tmp/perf-measure/run.py` (flock pid 274382). This lane did not wait and did not signal them.

## Test evidence

Unmutated cloud suite, before the catalog run: `tests.test_pfy_build_cloud`, 61 tests, OK, 24.938s. Not a red base.

`nice -n 19 python3 -m unittest tests.test_mut_cloud2_harness tests.test_mut_cloud2_survivors tests.test_mut_cloud_harness tests.test_mut_cloud_survivors`

17 tests, OK, 13.385s, at `dd0c34e`, checked again at 2026-11-01T00:34Z.

`nice -n 19 python3 eval/mutation-1031/cloud/run_mutants.py --baseline-only --label before --timeout 180` for C17-C43.

19 killed, 8 survived. 516.8s. HEAD `1dd23ee`. `eval/mutation-1031/cloud/results/before.json`. The detail text in that file is noisy (`FAIL: commit-recheck-failed` from a passing recovery test). Status is the exit code.

`nice -n 19 python3 eval/mutation-1031/cloud/run_mutants.py --label after --timeout 180` for C17-C43.

27 killed, 0 survived, 0 unapplicable, 0 error. 708.7s. Finished 2026-11-01T00:30:19Z. HEAD `dd0c34e`. Modules: `tests.test_pfy_build_cloud`, `tests.test_mut_cloud_survivors`, `tests.test_mut_cloud2_survivors`. `eval/mutation-1031/cloud/results/after.json`.

A first after run against `7ded452` was 26 killed and 1 survived (C21). That is not the score. `dd0c34e` is the score.

Full table, the applied edit for each mutant, and the re-run command: `eval/mutation-1031/cloud/REPORT.md`.

## How each change fails and recovers

The harness applies one mutant to a clone under this worktree's `tmp/`. A clone dest outside that tree is an error. A missed anchor is `unapplicable`, not survived, and the command exits 2. A suite that exceeds 180s is killed. The source runner hash is checked after every mutant. `first_detail` prefers the unittest failure line over the runner's own `FAIL: <reason>` line.

The 19 mutants that died on the baseline fail in `tests.test_pfy_build_cloud`. The killing test for each id is the After column in the report. Recovery is the current runner behavior those tests already lock: allow-list, literal pathspec, archive recheck with retry, protected paths, redaction, a recovery line on stderr, missing-base as worktree-failed, and a timeout that kills the child group.

The eight new tests in `tests/test_mut_cloud2_survivors.py`:

- C19: `--writable-test tests/test_ed*.py` commits the edit to `tests/test_edit.py` and leaves `tests/test_keep.py` as it was. Exit 0, receipt PASS. If the glob is compared as literal text, the run exits 1 with tests-tampered and no commit.
- C21: grok writes `*` and a root `extra.pyc`. Literal staging commits only the star file. Glob staging also stages the pyc, the scope check rejects the commit, and the receipt is not PASS.
- C23: gates 1 to 3 pass and gate 4 sleeps. `--timeout 1 --no-review` exits 3, reason timeout, recovery contains `the gate timed out`, and no `cloud/` branch exists. If that recheck timeout is treated as a pass, a branch is created.
- C27: `nested/auth.json` plus `kept.py` exits 1, reason `protected-path-changed`, recovery names the path, and no branch is kept. If the basename match is off, the nested file is committed. A nested pem is not the check: Python `fnmatch` lets `*` match `/`.
- C30: a private-key body `MIIB-CLOUD2-SECRET` must be absent from the receipt. The receipt contains `[redacted-private-key]` and does not contain `BEGIN PRIVATE KEY`. `kept.py` still lands. If the PEM block pass is skipped, the body stays in the receipt.
- C39: the review argv (`PFY-CLOUD-REVIEW`) sleeps and the implement call does not. `--retries 0 --timeout 1` exits 3, reason timeout, and no branch. If the timeout is stored as review-rejected, the exit is 1.
- C40: the first gate sleeps. Exit 3, recovery contains `the gate timed out`, and the grok side marker is absent. If the before-gate timeout is ignored, the marker exists.
- C41: `--timeout 0` exits 2 with `--timeout must be > 0`. Grok is not started and no receipt is written. If zero is accepted, grok starts.

## Cross-lane requests

None for mvp-cloudfix-1031. No runner bug.

mvp-integrate-1031: this branch is eval and tests only. It does not change the daily command. Merge it only if the mutation report should ride with the integrate branch. No Feature GO.

`docs/TODO.md`: this lane did not add a row. The score lives in `eval/mutation-1031/cloud/REPORT.md`. A TODO pointer, if one is wanted, belongs to the lane that owns that file.

## Gate

Docs, eval, and test-only. Gate is pregate plus Reviewer. Tester plus Reviewer is not the gate: the runner did not change.

Pregate not run: host busy. Do not request Reviewer until a pregate on this tip is PASS.

```bash
nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock ./scripts/pregate.sh
```

Run that only when `pgrep -f 'Runner[.]Worker'` is empty and the lock is free.

## Next step

Lane empty for owned files. When `origin/bot/mvp-cloudfix-1031` moves, merge it (never rebase) and re-run:

```bash
nice -n 19 python3 eval/mutation-1031/cloud/run_mutants.py --label after --timeout 180
```

Pass `--mutant C17` through `C43` to score only this wave. If a row is `unapplicable`, update that anchor in `run_mutants.py` and re-run. If a row is `survived`, add a behavior test under `tests/test_mut_cloud2_*.py`. Do not edit the runner from this lane. Do not renumber C1-C16.
