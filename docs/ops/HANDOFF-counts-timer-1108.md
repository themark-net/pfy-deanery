# Handoff: counts timer off Mark's checkout (2026-11-08)

Lane `bot/loopbuild-counts-1108`. Not pushed. This lane does not build the catalog loop. The next lane can call `scripts/loop_worktree.sh`.

## What broke

The installed user unit ran in Mark's checkout. That tree does not have `scripts/catalog_counts.py`. Journal from the 04:17 PT run on 2026-11-08:

```
2026-11-08T04:17:00-08:00 nimo systemd[4895]: Starting catalog-counts.service - Regenerate catalog counts from stage cards...
2026-11-08T04:17:00-08:00 nimo python3[877858]: /usr/bin/python3: can't open file '/home/mark/DEVELOP/pfy-mentat/scripts/catalog_counts.py': [Errno 2] No such file or directory
2026-11-08T04:17:00-08:00 nimo systemd[4895]: catalog-counts.service: Main process exited, code=exited, status=2/INVALIDARGUMENT
2026-11-08T04:17:00-08:00 nimo systemd[4895]: catalog-counts.service: Failed with result 'exit-code'.
2026-11-08T04:17:00-08:00 nimo systemd[4895]: Failed to start catalog-counts.service - Regenerate catalog counts from stage cards.
```

Exit 2. Nothing was written.

## The fix

`ops/systemd/catalog-counts.service` keeps `Type=oneshot` and `Nice=10`. `WorkingDirectory` is `%h`, not the checkout. `ops/systemd/catalog-counts.timer` is unchanged: `OnCalendar=*-*-* 04:17:00`, `Persistent=true`.

`ExecStart` does not run a script out of the checkout. It sets `GIT_DIR` to `%h/DEVELOP/pfy-mentat/.git`, fetches `origin`, and writes `origin/main:scripts/loop_worktree.sh` to `%t/pfy-loop-worktree.sh`. Then it execs that copy with `scripts/catalog_counts_publish.sh`. `GIT_TERMINAL_PROMPT=0` is set on those git commands. Fetch and show update remote refs and read a blob. They do not checkout, reset, or clean the checkout.

`scripts/loop_worktree.sh [--wt DIR] -- <command...>` prepares a detached worktree and runs the command there.

- `DIR` defaults to `${PFY_LOOP_WT:-$HOME/DEVELOP/pfy-mentat/tmp/loop/wt}` (under gitignored `tmp/`).
- The repo defaults to `${PFY_LOOP_REPO:-$HOME/DEVELOP/pfy-mentat}`. Only `git fetch` and `git worktree add` touch it. The script never checkouts, resets, stashes, or cleans that working tree.
- If `DIR` is missing, it creates the parent, takes the lock, fetches, and runs `git worktree add --detach DIR origin/main`.
- It then fetches, `git reset --hard origin/main`, and `git clean -qfdx -e tmp/` inside the worktree. Files under that worktree's `tmp/` stay.
- Exit 2 if `DIR` resolves to the repo top-level, or if `DIR` exists and is not a worktree of that repo.
- The lock is `DIR/../loop-worktree.lock` (`flock -n`). A busy lock exits 75 and does not run the command. The lock stays held until the command exits.

`scripts/catalog_counts_publish.sh` runs `python3 scripts/catalog_counts.py` in that worktree. It also refuses (exit 2) if its own top-level is `PFY_LOOP_REPO`, so a direct run cannot commit from the checkout.

- No output change: print `unchanged`, exit 0.
- Any path other than the three outputs below: print the paths, commit nothing, exit 3.
- `PFY_LOOP_NO_PUSH=1`: print the three paths (or `unchanged`), commit nothing, exit 0. A stray path is still exit 3.
- Otherwise commit `catalog: regenerate counts` as author and committer `catalog-loop <catalog-loop@localhost>`, then fast-forward `refs/heads/main`.
- The push tries at most 3 times: `git fetch origin`, `git merge-base --is-ancestor origin/main HEAD`, `git push origin HEAD:refs/heads/main`. If `origin/main` is not an ancestor, it rebases only that counts commit and retries. A rebase conflict aborts and exits 1. Nothing is forced. `GIT_TERMINAL_PROMPT=0` is set for the whole publish script, including push.
- If `catalog_counts.py` exits non-zero, publish exits with that status and does not commit, even if the tree is dirty.

Allowed paths:

- `data/stages/_registry.json`
- `pipelines/catalog/dashboard.latest.md`
- `pipelines/catalog/counts.latest.json`

## Install (operator, after this commit is on origin/main)

This lane did not install the unit and did not start the timer. `git show` reads the script from `origin/main`, so install after the driver has pushed.

```bash
cp ops/systemd/catalog-counts.* ~/.config/systemd/user/ && systemctl --user daemon-reload && systemctl --user start catalog-counts.service
```

The 2026-11-07 install already enabled `catalog-counts.timer`. The timer file did not change. `daemon-reload` picks up the new service. `start` runs it once. The next 04:17 run uses the new `ExecStart`.

## Five questions

