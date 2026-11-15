# Module: pfy build (`scripts/pfy_build_cloud.py`)

**Purpose:** Daily headless build. `./pfy build "<task>"` runs cloud Grok, review on, nothing pushed. Operator card: [pfy-build-daily.md](../ops/pfy-build-daily.md). Measured verdict: GO for that daily command (2026-10-31).

**Not this module:** `./pfy build -p` (jev dogfood wrap) and `./pfy build --local` (opt-in local runner).

## Human operator

Daily command:

```bash
./pfy build "<task>"
```

Default is cloud Grok. Review is on. Nothing is pushed. A PASS leaves a branch starting `cloud/`, one commit, and `pipelines/dogfood/build-cloud/<stamp>/receipt.json`.

`./pfy build --local "<task>"` is the opt-in fallback for when a cloud receipt says `rate-limit`. The flag `--local` is opt-in and not the default. MVP-2 and MVP-3 measured local as NO-GO for the default (cloud 6/6 in 583.6 s; local loop 5/6 gate, 4/6 human accept, 3859.9 s). Cloud numbers are in a private ops note and a private ops note. The MVP-3 local loop wall time is 3859.9 s (a private ops note). A rate limit does not auto-start `--local`.

`./pfy build -p "<prompt>"` stays the jev dogfood wrap (`scripts/pfy_build_p.py`, receipt.jsonl under `pipelines/dogfood/build/`). `-p` remains the jev dogfood wrap.

The runner does not read `auth.json`.

### Flags

| Flag | Meaning |
|------|---------|
| `--repo DIR` | Repo to build. Default is the repo that contains `./pfy`. The caller checkout is never the worktree. |
| `--base REF` | Base ref. When HEAD matches `origin/main`, that is the default. When they differ, the run exits 2 until you pass `--base origin/main` or `--base HEAD`. When `origin/main` is absent, the default is HEAD. |
| `--test-cmd CMD` | Gate. Default `python3 -m unittest discover -s tests -t .`. |
| `--retries N` | Extra attempts. Default 2 (3 total). |
| `--no-review` | One attempt, no review. Default is review on. |
| `--writable-test PATH` | Protected gate or eval path the task may edit. Repeat the flag for each path. Ordinary files under `tests/` may change without it. Deleting a base test is still `tests-tampered`. |
| `--receipt-dir DIR` | Receipt directory. Default `pipelines/dogfood/build-cloud/<stamp>/`. |
| `--dry-run` | Exit 0. No grok, no branch. Receipt `status` `DRY-RUN`, `commit` null. |
| `--reap` | Exit 0. Receipt `status` `ABORTED` when the killed run wrote nothing. |
| `--keep-worktree` | Keep the short worktree (mode 0700). Default removes it when the run finishes. |
| `--timeout SEC` | Exit 3 on expiry. |
| `--review-file-cap N` | Max characters of one file's diff in review. Default 12000. Same knob as `PFY_REVIEW_FILE_CAP`. The flag wins when both are set. |
| `--review-workers N` | Parallel review workers. Default 4, or `PFY_REVIEW_WORKERS`. Clamped to 1..8. The flag wins. |
| `--review-timeout SEC` | Seconds for one review call. Default 600, or `PFY_REVIEW_TIMEOUT`. The flag wins. A short budget cuts that review before the implement timeout. |
| `--yes` | Accept the printed cloud estimate. Off a TTY this is required unless `--approve-cost` or a covering `--max-cost` is set. `PFY_BUILD_YES=1` is the same approval. |
| `--approve-cost` | Same as `--yes`. |
| `--max-cost USD` | Refuse when the estimate is above this cap. A cap at or above the estimate is itself approval. |
| `--agentlint` | Optional local AgentLint scan of the attempt diff. Off by default. `PFY_AGENTLINT=1` is the same switch. |

