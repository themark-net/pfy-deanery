# 02 pregate orphans

Why picked: docs/ops/HANDOFF-pregate.md says the orphan check only matches a live cwd or argv, and own_child will not signal a pid whose ppid is 1. Type: two product files (shell plus a new helper) and a behavior test committed only on the throwaway before the run. Not the latest-summary or lock tasks from the earlier dogfood lane.

Gate before exit 1 (ImportError, no module pregate_orphans). Gate after exit 0, 5 tests. Review accept. One attempt. Wall 1490 seconds.

Diff: 2 files, 230 insertions, 15 deletions (245 changed lines). Patch is 10454 characters, under the 12000 character review cap, so this run does not show truncation. It is the closest run so far.

Human accept: yes. tracked uses a slash boundary, note records only tracked pids, escaped returns sorted live pids that left the roots, and signal_pids keeps ppid 1 while dropping this run's own children. pregate.sh calls the helper on non-comment lines for the leak check and for end-of-run signals. A recorded pid that later chdirs is still a leak. A reparented recorded pid is printed by the signal command. A never-recorded pid is not. bash -n on the shell is clean. The sampler polls ps every 0.25 seconds for the length of the run; that is the produced design, and it still matches the task.

Cloud commit subject is the task text cut mid-word ("sees a proc"). Same runner finding as task 01. One comment in the helper contains an em dash. Left as produced. Cherry-picked with the Built-by trailer. The behavior test is added on this branch in the following commit. It was written before the run.

Pushed false. worktree_removed true.
