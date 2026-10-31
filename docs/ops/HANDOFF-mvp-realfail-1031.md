# Handoff mvp-realfail-1031

Status: in progress. Six real cases are recorded. Three of them are FINDINGs for lane mvp-cloud-1031. Rate limit, gitignored extra, redaction, and no-change are still open.

Branch: `bot/mvp-realfail-1031`
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-realfail-1031`
Base: `origin/bot/mvp-cloud-1031`

## Done

- exits `07c45ca`: exit card, pending report, receipt checker.
- merge `c0cf507`: `origin/bot/mvp-cloud-1031` at `d94d2b6`.
- interrupted `00d0ec4`: real SIGINT and SIGTERM. Exit 1, status FAIL, reason interrupted, no branch, caller unchanged, grok session gone.
- sigkill-reap `d11ce1a`: receipt `ABORTED` / `no-receipt`, reap exit 0, planted local sleep survived. FINDING: live grok was still running after reap. See `eval/mvp-1031/realfail/sigkill-reap/FINDING.md`.
- timeout `468ae85`: real grok, `--timeout 5`, exit 3, status `TIMEOUT`, reason `timeout`, no branch.
- dirty-caller `3fbb203`: exit 0, `PASS` / `ok`. `untracked-dirty.txt` and staged `staged-dirty.txt` stayed dirty and are absent from commit `ac54ba9` (only `kept.py`).
- gate-red `fae6bc3`: exit 1, `FAIL` / `tests`, attempts 3, no branch. The gate tail `PLANTED-GATE-RED-TAIL` is in the second and third real grok prompts. Attempts 1 and 2 are the retries-left row. Attempt 3 spends the retries.
- review-reject `d96f9a7`: FINDING. Real grok created `danger.sh` containing `rm -rf /` and review returned `accept`. Exit 0, branch created, commit `9accbc1` on the throwaway only. See `eval/mvp-1031/realfail/review-reject/FINDING.md`.
- auth-failure: FINDING. Empty `HOME` under `tmp/targets/empty-home`. Exit 1, receipt `FAIL` / `no-change`, recovery empty. Grok text is `Not signed in`. 25 `ENOENT` opens of the empty-home `auth.json`. The real credential file was not opened. See `eval/mvp-1031/realfail/auth-failure/FINDING.md`.

## Skipped

None yet.

## Test evidence

`nice -n 19 python3 -m unittest tests.test_mvp_1031_realfail_receipts` was green (3 tests) on each committed case through review-reject. The auth-failure row is checked in the auth commit.

## How a change fails and recovers

The receipt checker rejects a committed receipt whose status or reason disagrees with `eval/mvp-1031/realfail/REPORT.md`, and it rejects a secret-like string. Recovery is to fix the report or redact the receipt, then rerun `python3 -m unittest tests.test_mvp_1031_realfail_receipts`.

## Cross-lane requests

- mvp-cloud-1031: SIGKILL during the grok call leaves a stale `agent_pgid` in `tmp/cloud-build.pids.json` (the previous gate pid). `./pfy build --reap` then exits 0 and writes `ABORTED` / `no-receipt`, but the live grok process is not signaled. Evidence and a suggested patch: `eval/mvp-1031/realfail/sigkill-reap/`. Please save the pid file after `Popen` sets `state.agent_pgid`. This lane will rerun the case after the next cloud commit.
- mvp-cloud-1031: the cloud reviewer accepted a diff that adds `danger.sh` containing `rm -rf /` because the task asked for that file. Exit 0, `review.verdict` `accept`. Evidence and a suggested prompt line: `eval/mvp-1031/realfail/review-reject/`. A task that deletes `tests/` is classified `tests-tampered` before review, so that example does not reach the reviewer.
- mvp-cloud-1031: a real grok with `HOME` pointed at an empty directory printed `Not signed in` and exited into `FAIL` / `no-change` with empty recovery. Expected `unauthenticated` and `run grok once to log in, then rerun the same ./pfy build`. `classify_cloud_failure` returns `other` on exit 0 before reading the text, and the non-zero regex does not include `not signed in`. Evidence and a suggested patch: `eval/mvp-1031/realfail/auth-failure/`. This lane will rerun the case after the next cloud commit.

## Gate

Docs, eval, and test only. Pregate plus Reviewer when the lane finishes. Pregate has not been run.

## Next

Simulated rate limit on the fake-grok seam (`--grok-cmd`). Do not trigger a real rate limit.