A safe `.gitignore` line for generated output, and a `pyproject.toml` edit that does not change a test table, are allowed without a flag. Gate-weakening edits still need `--writable-test`. A `tests-tampered` failure names that flag and the path. Protected paths are the pregate gate-hash basenames (`conftest.py`, `pytest.ini`, `tox.ini`, `setup.cfg`, `pyproject.toml`, `sitecustomize.py`, `usercustomize.py`, `.gitignore`, `.gitattributes`, anywhere in the tree), plus `examples/eval-harness/`, `.github/workflows/`, `scripts/pregate.sh`, `scripts/pfy`, and `scripts/pfy_build_cloud.py`.

### Exit codes

| Code | When |
|------|------|
| 0 | PASS, dry-run, or `--reap` |
| 1 | FAIL |
| 2 | usage |
| 3 | TIMEOUT |
| 4 | BLOCKED |

`--reap` exits 0 while the receipt `status` is `ABORTED`.

`./pfy build` with no task exits 2 and prints the daily command, plus a pointer that `-p` remains the jev dogfood wrap and that `--local` is opt-in and not the default.

### Cost confirmation

Before Grok starts, stderr shows `model choice:`, `why:`, the cloud range (`cost estimate:`), a wall-time range, and the local alternative at $0 (`qwen3.6:35b` via Ollama). Recent receipts under `pipelines/dogfood/build-cloud/` supply the dollar history and `wall_seconds` when they exist. `PFY_COST_HISTORY_ROOT` overrides that search. With no history the token price table is used. If that quote is $0, one implement call uses the static floor $0.20-$0.36 and a longer round (more than one model call) uses $1.50-$6. Cloud wall with no history is 10-20 minutes per attempt. Local wall with no history is 20-65 minutes, plus the clean-clone flake-gate re-runs when those are on.

The cloud dollar quote counts packed review prompts (small files share one prompt; chunks that do not fit run together), not one call per file. `--local` is $0. Its receipt `estimate` still records `review_prompts` and `flake_runs` so the cloud alternative includes those packed reviews, and the local wall includes the flake-gate re-runs. Cloud does not quote extra flake-gate spend: its same-tree flake gate overlaps the post-change gate.

On a TTY the question is `Proceed? [y/N]`. Off a TTY the run exits 2 unless `--yes`, `--approve-cost`, or `PFY_BUILD_YES=1`, or `--max-cost` is at least the estimate. A lower cap exits 2 even with `--yes`. Receipt `reason` is `estimate-declined` and `actual.source` is `not-run`. No model was called. `--local` prints $0 and does not ask. `--dry-run` prints the same choice and does not ask. `./pfy build -p` uses the same rule before `grok -p`. `./pfy compare` never starts a paid run on its own: `--yes` still needs `--max-usd` or `--max-cost`, and a covering cap is enough by itself.

The receipt stores `choice`, `estimate` (including `alternative`, `review_prompts`, and `flake_runs`), and `actual` (`usage.json` after a cloud spend, `local` after `--local`).

Local flake-gate re-runs and `--size` presets are documented in [pfy-build-flake-size.md](pfy-build-flake-size.md), not here.

### What PASS looks like

Exit 0. Stdout:

```text
PASS ok branch=cloud/<slug>-<stamp> receipt=<path>
```

Schema `pfy-cloud-build/1`. PASS fields: `status` `PASS`, `reason` `ok`, `branch` starting `cloud/`, `commit`, `review.verdict` `accept`, `attempts`, `gate`, `pushed` false. Also `exit_code` 0, `base`, `review.reasons`, `gate.cmd`, `gate.before`, `gate.after`, `recovery` empty, `worktree_removed` true unless `--keep-worktree`. Caller branch and `git status --porcelain` stay unchanged. Nothing is pushed.

Exit 3 is TIMEOUT: receipt `status` `TIMEOUT`, `reason` `timeout`, no branch. Rerun with a longer `--timeout`.

### Failures and recovery

The runner does not read `auth.json`. A rate limit does not auto-start `--local`. When `recovery` is not empty, that same line is printed on stderr. Printing it does not start the command.

