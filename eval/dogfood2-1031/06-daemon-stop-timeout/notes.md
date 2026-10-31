# 06 daemon-stop timeout

Why picked: eval/mvp3/tasks/t3. smoke_overtime records a daemon-stop TimeoutExpired on the step, then still returns the success sentence when overtimed.lock is gone. Type: one product file. The gate tests/test_mvp2_t3_daemon_stop.py was copied from eval/mvp2/gates and committed only on the throwaway. The existing daemon-stop assertion stays read-only.

Gate before exit 1 (return code 0 and the success sentence). Gate after exit 0, 2 tests. Review accept. One attempt. Wall 301 seconds.

Diff: 1 file, 6 insertions, 1 deletion (7 changed lines). Patch is 1666 characters, under the 12000 character review cap. This run is below the 2 file and 60 line aim. It does not show truncation.

Human accept: yes. A stop timeout is stored on the step and, when the lock is not alive, becomes the receipt reason and exit 1. A live lock still returns daemon still running before that check. A clean stop leaves the success sentence. A command timeout is still reported ahead of a stop timeout. The required case matches the gate.

Cloud commit subject is the task text cut at 72 characters ("a daemon s"). Cherry-picked as 072c7cd with the Built-by trailer. The behavior test is added on this branch in the following commit. It was written before the run.

Pushed false. worktree_removed true.
