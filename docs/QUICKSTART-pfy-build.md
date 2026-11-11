# pfy build quickstart

One card for the daily command. Cloud Grok, review on, nothing pushed. The longer operator card is [pfy-build-daily.md](ops/pfy-build-daily.md). Line-by-line proof: MVP-DOD-WALKTHROUGH.md. Measured GO and the six PASS lines: VERDICT.md.

Commands below were run from this worktree at `2026-10-31T21:21:27Z`. A fence tagged `bash runnable exit=N` is re-run by `tests/test_quickstart_commands.py`. A `text` fence is the output from that run.

## Prerequisites

Grok is logged in once, on the operator account, outside this repo. This card does not open `auth.json`. bwrap is on the host for the local fallback sandbox.

From this checkout, `./pfy install` writes `deanery` and `pfy` (plus the transition alias `mentat`) into `$HOME/.local/bin`. Then `deanery` from any directory behaves like `./pfy`. Pass `--prefix` for another directory (for example `/opt/pfy-deanery/bin`). If the directory is not writable, the command prints a sudo line and does not run sudo. If it is not on PATH, add the printed line to `~/.bashrc` or `~/.profile` (for the default directory, `export PATH="$HOME/.local/bin:$PATH"`). Remove the launchers with `./pfy install --uninstall` or `./pfy uninstall --launchers`.

```bash
./pfy install
deanery help
```

```text
$ command -v grok
$HOME/.local/bin/grok
exit 0
$ timeout 15 grok --version
grok 1.0.70 (f50904eaee6c) [stable]
exit 0
$ command -v bwrap
/usr/bin/bwrap
exit 0
$ bwrap --version
bubblewrap 0.11.1
exit 0
```

## Daily command

```bash runnable exit=2
./pfy build
```

```text
Daily cloud build.

  ./pfy build "<task>"

-p is the jev dogfood wrap (./pfy build -p "<prompt>").
--local is the opt-in fallback (./pfy build --local "<task>").

usage: ./pfy build "<task>"
exit 2
```

The daily command is `./pfy build "<task>"`. That starts cloud Grok. This card does not run it. A missing task exits 2 and prints the lines above. An ordinary file under `tests/` may change with no flag. When a protected gate or eval file must change, add `--writable-test PATH` for that file. Deleting a base test is still `tests-tampered`.

```bash runnable exit=0
./pfy build --help
```

Help exits 0. Excerpt from this branch on 2026-11-01:

```text
usage: pfy build [-h] [--repo REPO] [--base BASE] [--test-cmd TEST_CMD]
                 [--retries RETRIES] [--no-review]
                 [--writable-test WRITABLE_TEST] [--receipt-dir RECEIPT_DIR]
                 [--dry-run] [--reap] [--keep-worktree] [--timeout TIMEOUT]
                 [--grok-cmd GROK_CMD]
                 [task ...]
exit 0
```

## Flags

| Flag | What it does |
|------|----------------|
| `--repo DIR` | Git repo to build. Default is the repo that contains `./pfy`. The caller checkout is never the worktree. |
| `--base REF` | Base ref. When HEAD matches `origin/main`, that is the default. When they differ, the run exits 2 until you pass `--base`. When `origin/main` is absent, the default is HEAD. |
| `--test-cmd CMD` | Gate. Default `python3 -m unittest discover -s tests -t .`. |
| `--writable-test PATH` | Protected gate or eval path the task may edit. Repeat the flag for each path. Ordinary files under `tests/` may change without it. Deleting a base test is still `tests-tampered`. |
| `--receipt-dir DIR` | Directory for `receipt.json`. Default `<repo>/pipelines/dogfood/build-cloud/<stamp>/`. |
| `--dry-run` | Write a receipt, start no grok, create no branch. Exit 0. |

Also on the help line: `--retries` (default 2 extra, 3 total), `--no-review`, `--reap`, `--keep-worktree`, `--timeout`.

