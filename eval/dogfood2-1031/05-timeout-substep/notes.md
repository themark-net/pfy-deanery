# 05 timeout sub-step reasons

Why picked: eval/mvp3/tasks/t4. Timeouts in smoke_112_114.py named the entry (overtime, festival) instead of the command that timed out. Type: one product file plus two assertion strings in the existing suite. The gate tests/test_mvp2_t4_timeout_step.py was copied from eval/mvp2/gates and committed only on the throwaway. --writable-test names the existing suite so those two strings can change.

Gate before exit 1 (reasons were still overtime timeout and festival timeout). Gate after exit 0, 5 tests. Review accept. One attempt. Wall 306 seconds.

Diff: 2 files, 14 insertions, 5 deletions (19 changed lines). Patch is 3925 characters, under the 12000 character review cap. This run is below the 60 line aim. It does not show truncation.

Human accept: yes. The overtime new command sets the step name to new and re-raises, so other overtime timeouts still use the entry name. Festival's fest --version catch returns version timeout after 0.4s. The daemon-stop assertion is unchanged and still passes. The existing suite diff is only those two expected strings.

Cloud commit subject is the task text cut at 72 characters ("entry (ove"). Cherry-picked as 26e71fa with the Built-by trailer. The behavior test is added on this branch in the following commit. It was written before the run.

Pushed false. worktree_removed true.