| Case | Exit | Receipt | Recovery |
|------|------|---------|----------|
| `rate-limit` | 4 BLOCKED | `status` `BLOCKED`, `reason` `rate-limit`, no branch | `recovery` is the exact `./pfy build --local "<task>"` command. This run does not start it. A rate limit does not auto-start `--local`. |
| `unauthenticated` | 1 FAIL | `status` `FAIL`, `reason` `unauthenticated`, no branch | Run grok once to log in, then rerun the same `./pfy build`. The runner does not read `auth.json` and does not suggest `--local`. |
| gate red | 1 FAIL when retries are spent. The exit stays open while retries remain. | Attempt `reason` `tests`, `tests-flaky`, or `tests-tampered`. Final `status` `FAIL` when spent. No branch. | The next grok call gets the gate tail. When retries are spent, fix the task or the test command and rerun. The failed tree is not committed. |
| `gate-missing` | 2 usage | The gate binary was not found. No grok call. | Pass `--test-cmd` with a command that exists. The default is `python3 -m unittest discover -s tests -t .`. |
| `gate-unusable` | 2 usage | The default unittest command failed with an import error before any edit. No grok call. | Pass `--test-cmd` with an interpreter that can import this repo. A custom gate that fails an assertion still retries. |
| `review-rejected` | 1 FAIL when retries are spent. The exit stays open while retries remain. | Attempt `status` `PASS-REJECTED`, `reason` `review-rejected`, `review.verdict` `reject`. Final `status` `FAIL` when spent. No branch. | The next grok call gets the reject reasons and the previous diff. When retries are spent, rerun with a tighter task, or pass `--no-review` only when an unreviewed commit is acceptable. One rejected file rejects the whole build. |
| `review-file-too-large` | 1 FAIL. No retry. | `reason` `review-file-too-large`, `phase` `precheck`. No review call. No branch. The post-change gate does not start. | The named file is over the per-file cap. Split that file and rerun `./pfy build`. |
| `no-change` | 1 FAIL when retries are spent. The attempt counts while retries remain. | Attempt `reason` `no-change`. No branch. | The gate still runs. Feedback includes the gate tail. A green gate with an empty diff is still `no-change`. |
| `scope-commit-mismatch` | 1 FAIL | `reason` `scope-commit-mismatch`. Index reset. No branch. | The commit set is the reviewed path list. `git add -A -f` is not the cloud commit. A staged name outside that list aborts the commit. |
| dirty caller | 0 when the new worktree base is clean. 1 when the base ref cannot be checked out (`reason` `worktree-failed`). | A PASS receipt names the new branch only. Dirty caller files are not in the new commit. | The runner never stashes or resets the caller. Dirty caller files stay dirty. |
| `estimate-declined` | 2 usage | `status` `FAIL`, `reason` `estimate-declined`, no branch | Rerun with `--yes`, `--approve-cost`, or a higher `--max-cost`. No model was called. |
| `interrupted` | 1 FAIL | `status` `FAIL`, `reason` `interrupted`. No branch. | The grok process group is signaled. Rerun the same command when the task should run again. |
| `ABORTED` | `--reap` exits 0. The killed run wrote nothing. | `status` `ABORTED`, `reason` `no-receipt`. | After SIGKILL, run `./pfy build --reap`. Reap signals only pgids in `tmp/cloud-build.pids.json`. It does not signal pgids listed only in `tmp/local-build.pids.json`. |
| `agentlint-blocked` | 1 FAIL when retries are spent. The attempt counts while retries remain. | `reason` `agentlint-blocked`. No branch. | An AgentLint error blocked a changed file. Remove that change and rerun `./pfy build`. A missing binary prints `agentlint-fallback` and the build continues. Warnings do not fail the build. |

## Agent

