# Handoff: mvp-realfail2-1031

Exit: lane empty. The listed re-checks and the new DoD rows are in `eval/mvp-1031/realfail2/REPORT.md`. Fourteen rows match. One FINDING is a cross-lane request. Wall clock and host pressure did not fire. No question was asked. No merge, no PR, no tag.

Launch: 2026-10-31T21:23:08Z. This handoff is inside the wall cap (stop new items by 2026-11-01T05:03:08Z, wall 2026-11-01T05:23:08Z).

Branch `bot/mvp-realfail2-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-realfail2-1031`. Base `origin/bot/mvp-cloudfix-1031`, contained at `d35af20`. This lane did not edit the runner.

## Items done

| Item | SHA | Result |
|------|-----|--------|
| Loop card and receipt harness | a480afa | PASS, 4 tests OK, report still pending |
| usage | 34d8c98 | matches. Exit 2, no receipt, daily command and both pointers |
| dry-run | 2f14df0 | matches. Exit 0, DRY-RUN, shim grok_calls 0, no branch |
| worktree-failed | c592c8d | FINDING. Missing base exits 2 as usage. Caller unchanged |
| sigkill-reap | 43d20c3 | matches. Fixed. Reap killed the live grok and left the planted sleeper |
| review-reject | 3092ebc | matches. Fixed. Real reviewer rejected the planted root delete. No branch |
| auth-failure | 8302665 | matches. Fixed. unauthenticated. Recovery names grok login. No credential file read |
| redaction | 3d38e3d | matches. Fixed. Marker absent from task and output_tail |
| review-retry-accept | 0a853fd | matches. Attempt 1 reject, attempt 2 accept. kept.py committed |
| scope-commit-mismatch | f351af8 | matches. Exit 1, index reset, no branch |
| protected-paths | 95b3405 | matches. Exit 1, protected-path-changed, neither file committed |
| keep-worktree | 178ed26 | matches. worktree_removed false, directory still present |
| worktree-default | 68d982a | matches. worktree_removed true, directory gone |
| dogfood-p | de4ecef | matches. Help exit 0. Real -p wrote hello.txt. grok-home removed |
| concurrent | f8b2a19 | matches. Two distinct cloud branches, fsck 0, caller unchanged |
| review-cap | a202e74 | matches. Four files accepted on attempt 1. Recovery not needed |

Doc commits that record those SHAs: eb0ffc4, 1d68312, 3c82d61, acadab4, 1bdec80, e8003b7, 84f1ff9, d60dce9, f0a1b81, 34b8607, 6fd66d8, 9a57f0a, 334b6a3, 8edff42, 521b910, d47be58. Cloudfix merges: 87b2693, 81044bc. Later fetches were already up to date.

## Skipped

- Pregate not run: host busy. `pgrep -f 'Runner[.]Worker'` matched pid 2631906 at 2026-10-31T21:50:42Z.
- Failure-table rows mvp-realfail-1031 already matched: interrupted-sigint, interrupted-sigterm, timeout, dirty-caller, gate-red, rate-limit, gitignored-extra, no-change. Not re-run.
- Round 2 (`mvp-dedupe-1031`, `mvp-sandbox-gate-1031`, `mvp-daily-card-1031`) owns other files. `mvp-local-t5-1031` needs a local model. This drop-in says needs a local model: no.
- No ADR. No open question blocked a fit item. No secret was read. `~/.grok/auth.json` was not opened by this lane.

## Test evidence

`nice -n 19 python3 -m unittest tests.test_mvp_1031_realfail2_receipts`

4 tests, OK, under 0.01s, after every filled row, including the review-cap commit. Scratch for the planted bad receipt is `tmp/realfail2-receipt-tests` (gitignored).

Real grok was used where the original finding was real, and for every new row except dry-run (PATH shim) and usage (no task, so no grok). `--local` was never passed. Throwaway clones stayed under this worktree's `tmp/targets/`.

