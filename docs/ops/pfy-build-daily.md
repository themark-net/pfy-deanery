# Daily command: `./pfy build`

Operator card for one headless build. Default is cloud Grok. Review is on. Nothing is pushed. The structural map is [pfy-build.md](../modules/pfy-build.md).

Daily command:

```bash
./pfy build "<task>"
```

A PASS leaves a branch whose name starts with `cloud/`, one commit, and a receipt. The caller's branch and `git status` stay as they were. The runner does not push and does not open a PR.

## What is not the daily command

`./pfy build --local "<task>"` is the opt-in fallback for when a cloud receipt says `rate-limit`. The flag `--local` is opt-in and not the default. MVP-2 and MVP-3 measured local as NO-GO for the default (cloud 6/6 in 583.6 s; local loop 5/6 gate, 4/6 human accept, 3859.9 s). Cloud numbers are in [eval/mvp2/REPORT.md](../../eval/mvp2/REPORT.md) and [HANDOFF-mvp2-trial.md](HANDOFF-mvp2-trial.md). The MVP-3 local loop wall time is 3859.9 s on `bot/mvp3-review-retry` (that report is not on this branch). A rate limit does not auto-start `--local`. Mark runs the fallback later, under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`, only when he chooses it.

`./pfy build -p "<prompt>"` stays the jev dogfood wrap (`scripts/pfy_build_p.py`, receipt.jsonl under `pipelines/dogfood/build/`). `-p` remains the jev dogfood wrap. Its exit codes and receipt path do not change. `./pfy build --prompt` and `./pfy build --prompt-file` stay on that same wrap. Any argv that contains `--local` stays on `scripts/pfy_build_local.py`.

## Dispatch

The runner is `scripts/pfy_build_cloud.py`. This card does not change `scripts/pfy`. The cloud lane owns that help text. After that dispatch lands, a task that is not `-p`, `--prompt`, `--prompt-file`, or `--local` runs `scripts/pfy_build_cloud.py`. On this branch, before that lands, a bare `./pfy build` still reaches the jev wrap.

The runner does not read `auth.json`. Grok uses the operator login that already exists outside the worktree. Auth failure is whatever grok prints, or a missing grok binary. Tests use a fake grok and do not stat the auth file.

## Flags

| Flag | Meaning |
|------|---------|
| `--repo DIR` | Git repo to build. Default is the repo that contains `./pfy`. The caller checkout is never the worktree. |
| `--base REF` | Base ref. Default `origin/main`. |
| `--test-cmd CMD` | Gate command. Default `python3 -m unittest discover -s tests -t .`. |
| `--retries N` | Extra attempts after the first. Default 2, so 3 attempts total. |
| `--no-review` | One attempt, no review call. Default is review on. |
| `--receipt-dir DIR` | Where to write the receipt. Default is under `pipelines/dogfood/build-cloud/<stamp>/`. |
| `--dry-run` | Plan only. Exit 0. No grok, no branch. |
| `--reap` | Clean a cloud run that died before it could write a receipt. Exit 0. |
| `--keep-worktree` | Leave `<repo>/tmp/cloud-build/<stamp>/` in place. Default removes it on PASS. |
| `--timeout SEC` | Bound the run. Exit 3 when it fires. |

## Exit codes

| Code | When |
|------|------|
| 0 | PASS, dry-run, or `--reap` |
| 1 | FAIL |
| 2 | usage |
| 3 | TIMEOUT |
| 4 | BLOCKED |

`--reap` exits 0 while the receipt `status` is `ABORTED`.

## What PASS looks like

Exit 0. Stdout has one summary line:

```text
PASS ok branch=cloud/<slug>-<stamp> receipt=<path>
```

`<path>` is `pipelines/dogfood/build-cloud/<stamp>/receipt.json` unless `--receipt-dir` overrides the directory. Schema is `pfy-cloud-build/1`. PASS fields: `status` `PASS`, `reason` `ok`, `branch` starting `cloud/`, `commit` (40 hex characters), `review.verdict` `accept`, `attempts` (at least one, last item `status` `PASS`), `gate`, `pushed` false. Also present: `schema`, `exit_code` 0, `base`, `review.reasons` (a list), `gate.cmd`, `gate.before`, `gate.after`, `recovery` (empty string on PASS), `worktree_removed` true unless `--keep-worktree`.

```json
{
  "schema": "pfy-cloud-build/1",
  "status": "PASS",
  "reason": "ok",
  "exit_code": 0,
  "branch": "cloud/<slug>-<stamp>",
  "commit": "<40 hex>",
  "base": "origin/main",
  "review": {"verdict": "accept", "reasons": []},
  "attempts": [{"status": "PASS"}],
  "gate": {"cmd": "python3 -m unittest discover -s tests -t .", "before": "<outcome before the edit>", "after": "<outcome after the edit>"},
  "recovery": "",
  "pushed": false,
  "worktree_removed": true
}
```

`git rev-parse <branch>` equals `commit`. That commit is not the caller's previous HEAD. The caller's branch name and `git status --porcelain` are unchanged. The runner does not stash, reset, or commit in the caller checkout. The commit tree contains only paths the review saw. Nothing was pushed.

## What dry-run looks like

`./pfy build "<task>" --dry-run` exits 0, starts no grok, writes no branch, and writes a receipt with `status` `DRY-RUN` and `commit` null.

## What usage looks like

`./pfy build` with no task exits 2 and prints the daily command, plus a pointer that `-p` remains the jev dogfood wrap and that `--local` is opt-in and not the default.

## What TIMEOUT looks like

Exit 3. No branch. Receipt `status` `TIMEOUT`, `reason` `timeout`. Rerun with a longer `--timeout`. No commit.

## Failures and recovery

The runner does not read `auth.json`. A rate limit does not auto-start `--local`.

| Case | Exit | Receipt | Recovery |
|------|------|---------|----------|
| `rate-limit` | 4 BLOCKED | `status` `BLOCKED`, `reason` `rate-limit`, no branch | `recovery` is the exact `./pfy build --local "<task>"` command. This run does not start it. A rate limit does not auto-start `--local`. |
| `unauthenticated` | 1 FAIL | `status` `FAIL`, `reason` `unauthenticated`, no branch | Run grok once to log in, then rerun the same `./pfy build`. The runner does not read `auth.json` and does not suggest `--local`. |
| gate red | 1 FAIL when retries are spent. The exit stays open while retries remain. | Attempt `reason` `tests`, `tests-flaky`, or `tests-tampered`. Final `status` `FAIL` when spent. No branch. Default `attempts` length is 3. | The next grok call gets the gate tail. When retries are spent, fix the task or the test command and rerun. The failed tree is not committed. |
| `review-rejected` | 1 FAIL when retries are spent. The exit stays open while retries remain. | Attempt `status` `PASS-REJECTED`, `reason` `review-rejected`, `review.verdict` `reject`. Final `status` `FAIL` when spent. No branch. | The next grok call gets the reject reasons and the previous diff. When retries are spent, rerun with a tighter task, or pass `--no-review` only when an unreviewed commit is acceptable. Review stays on by default. |
| `no-change` | 1 FAIL when retries are spent. The attempt counts while retries remain. | Attempt `reason` `no-change`. No branch. | The gate still runs. Feedback includes the gate tail, not only the word `no-change`. A green gate with an empty diff is still `no-change`. There is no empty PASS. |
| `scope-commit-mismatch` | 1 FAIL | `reason` `scope-commit-mismatch`. Index reset. No branch. | The commit set is the reviewed path list. `git add -A -f` is not the cloud commit. A staged name outside that list aborts the commit. |
| dirty caller | 0 when the new worktree base is clean. 1 when the base ref cannot be checked out (`reason` `worktree-failed`). | A PASS receipt names the new branch only. Dirty caller files are not in the new commit. | The runner never stashes or resets the caller. Dirty caller files stay dirty. |
| `interrupted` | 1 FAIL | `status` `FAIL`, `reason` `interrupted`. No branch. SIGINT or SIGTERM. | The grok process group is signaled. Rerun the same command when the task should run again. |
| `ABORTED` | `--reap` exits 0. The killed run wrote nothing. | `status` `ABORTED`, `reason` `no-receipt`, for a cloud pid-file entry whose receipt is missing. | After SIGKILL, run `./pfy build --reap`. Reap signals only pgids in `tmp/cloud-build.pids.json`. It does not signal pgids listed only in `tmp/local-build.pids.json`. |

## Receipt rules

Receipt text is redacted (token, bearer, AKIA, private-key blocks). A short fixture assignment such as `user_key=list-user` stays readable. An uppercase name such as `API_TOKEN`, a name that contains password or secret, and a value that mixes letters and digits are still replaced with `[redacted]`. A receipt that still contains those raw forms is a failed run. Do not paste a receipt that holds a live token into chat or into git. The demo copy that integration keeps is `eval/mvp-1031/demo-receipt.json` on the integrate branch, not a default receipt under `pipelines/dogfood/build-cloud/`.

Pid file: `<repo>/tmp/cloud-build.pids.json`. Worktree: `<repo>/tmp/cloud-build/<stamp>/`, removed on PASS unless `--keep-worktree`. Branch prefix: `cloud/`. The branch ref remains after the worktree is removed.

Default protect globs include `auth.json`, `.env`, `*.pem`, and `pipelines/dogfood/**/grok-home/**`. Protect means those paths are not committed. It does not mean the runner opens `auth.json`.

## Where this lives

| Piece | Path |
|-------|------|
| Cloud runner | `scripts/pfy_build_cloud.py` (not on this branch; cloud lane) |
| Dispatch and help | `scripts/pfy` (cloud lane owns the build help text) |
| Jev dogfood wrap | [scripts/pfy_build_p.py](../../scripts/pfy_build_p.py) |
| Local opt-in runner | [scripts/pfy_build_local.py](../../scripts/pfy_build_local.py) |
| Module map | [pfy-build.md](../modules/pfy-build.md) |

Cloud stays the daily path ([ADR-0002](../adr/0002-grok-cli-primary-interface.md), [ADR-0011](../adr/0011-hybrid-operator-surfaces-grok-opencode-ollama.md)). [ADR-0014](../adr/0014-pluggable-local-inference-spine.md) is the inference spine, not the build default. Surface split: [local-cloud-split.md](local-cloud-split.md).