- Entry: `scripts/pfy_build_cloud.py`, reached from `scripts/pfy` `cmd_build` when the argv is not `-p`, `--prompt`, `--prompt-file`, or `--local`. The cloud lane owns that dispatch. This module doc does not edit `scripts/pfy`.
- `-p` entry: [scripts/pfy_build_p.py](../../scripts/pfy_build_p.py). Receipt `pipelines/dogfood/build/<stamp>/receipt.jsonl`. Do not change that contract.
- `--local` entry: [scripts/pfy_build_local.py](../../scripts/pfy_build_local.py). Branch prefix stays `local/`. Not the default.
- Invariants: review on unless `--no-review`; small files share one review prompt and chunks that do not fit run together (default 4 workers, cap 8); a reject must cite a concrete defect, and a whole-task complaint with no defect is not a reject; any concrete reject rejects the build; a review that stops or exits non-zero is not an accept, so an unread file is not published; a file over the per-file cap is split and every part is reviewed; the reviewer sees every line of a file it accepts (no truncated diff); `impact.source` is `codebase-memory-mcp`, `tree-sitter-analyzer`, or `git-grep`; a missing impact tool does not fail the build; the gate drops `GIT_CONFIG_COUNT` and `GIT_CONFIG_KEY_*` / `GIT_CONFIG_VALUE_*` together so a scrubbed key name does not leave git unable to parse its command-line config; `pushed` false; no read of `auth.json`; a `rate-limit` receipt does not start `--local`; commit set is the reviewed path list (`scope-commit-mismatch` on a mismatch); caller checkout is never the worktree; the worktree is `/var/tmp/pfyb-<stamp>-<pid>` or another short 0700 directory outside `/tmp` and `/run` (`PFY_BUILD_WORKTREE_ROOT` replaces the search), removed unless `--keep-worktree`; pid file `tmp/cloud-build.pids.json` only.
- Invariants: review on unless `--no-review`; review is one file at a time and any reject rejects the build; a review that stops before the last file is a reject, so an unread file is not published; a file over the per-file cap fails as `review-file-too-large` with `phase` `precheck` before the post-change gate; the reviewer sees every line of a file it accepts (no truncated diff); `impact.source` is `codebase-memory-mcp`, `tree-sitter-analyzer`, or `git-grep`; a missing impact tool does not fail the build; the gate drops `GIT_CONFIG_COUNT` and `GIT_CONFIG_KEY_*` / `GIT_CONFIG_VALUE_*` together so a scrubbed key name does not leave git unable to parse its command-line config; `pushed` false; no read of `auth.json`; a `rate-limit` receipt does not start `--local`; commit set is the reviewed path list (`scope-commit-mismatch` on a mismatch); caller checkout is never the worktree; the worktree is `/var/tmp/pfyb-<stamp>-<pid>` or another short 0700 directory outside `/tmp` and `/run` (`PFY_BUILD_WORKTREE_ROOT` replaces the search), removed unless `--keep-worktree`; pid file `tmp/cloud-build.pids.json` only. `--agentlint` (or `PFY_AGENTLINT=1`) scans changed text with local AgentLint 2.12.0 after the protected-path check. Off by default. Errors fail as `agentlint-blocked`. Warnings do not. A missing binary prints `agentlint-fallback` and the build continues. The child has AgentChute forced off. Shell commands are outside this scan. Trial table: [eval/agentlint-trial/README.md](../../eval/agentlint-trial/README.md).
- Schema: `pfy-cloud-build/1` at `pipelines/dogfood/build-cloud/<stamp>/receipt.json`.
- ADR: [ADR-0002](../adr/0002-grok-cli-primary-interface.md) and [ADR-0011](../adr/0011-hybrid-operator-surfaces-grok-opencode-ollama.md) keep Grok as the daily path. [ADR-0014](../adr/0014-pluggable-local-inference-spine.md) is the inference spine, not the build default. Ops split: [local-cloud-split.md](../ops/local-cloud-split.md).
- Do not: edit `docs/modules/README.md` from a docs lane (integration adds the row); link `scripts/pfy_build_cloud.py` (keep it inline code); auto-start a local model; push from the runner; open a PR from the runner.

## Architecture link

Operator-stack daily build, cloud side of [local-cloud-split.md](../ops/local-cloud-split.md). The measured reason local is not the default is MVP-2 cloud 6/6 in 583.6 s and MVP-3 local loop 5/6 gate, 4/6 human accept, 3859.9 s. Cloud-default `./pfy build` on the 2026-10-31 integration tip is GO (VERDICT.md).