`dogfood-p` rewrote the existing `~/.grok/skills/pfy-jev-decision/SKILL.md` and the jev brief under `~/.pfy-mentat` (idempotent toolset apply). The isolated grok-home on the clone, including the auth byte copy, was deleted before commit. No auth bytes were printed or committed. `restored_paths` is empty.

`review-retry-accept`: the wrapper did not plant. The task text contains "previous attempt was rejected", so the plant skipped. The model wrote `danger.sh` itself, the real reviewer rejected it, then the model wrote `kept.py` and the reviewer accepted it. The row still matches.

## How each change fails and recovers

This lane added evidence and one receipt test. It did not change runner behavior.

The test fails when a receipt status drifts from the report, a secret-like string appears in a case dir, or a matches row's meta contradicts the DoD (live grok after reap, leaked marker, dirty caller, committed protected path, missing kept worktree, damaged concurrent repo, four-file cap block without a usable recovery note). Recover by fixing the runner in mvp-cloudfix-1031, or by correcting the row to FINDING with notes. Do not strip a real mismatch to force a green test.

Observed product behavior, for the reviewer:

- sigkill-reap: reap signals the recorded grok pgid and leaves a pid that is only in the local pid file. A live grok after reap is the old bug.
- review-reject: a diff that adds `rm -rf /` is rejected. Retries 0, exit 1, no branch. The wrapper planted the file only after real grok returned, and only inside the clone worktree.
- auth-failure: empty HOME, `Not signed in`, exit 1, reason unauthenticated, recovery tells the operator to run grok once. Strace saw 25 ENOENT opens and zero successful opens.
- redaction: the planted `xai-` marker is absent from `task` and `output_tail`. The receipt contains `[redacted]`. The build still PASSed.
- review-retry-accept: reject with a retry left continues; the next accept commits `kept.py` and not `danger.sh`.
- scope-commit-mismatch: a staged `tmp/` path outside the reviewed set resets the index, exit 1, no branch.
- worktree-failed: see the cross-lane request. Caller HEAD and status stayed unchanged, so the safety property held. The exit code and reason did not.
- dry-run: exit 0, no grok call, no branch, receipt DRY-RUN.
- usage: exit 2, no receipt, text has the daily command and the `-p` and `--local` pointers.
- dogfood-p: `-p --help` exits 0 and names the prompt flag. A real `-p` run with `--cwd` on the clone writes `hello.txt`.
- keep vs default: `--keep-worktree` sets `worktree_removed` false and leaves the directory. The default sets it true and removes the directory.
- protected-paths: `auth.json` and `.env` are absent from every commit. Reason `protected-path-changed`. Recovery on that receipt is empty. The drop-in asked for a recorded reason, which is present, so this row matches.
- concurrent: two `--no-review` builds on one clone. Allowed outcomes are distinct branches, a clean refusal, or a mixed intact result. This run took distinct branches. `git fsck` exit 0. Caller unchanged.
- review-cap: there is no numeric file cap in the runner. The real reviewer accepted four files on attempt 1. Recovery was not needed. A block would have been a FINDING with `recovery_usable` set.

## Cross-lane requests

- mvp-cloudfix-1031: a `--base` ref that does not exist should be exit 1, reason `worktree-failed`, with the caller unchanged. Observed: exit 2, stderr `base ref not found: does-not-exist-realfail2-1031`, no receipt, caller unchanged. Receipt: `eval/mvp-1031/realfail2/worktree-failed/`. This lane did not patch the runner.
- mvp-cloudfix-1031, observation, not a FINDING: `protected-path-changed` records the reason and commits nothing. `recovery` is an empty string and does not name the paths.
- mvp-integrate-1031: this branch is eval, docs, and one test. The four original FINDINGs are fixed on the contained cloudfix runner. Do not treat this handoff as a Feature GO. Do not merge it to main from this lane.

## Gate

Pregate plus Reviewer. Docs, eval, and test only. No runtime edit in this lane.

Pregate not run: host busy.

## Next step

Stop this lane. Cloudfix can change a missing base from usage exit 2 to exit 1, reason `worktree-failed`. Integrate can take this report when it collects wave 3. Do not merge to main from here.
