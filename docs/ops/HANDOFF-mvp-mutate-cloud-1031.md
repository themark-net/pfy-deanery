# Handoff: mvp-mutate-cloud-1031

Exit: lane empty. C1 through C16 are killed. The two baseline survivors (C4, C10) are killed by new behavior tests. No runner edit. Wall clock and host pressure did not fire. No question was asked. No merge, no PR, no tag.

Launch: 2026-10-31T21:15:42Z. Stop new items by 2026-11-01T04:55:42Z. Wall 2026-11-01T05:15:42Z. This handoff is inside the cap.

Branch: `bot/mvp-mutate-cloud-1031`. Base merged: `origin/bot/mvp-cloudfix-1031` `d35af20` (merge `0a76e22`). Still the cloudfix tip at 2026-10-31T21:43Z.

## Items done

| Item | SHA | Result |
|------|-----|--------|
| Merge cloudfix `d35af20` | 0a76e22 | anchors C1-C16 still apply |
| Mutation harness | d5540a4 | `tests.test_mut_cloud_harness`, 4 OK |
| Baseline round | results/before.json | 14 killed, C4 and C10 survived, on `9429aaf` |
| Killing tests | 6d41f73 | `tests.test_mut_cloud_survivors`, 2 OK on the runner |
| After round | results/after.json | 16 killed, 0 survived, on `38b26a1` |
| Report | this handoff commit | `eval/mutation-1031/cloud/REPORT.md` |

Doc commits that record SHAs: 9429aaf, 38b26a1, and this handoff commit.

## Skipped

- No change to `scripts/pfy_build_cloud.py` or `tests/test_pfy_build_cloud*.py`. The survivors did not need a runner change.
- `docs/TODO.md` and `docs/PENDING-HANDOFF.md`. Integration owns them. This lane's note is this file.
- Pregate not run: heavy lock busy. `flock -n ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` failed. Holder was `python3 -u -m unittest discover -s tests -t .` (pid 2516046) under flock pid 2294586. `pgrep -f 'Runner[.]Worker'` was empty at 2026-10-31T21:43Z, so the GitHub runner was idle, but the heavy lock was not.
- No ADR. No open question blocked a fit item. No secret was read. No local model.

## Test evidence

`nice -n 19 python3 -m unittest tests.test_mut_cloud_harness`

4 tests, OK, about 3.1s. Covers: each anchor applies once and parses, a value flip is killed, a comment edit survives, a hang is killed, a missed anchor is not survived, a clone outside `<source>/tmp` is refused, and `scripts/pfy_build_cloud.py` bytes do not change.

`nice -n 19 python3 -m unittest tests.test_mut_cloud_survivors`

2 tests, OK, about 0.2s, on the unmutated runner.

Proof on throwaway clones before that commit, with the new file copied in:

- C4: rc 1. The mutant printed `PASS ok` and the test required exit 1.
- C10: rc 1. `poll()` was `-15`, not `None`.

`nice -n 19 python3 eval/mutation-1031/cloud/run_mutants.py --baseline-only --label before`

14 killed, 2 survived. About 5 minutes.

`nice -n 19 python3 eval/mutation-1031/cloud/run_mutants.py --label after`

16 killed, 0 survived. Modules: `tests.test_pfy_build_cloud`, `tests.test_mut_cloud_survivors`. About 5 minutes.

Unmutated cloud suite, before the harness, in a throwaway clone: 44 tests, OK, 9.5s. After the cloudfix merge the mutant runs collected 48 tests in that module. Not a red base.

## How each change fails and recovers

- Harness: a clone dest outside `<source>/tmp` returns status `error` and does not create the dest. A missed anchor is `unapplicable`, not survived, and the command exits 2. A suite that exceeds 180s is killed and the clone's process group is stopped. Processes whose cwd is still that clone are signaled. The source runner hash is checked after every mutant.
- C4: a review reply with no `verdict:` line must not commit. The runner rejects it (`review.verdict` reject, reason `review-unparseable`, final reason `review-rejected`, exit 1, no branch). Recovery is the existing retry path: with retries left, the next prompt gets the reject reasons. This test uses `--retries 0`, so the run stops. If someone treats a missing verdict as accept, the test goes red because a `cloud/` branch appears and the exit is 0.
- C10: `./pfy build --reap` must not signal pgids that are listed only in `tmp/local-build.pids.json`. The local sleeper stays running (`poll()` is `None`) and the pid file bytes stay put. Recovery is to leave that process alone. The cloud pid file is still the only file reap reads. If reap signals the local group, `poll()` returns the signal and the test goes red. `kill(pid, 0)` is not the check, because a zombie still answers it.

## Cross-lane requests

None for mvp-cloudfix-1031. Both survivors are killed without a runner change.

mvp-integrate-1031: this branch is eval and tests only. It does not change the daily command. Merge it only if the mutation report should ride with the integrate branch. No Feature GO.

## Gate

Docs, eval, and test-only. Gate is pregate plus Reviewer. Pregate did not run (heavy lock busy). Do not request Reviewer until a pregate on this tip is PASS.

```bash
nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock ./scripts/pregate.sh
```

Run that only when `pgrep -f 'Runner[.]Worker'` is empty and the lock is free.

## Next step

Lane empty for owned files. When `origin/bot/mvp-cloudfix-1031` moves, merge it and re-run:

```bash
nice -n 19 python3 eval/mutation-1031/cloud/run_mutants.py --label after
```

If a row is `unapplicable`, update that anchor in `run_mutants.py` and re-run. If a row is `survived`, add a behavior test under `tests/test_mut_cloud_*.py`. Do not edit the runner from this lane.