Protected paths, which still need `--writable-test`, are the pregate gate-hash basenames (`conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `usercustomize.py`, `.gitignore`, `.gitattributes`, anywhere in the tree), plus `examples/eval-harness/`, `.github/workflows/`, `scripts/pregate.sh`, `scripts/pfy`, and `scripts/pfy_build_cloud.py`.

## Dry-run

```bash runnable exit=0
./pfy build "quickstart dry run" --dry-run --base HEAD --receipt-dir "$PWD/tmp/quickstart-dry-run"
```

On a branch whose HEAD is not `origin/main`, a dry-run without `--base` exits 2 and names `--base origin/main` or `--base HEAD`. The fence passes `--base HEAD`.

```text
DRY-RUN dry-run branch=none receipt=$HOME/DEVELOP/pfy-mentat/tmp/mvp-docs-final-1031/tmp/quickstart-dry-run/receipt.json
exit 0
```

Receipt fields from that file: `schema` `pfy-cloud-build/1`, `status` `DRY-RUN`, `reason` `dry-run`, `exit_code` 0, `branch` null, `commit` null, `base` `HEAD`, `pushed` false, `attempts` `[]`, `recovery` empty, `task` `quickstart dry run`. The receipt directory is under `tmp/`, which this repo gitignores.

## What PASS looks like

A PASS receipt has these fields:

```text
schema pfy-cloud-build/1
status PASS
reason ok
exit_code 0
branch cloud/make-add-return-the-sum-of-its-two-argum-20261031T210933627529Z
commit ebef4238a7eff8f938747623f7920b3fde74e586
base main
review {'verdict': 'accept', 'reasons': []}
attempts 1, last PASS ok
gate.cmd python3 -m unittest test_add
gate.before.exit 1
gate.after.exit 0
recovery ''
pushed False
worktree_removed True
```

```text
$ python3 tests/fixtures/mvp_receipt/check_receipt.py <receipt.json>
exit 0
```

The runner summary line on a PASS is `PASS ok branch=cloud/<slug>-<stamp> receipt=<path>`. The demo branch and commit are the fields above. `pushed` is false.

## Where receipts and branches go

| Piece | Path |
|-------|------|
| Default receipt | `<repo>/pipelines/dogfood/build-cloud/<stamp>/receipt.json` |
| Branch | `cloud/<slug>-<stamp>` in the `--repo` repo |
| Worktree | `/var/tmp/pfyb-<stamp>-<pid>` (mode 0700), removed when the run finishes unless `--keep-worktree` |
| Cloud pid file | `<repo>/tmp/cloud-build.pids.json` |

The caller branch name does not change. The `cloud/` ref remains after the worktree is removed. The worktree is not under the caller repo. When `$XDG_RUNTIME_DIR` is outside `/tmp` and `/run` and the harness2 socket still fits in 107 bytes, that directory is the parent. Otherwise `/var/tmp`, then `~/.cache`. `PFY_BUILD_WORKTREE_ROOT` replaces the search.

## How to land a cloud/ branch

The runner does not push. Proof used a throwaway repo whose `origin` was a local bare repo under `tmp/qs-land-bare` (not GitHub):

```text
$ git -C tmp/qs-land-repo rev-parse cloud/qs-land
734e18d10cb9f301f08be87829558317d4a073cb
exit 0
$ git -C tmp/qs-land-repo status --porcelain
exit 0
$ git -C tmp/qs-land-repo push origin cloud/qs-land
To $HOME/DEVELOP/pfy-mentat/tmp/mvp-docs-1031/tmp/qs-land-bare
 * [new branch]      cloud/qs-land -> cloud/qs-land
exit 0
$ git --git-dir=tmp/qs-land-bare rev-parse cloud/qs-land
734e18d10cb9f301f08be87829558317d4a073cb
exit 0
```

On a task repo, `rev-parse` the branch named in the receipt, then `git push origin` that same ref when you choose to publish it. The same two commands are what the throwaway ran.

## Failure exits and recovery

| Case | Exit | Receipt | Recovery |
|------|------|---------|----------|
| Cloud rate limit | 4 | `BLOCKED`, `reason` `rate-limit`, no branch | `recovery` is `./pfy build --local "<task>"`. This run does not start it. Run that later, under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`, only when you choose the fallback. |
| Auth failure or grok missing | 1 | `FAIL`, `reason` `unauthenticated`, no branch | Run grok once to log in, then rerun the same `./pfy build`. Recovery does not use `--local`. |
| Gate red, retries left | stays open | Attempt `FAIL`, `reason` `tests`, `tests-flaky`, or `tests-tampered` | The next grok call gets the gate tail. A later attempt may PASS. |
| Gate red, retries spent | 1 | `FAIL`, that gate reason, `attempts` length 3 by default, no branch | Fix the task or the test command and rerun. The failed tree is not committed. |
| Review reject, retries left | stays open | Attempt `PASS-REJECTED`, `reason` `review-rejected`, `review.verdict` `reject` | The next grok call gets the reject reasons and the previous diff. |
| Review reject, retries spent | 1 | `FAIL`, `reason` `review-rejected`, no branch | Rerun with a tighter task, or `--no-review` only when you accept an unreviewed commit. Default stays reviewed. |
| No-change | 1 when retries are spent | Attempt `reason` `no-change`, no branch | The gate still runs. Feedback includes the gate tail. A green gate with an empty diff is still `no-change`. |
| Scope vs commit mismatch | 1 | `reason` `scope-commit-mismatch`, index reset, no branch | The commit set is the reviewed path list. A staged name outside that list aborts the commit. |
| Dirty caller | 0 when the new worktree base is clean | PASS names the new branch only | Dirty caller files stay dirty and are not in the new commit. If the base ref cannot be checked out, exit 1, `reason` `worktree-failed`. |
| SIGINT or SIGTERM | 1 | `FAIL`, `reason` `interrupted`, no branch | The grok process group is signaled. Rerun the same command when the task should run again. |
| SIGKILL | next reap exits 0 | `ABORTED`, `reason` `no-receipt` | `./pfy build --reap` signals only pgids in `tmp/cloud-build.pids.json`. |
| Timeout | 3 | `TIMEOUT`, `reason` `timeout`, no branch | Rerun with a longer `--timeout`. No commit. |

A real rate-limit receipt has `recovery` `./pfy build --local rate-limit-sim`. That command was not run.

Reap on a throwaway repo with no pid file:

```text
$ ./pfy build --reap --repo tmp/qs-land-repo
reaped: none
exit 0
```

Receipt text is redacted (token, bearer, AKIA, private-key blocks). A receipt that still contains those raw forms is a failed run.

## When to use --local, and what -p is

Use `--local` only when a cloud receipt says `rate-limit`, and only under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`. Auth failure stays on the cloud command after you log in.

`-p` is the jev dogfood wrap (`scripts/pfy_build_p.py`). It is a different command from the daily build.

```bash runnable exit=0
./pfy build -p --help
```

```text
usage: pfy build [-h] [-p PROMPT] [--prompt-file PROMPT_FILE] [--cwd CWD]
                 [--dry-run]

Apply local jev toolset, shadow decision, run grok -p (plain).
exit 0
```

Dogfood receipts go under `pipelines/dogfood/build/<stamp>/receipt.jsonl`.
