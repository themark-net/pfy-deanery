# Gom dogfood 2026-10-31

Six real `./pfy build` runs (cloud, no `--local`) against throwaway clones of `themark-net/gom-jabbar-grok4`. Branch under test: `bot/gom-dogfood-1031`. Caller branch: `bot/mvp-gom-dogfood-1031`. Each run used `--retries 1 --timeout 900 --keep-worktree` and an explicit `--test-cmd`. The red test was committed on the throwaway base before the build. Human accept is the lead reading the diff. Review accept is the second cloud call.

## Rows

| n | slug | exit | status | attempts | review | human | wall_s | commit |
|---|------|------|--------|----------|--------|--------|--------|--------|
| 01 | catch-view-thread | 0 | PASS | 1 | accept | accept | 122 | ddb8e75693394b05e2a18880d68a6e309b1bb573 |
| 02 | catch-view-meta | 0 | PASS | 1 | accept | accept | 101 | 86b67cae44e9a85eb7d3959040435fc78eddb919 |
| 03 | catch-view-index | 0 | PASS | 1 | accept | accept | 106 | 3960757fce438fe83adadafe0dc8ecba38160fba |
| 04 | catch-view-parties | 0 | PASS | 1 | accept | accept | 84 | 26a6d07230c962068491ce7ffa6b6ace14f3bcc3 |
| 05 | land-thread-provenance | 0 | PASS | 1 | accept | accept | 85 | 0c06365b9afbe7012f02cdd351d589e1c6502db6 |
| 06 | capture-list-thread | 0 | PASS | 1 | accept | accept | 141 | 7600d6cf88477251bd80b56dca59dd8ef82d49c5 |

`commit` is the cloud commit on the throwaway clone (`receipt.json` field `commit`). It is not the gom branch SHA. Landed SHAs are in each `meta.json` (`landed_fix`, `landed_test`).

## Rates

| measure | value |
|---------|--------|
| runs | 6 |
| PASS | 6 (100%) |
| FAIL, TIMEOUT, BLOCKED | 0 |
| review accept | 6/6 |
| human accept | 6/6 |
| attempts used | 1 on every run (retries armed, none spent) |
| wall sum | 639 s |
| wall mean | 106.5 s |
| cherry-picked to `bot/gom-dogfood-1031` | 6/6 |

Gate before was exit 1 on every run (the seeded red test). Gate after was exit 0. Gom tip after the sixth land: `3d9aac7b434e02d93ecab45a97457f5b2069dcb3`.

## What the runner did outside pfy-mentat

The review prompt does not name pfy-mentat. It accepted each gom diff. The implement prompt names the test command it was given. With an explicit pytest command, an explicit base, and a pre-seeded red test, all six runs passed on the first attempt.

These are the mismatches. Each one is a request for lane mvp-cloudfix-1031. This lane did not edit `scripts/pfy_build_cloud.py`.

1. New tests are tamper. `tests_tampered` treats any new or edited path under `tests/`, and any `test_*.py` or `*_test.py`, as a failed attempt. Gom cannot grow its suite inside the run. This lane committed the red test on the clone before `./pfy build` and told the model not to edit `tests/`. Request: let a task add a behavior test, or tell the gate to run a new test instead of rejecting the path.

2. The default gate is the wrong tool and the wrong interpreter. `DEFAULT_TEST_CMD` is `python3 -m unittest discover -s tests -t .`. On the gom worktree at 2026-10-31, that command exited 1: system Python 3.14, `ModuleNotFoundError: No module named 'structlog'`, and `No module named 'pytest'`, 35 errors. Gom tests are pytest (`tmp_path`) and the fresh worktree has no `.venv`. `uv run pytest -q` would sync over the network on every cloud worktree. This lane passed an absolute Python 3.12 venv and `pytest -q -p no:cacheprovider`. Request: do not score a missing interpreter as a product failure. If the repo has no venv, stop with a usage error that asks for `--test-cmd`. Do not assume `python3` can import the package.

3. The default base is the wrong commit when the clone's `origin/main` is not the branch under test. `resolve_base` uses `origin/main` when that ref exists, else HEAD. On clone `06-capture-list-thread`, `origin/main` was `2d26630915783ada9f6631fed125b6c1b566da6c` (the shared repo's local `main`) while HEAD was the bot branch that already held the earlier lands. A run without `--base` would have dropped those commits and the red test. Request: if `--repo` HEAD is not the resolved default base, refuse to start until `--base` is set.

4. The receipt redactor rewrites fixture names. `_SECRET_EQ` matches any identifier containing `TOKEN`, `KEY`, `SECRET`, `PASSWORD`, or `PASSWD`, then `=` or `:`. Pytest tails in these receipts show `user_key=[redacted]` and `token=[redacted]`. The values were fixture ids (`list-user`, `land-user`, `RAWTOKEN-only-in-source`), not credentials. Request: redact values that look like secrets. Do not rewrite every name that contains those substrings. The archived tail should still show the assertion.

5. The gate inherits the parent environment. `child_env` copies `os.environ` and sets `TMPDIR` to the cloud worktree `tmp/` plus `PYTHONDONTWRITEBYTECODE=1`. A foreign test can read whatever the operator shell exported. This lane's receipts were scanned and have no `AKIA`, `BEGIN PRIVATE KEY`, `sk_`, or `ghp_` markers. The tests also pop `GROK_API_KEY`, `XAI_API_KEY`, and `GMX_IMAP_*` inside the subprocess. Request: start the gate from a scrubbed environment (PATH, TMPDIR, and the variables the test command sets itself).

`--test-cmd` is split with `shlex` and run as argv, not a shell. A prefix of `env NAME=value command` works, and that is how `JOURNAL_DB_PATH` was forced onto a scratch db. Gom's default db path is a relative `gomjobbar_journal.db`. The real journal under `~/DEVELOP/jobbar-master/current` was not opened (mtime `1790360353`, size `1744896` after every land).

`.pytest_cache` is already ignored by `files_changed`. This lane still passed `-p no:cacheprovider` so the gate would not write a cache. That is not a runner bug.

## Checker

`tests/test_gom_dogfood_1031_report.py` reads this table and compares each row to `receipt.json` (`exit_code`, `status`, `len(attempts)`, `review.verdict`, `commit`) and `meta.json` (`human_verdict`, `wall_s`). A planted exit or attempt count that disagrees with the receipt fails the check. A missing row fails the check.

## Wave 5

Six more cloud runs after `origin/bot/mvp-integrate-1031` was merged (`d6d62db`). No `--local`. The red test was still committed on the throwaway base before `./pfy build`, because an edit to that seeded file is still `tests_tampered`. Rows below use the same columns. `commit` is still the cloud commit.

| n | slug | exit | status | attempts | review | human | wall_s | commit |
|---|------|------|--------|----------|--------|--------|--------|--------|
| 07 | catch-view-to | 0 | PASS | 1 | accept | accept | 112 | 57e15700113ea1949526cb97a16f1f9a74db141a |
| 08 | catch-view-cc | 0 | PASS | 1 | accept | accept | 102 | b2b1981c78666b0d7d55828545cc13feea3a11a4 |

