# Autonomous decisions: mvp-review-fix-1031

Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-review-fix-1031`
Branch: `bot/mvp-review-fix-1031`
Started: 2026-10-31T19:50:34Z

1. 2026-10-31T19:50Z: Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. Choice: follow the drop-in exit list, the agent-loops eight-exit card in the run log, and `docs/ops/HANDOFF-mvp-review-fix-1031.md`. Alternative: stop and ask. Why: the drop-in already states the exits and the handoff path, and it says not to ask.

2. 2026-10-31T19:50Z: Do not spawn implementation sub-agents for scope-commit and no-change. Choice: the lead edits the shared runner and tests in order. Alternative: one sub-agent per item in extra worktrees. Why: both items own `scripts/pfy_build_local.py` and the same test modules, the drop-in orders them, and this run may use only this worktree.

3. 2026-10-31T19:50Z: Project map. Choice: spawn the project-map subagent to write `.project-map/index.html` only, and do not commit that directory (it is outside the owned file list). Alternative: skip the map. Why: the user project-map rule asks for the map before a long unattended stretch. Owned-file commits stay explicit paths. `.gitignore` already ignores `.project-map/`.

4. 2026-10-31T20:00Z: Stage only the reviewed names, with `:(literal)` pathspecs, and keep the tmp, bytecode, and pytest-cache excludes on both sides of the compare. Alternative: keep `git add -A -f` and fail closed whenever an ignored path would have been staged. Why: the drop-in says to stage the reviewed paths. A green fix plus an ignored receipt must still commit the fix. The excludes stay so a pytest cache path in `git status` does not false-mismatch.

5. 2026-10-31T20:00Z: `test_ignored_helper_is_in_the_commit` now expects fail-closed (`commit-recheck-failed` or `scope-commit-mismatch`) and no `src/helper.py` on any ref. Alternative: keep force-adding the ignored helper so the recheck passes. Why: that test encoded the t5 hole. The helper is not in the reviewed set. The archive recheck is the recovery when the committed tree cannot import it.

6. 2026-10-31T20:00Z: `PFY_LOCAL_BUILD_INJECT_EXTRA_STAGE=1` stages one extra path so the mismatch reset is observable. Alternative: rely only on the ignored-file test. Why: staging only reviewed paths does not mismatch on that case, so deleting the compare would still pass it. Unset in normal runs. Same pattern as `PFY_LOCAL_BUILD_INJECT_CRASH`.

7. 2026-10-31T20:10Z: On an empty diff, run the post-attempt gate once, record `no-change` even when that gate is green, and put the gate tail in the retry feedback. Do not call the review model. `interrupted`, `mem-edge`, and `test-cmd-failed-to-start` keep their own reasons. Alternative: treat a green gate plus an empty diff as PASS, or reuse `tests_before` and skip the second run. Why: the drop-in says the empty path continued before `run_tests`, and a green gate plus an empty diff is still `no-change`.

8. 2026-10-31T20:11Z: Do not start the round-2 sandbox-gate item in this lane. Alternative: close the `--unsafe-no-sandbox` gate gap now, since the runner is an owned file. Why: `docs/plans/MVP-PARALLEL-1031.md` launches `mvp-sandbox-gate-1031` only after `origin/bot/mvp-integrate-1031` exists, on its own branch. That ref does not exist. Doing the work here would be a second copy of a scheduled lane.

9. 2026-10-31T20:11Z: Do not run `./scripts/pregate.sh`. Alternative: wait on the heavy lock and run the full discover here. Why: the lock is held by another lane's pregate (pid 1441386 at 2026-10-31T20:10:53Z) and two more pregates are waiting. The script also adds a worktree under `~/DEVELOP/pfy-mentat/tmp/pg/`, which this lane must not touch. Record pregate not run: host busy.
