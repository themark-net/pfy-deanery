# Autonomous decisions mvp-local-t5-1031

1. 2026-10-31T21:57Z: Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. Choice: follow the drop-in exit list, the agent-loops eight-exit card in the run log, and `docs/ops/HANDOFF-mvp-local-t5-1031.md`. Alternative: stop and ask. Why: the drop-in already states the exits and the handoff path, and it says not to ask.

2. 2026-10-31T21:57Z: Phases share the run log and `eval/mvp-1031/`. Choice: the lead runs them in order and does not spawn implementation sub-agents. Alternative: one sub-agent per phase. Why: the phases depend on each other and a second writer would race the owned files. The project-map subagent is allowed and writes only `.project-map/`.

3. 2026-10-31T21:57Z: `origin/bot/mvp-integrate-1031` resolves to `0c3f133d4d2ea2bf104f6390416fa8d26f394803`. Choice: continue on `bot/mvp-local-t5-1031`. Alternative: stop. Why: the base exists, so the round-2 stop does not fire. Do not branch from main.

4. 2026-10-31T21:57Z: MemAvailable 61386572 kB plus SwapFree 144 kB is about 58.5 GiB, and `ollama ps` listed no models. Choice: a later `qwen3.6:35b` load is allowed under the flock. Alternative: stop as host busy. Why: the sum is over 32 GiB and no model was loaded at launch.

5. 2026-10-31T22:05Z: The wrapper command passes no extra flag, and a separate flock attempt inside the script would race. Choice: continue only when an inherited fd already holds an exclusive FLOCK WRITE on `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock` (what `flock(1)` leaves open for the life of the process). The script never takes that lock itself. Tests set `PFY_RERUN_LOCK` to a temp file so they do not hold the host lock. The real run leaves that env unset. Alternative: require a flag the drop-in command does not pass, which would make the contract command refuse.

6. 2026-10-31T22:05Z: The task base is `997d892` and the fixed runner is this lane's `./pfy`. Choice: clone into this worktree's `tmp/`, plant the canonical gate, and pass that clone to `./pfy build --local`. Alternative: `git worktree add` on the shared git dir, which writes Mark's main checkout metadata. Why: the drop-in forbids touching that checkout.

7. 2026-10-31T22:05Z: A commit that contains a gitignored path is a failed rerun. Choice: the script exits 1 when that happens even if `./pfy` exited 0, and the note lists the paths. Alternative: leave the runner's exit 0 in place. Why: the drop-in says record the failure honestly and do not edit it away.

8. 2026-10-31T22:05Z: The behavior test cannot live under `tests/` because that tree is outside this lane's owned files. Choice: `eval/mvp-1031/test_rerun_local.py` beside the script. Alternative: skip the test file and only run the script by hand. Why: the drop-in requires a behavior test for the code change.

9. 2026-10-31T22:13Z: The heavy lock is held by `pregate.sh c0d38af` (flock pid 2652539) and three more waiters are queued (unittest discover, pregate 0c3f133, pregate fb759e9). Choice: wait until 2026-11-01T03:57Z for the lock, then run t5, and stop only this lane's t5 process at 2026-11-01T05:37Z if it is still going. Alternative: stop now and record host busy. Why: this lane must not cut ahead of another lane, and a t5 run still fits if the lock frees before 03:57Z. Do not signal any process this lane did not start.

10. 2026-10-31T23:05Z: The first t5 note treated every gitignored path in the full tree as a landing. Those three `pipelines/dogfood/local-bench-4/receipt-*.json` files are already in parent `bc865e84`. The commit diff is only the two test modules, and check-ignore on that diff is empty. Choice: a landed path is one this commit adds or changes. Re-score the saved commit. Do not rerun the model. Alternative: leave the rerun marked failed. Why: the drop-in says to record honestly, and a full-tree match of inherited files is not a landing.

11. 2026-10-31T23:05Z: t5 is recorded and the handoff reserve is about 6.5 hours away. t5 model time was about 10 minutes. Choice: run t4. The heavy lock is held again by `pregate.sh 6664713` (unittest discover). Wait until 2026-11-01T03:57Z, same as t5. Alternative: skip t4. Why: the drop-in says to run t4 when t5 is recorded and the cap still has room.