1. What triggers it? `catalog-counts.timer` at 04:17 America/Los_Angeles, `Persistent=true`, and a manual `systemctl --user start catalog-counts.service`.
2. What does it do, and which services does it read and write? It reads `origin/main` and the stage cards (through `scripts/catalog_counts.py` in the loop worktree). It writes the three generated files and, when those are the only changes, a fast-forward of `refs/heads/main`. It does not write the checkout. No hosted service. No model. `PFY_LOOP_NO_PUSH=1` does not commit.
3. What does it trigger next? Nothing. `Type=oneshot`. This lane does not start the catalog loop. Later readers use the three files on main.
4. Where does a human re-enter? `journalctl --user -u catalog-counts.service`. Exit 2 means the worktree path is the repo top-level or not a worktree of the repo. Exit 3 means a path outside the three outputs changed, and nothing was committed. Exit 75 means the lock was busy and the command did not run. If the push is still not a fast-forward after 3 tries, the run exits nonzero and does not force. Install only after this commit is on `origin/main`.
5. What stops two runs doing the same work? One `flock -n` on the worktree lock. The second run exits 75 and does not run. The push is fast-forward only. A rejected push rebases the one counts commit and retries at most 3 times. No `--force`. The counts script still prints `unchanged` and skips a commit when the three files already match.

## Catalog-first

Read `docs/eval/TOOLSET-RANKING.md`, `docs/ops/INTEGRATE.md`, `docs/ops/integration-stages.md`, the 2026-11-07 counts, queue, and verdicts handoffs, `docs/ops/HANDOFF-integrate2-1108.md`, and `uses` / `features` on the stage cards before writing code.

- `docs/eval/TOOLSET-RANKING.md` does not publish counts or own this timer. neatroots is rank 7 for offline trace checks. That is a different job.
- ATG (`data/stages/atomic-task-graph-atg.json`, I2) compiles and repairs a DAG. Its non-goals include a pipeline dependency. Not used.
- neatroots (I2) checks saved traces for loops and error streaks. This timer has no trace. Not used.
- headson (I2) previews JSON for a local-model prompt. This lane calls no model. Not used.
- Sponsio (I2) orders agent tool calls. Its non-goals include a pregate or CI gate. Fetch-then-show is two git commands. Not used.
- Brigade (I0) is a file ledger with an exclusive claim so two actors do not take the same item. The card says not to wire a gate. This lane keeps the exclusive-claim idea and uses `flock`, which is already on nimo. Brigade is not vendored and not started.
- `scripts/integrate_lane.sh` already lands with fetch, an ancestor check, a fast-forward push, a rebase, and 3 tries, and it does not force. Publish uses that rule. It does not call the integrate driver. That driver grills, runs Grok, and writes `tmp/integrate/` markers.
- `scripts/catalog_counts.py` is unchanged.

No new stage card. These scripts are not a cataloged tool moving to I3.

## Files

- `scripts/loop_worktree.sh`
- `scripts/catalog_counts_publish.sh`
- `ops/systemd/catalog-counts.service`
- `tests/test_loop_worktree_lock.py`
- `tests/test_loop_worktree_mkdir.py`
- `tests/test_loop_worktree_behavior.py`
- `tests/test_catalog_counts_unit_bootstrap.py`
- `tests/test_catalog_counts_unit_kept.py`
- `tests/test_catalog_counts_push_rebase.py`
- `tests/test_catalog_counts_publish_failure.py`
- `tests/test_catalog_counts_author.py`
- `tests/test_catalog_counts_no_push.py`
- `tests/test_catalog_counts_no_prompt.py`
- `tests/test_catalog_counts_publish_behavior.py`
- `docs/ops/HANDOFF-counts-timer-1108.md`

## Tests

Behavior tests. Each one runs the scripts as subprocesses against a temp dir and a local bare origin. They pass `--wt` and `PFY_LOOP_REPO`. They do not use `~/DEVELOP/pfy-mentat`.

18 new test methods, all OK. The older counts tests (`test_catalog_counts_from_cards`, `test_catalog_counts_idempotent`, `test_catalog_counts_fail_recover`) still pass. Fetch and push use the machine's existing git credential helper. `GIT_TERMINAL_PROMPT=0` makes a missing credential fail the run instead of waiting at a prompt.

- busy lock exits 75 and does not run the command
- missing parent is created, the worktree matches `origin/main`, and the command runs
- the lock stays held while the command runs
- a second run resets local edits, deletes untracked files, and keeps `tmp/`
- `DIR` equal to the repo exits 2 and does not reset that checkout
- a foreign git dir exits 2 and is not reset
- `ExecStart` fetches before `git show origin/main:scripts/loop_worktree.sh`, writes `%t/pfy-loop-worktree.sh`, and `WorkingDirectory` is `%h`
- `Type=oneshot`, `Nice=10`, timer 04:17, `Persistent=true`
- a rejected push rebases the counts commit and fast-forwards on the next push, with no force
- `catalog_counts.py` exit 1 does not commit or push
- author and committer are `catalog-loop <catalog-loop@localhost>`
- `PFY_LOOP_NO_PUSH=1` prints the three paths and does not commit
- push sets `GIT_TERMINAL_PROMPT=0`
- a stray path exits 3 and pushes nothing, including when `PFY_LOOP_NO_PUSH=1`
- a clean tree prints `unchanged`
- publish refuses to run in the repo top-level
- three rejected pushes exit 1, the push count is 3, and history is not forced

Also:

- `python3 scripts/catalog_check.py`: PASS
- `python3 scripts/check_no_encoded_payloads.py`: PASS

No full suite. No model. Not pushed. The unit was not installed.
