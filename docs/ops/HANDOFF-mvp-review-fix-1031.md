# Handoff: local review-loop holes (mvp-review-fix-1031)

Branch `bot/mvp-review-fix-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-review-fix-1031`. Base `origin/bot/mvp3-review-retry`. No PR. Mark merges after Tester plus Reviewer. This run does not merge.

`./pfy build --local` is still opt-in. Review stays on unless `--no-review`. `--retries` default stays 2. Exit codes are unchanged (0 PASS, 1 FAIL, 2 usage, 3 TIMEOUT, 4 BLOCKED). `eval/mvp3/REPORT.md` was not edited. The six MVP-3 tasks were not re-run. No Ollama process was started.

## Items done

| Item | SHA | Tests |
|------|-----|-------|
| Exit card before code | `122e207` | docs only |
| Scope vs commit | `7bdede7` (log `2873a90`) | both modules, Ran 70 in 91.800s, OK |
| No-change gate | `88ebcae` (log `9f85a6a`) | both modules, Ran 72 in 95.741s, OK |

Command, both times, with `TMPDIR` under this worktree's `tmp/`:

```text
nice -n 19 python3 -m unittest tests.test_pfy_build_local tests.test_pfy_build_local_review
```

## What changed

Scope vs commit (`scripts/pfy_build_local.py`): the commit stages only the reviewed names, with `:(literal)` pathspecs. The old excludes for `tmp`, bytecode, and pytest cache stay on both sides of the compare. After `git add`, `git diff --cached --name-only` must match that set. A mismatch runs `git reset --mixed`, sets `reason` to `scope-commit-mismatch`, exits 1, and creates no branch.

No-change: an empty diff runs the post-attempt gate once. `reason` is `no-change` even when that gate is green. The gate tail is in the next prompt. The review model is not called. Spent retries exit 1 with no `local/` branch.

## How this fails and how we recover

| Risk | How it fails | Recovery |
|------|--------------|----------|
| Gitignored receipt next to a real fix | The receipt is not in `git status`, so it is not reviewed and not staged. The commit blob does not contain it. | The reviewed file still commits when the archive recheck passes. Origin HEAD is unchanged. |
| Fix imports a gitignored helper the review never saw | The archive recheck cannot import the helper | `git reset --hard HEAD~1` before the branch exists. `reason` `commit-recheck-failed`. No `local/` branch. |
| Index gains a name the review did not see | Staged set differs from the reviewed set | Index reset. `reason` `scope-commit-mismatch`. Exit 1. No branch. |
| Agent writes nothing | Empty diff is not a PASS, even if the gate is green | Gate runs once. Next prompt contains the gate tail. Spent retries exit 1, `reason` `no-change`, no branch. |
| Review model on an empty diff | There is nothing to accept | The model is not called. |

## Skipped

- Round 2 sandbox gate (`--unsafe-no-sandbox` must not leave the gate unsandboxed when bwrap works). The plan launches `mvp-sandbox-gate-1031` only after `origin/bot/mvp-integrate-1031`. That ref does not exist. Doing it here would copy a scheduled lane.
- G1, G2, G3, G6, G7, G8, G9: other lanes, and the files are forbidden here.
- G10: the plan excludes it from round 1.
- Official `./scripts/pregate.sh`: not run. `pgrep -f 'Runner[.]Worker'` was empty at 2026-10-31T20:10:53Z, but the heavy lock was held by another lane's pregate (pid 1441386, `./scripts/pregate.sh`), with two more pregates waiting. pregate not run: host busy. The script would also add a worktree under `~/DEVELOP/pfy-mentat/tmp/pg/`.

## Cross-lane

- `mvp-cloud-1031`: do not copy `git add -A -f` of the whole tree. Stage the reviewed names and compare. On no-change, run the gate and put the tail in the retry. A green gate plus an empty diff is `no-change`. This branch has that behavior at `88ebcae`.
- `mvp-sandbox-gate-1031`: still open. This lane did not touch the unsandboxed-gate gap.
- Integrate: merge this branch after `origin/bot/mvp3-review-retry`. Do not edit `eval/mvp3/REPORT.md` while merging.

## Gate

Runtime change in `scripts/pfy_build_local.py`. Needs Tester plus Reviewer at the handoff SHA. Official pregate was not run (host busy). The two owned modules are green (72 tests). No Feature GO.

## Next

Gate this branch. The cloud lane copies the two rules without the old bugs. Sandbox-gate waits until integrate exists.
