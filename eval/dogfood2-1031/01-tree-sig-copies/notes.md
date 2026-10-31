# 01 tree-sig copies

Why picked: docs/automation/x-intake-2026-10-16-handoff.md parks mode-000, symlink retarget, and chmod-only as blind spots of tree_sig, and says smoke_119_121.py still uses mtime. The same helper is copied in smoke_112_114.py and smoke_115_116.py. smoke_122_124.py is the selfhost lane's task, so it was left alone. Type: three-file behavior fix. The check is tests/test_tree_sig_copies.py, committed only on the throwaway before the run.

Gate before exit 1 (three failures: chmod, content-plus-mtime, symlink follow). Gate after exit 0. Review accept. One attempt. Wall 398 seconds.

Diff: 3 files, 63 insertions, 12 deletions (75 changed lines). Under the 12000 character review cap, so this run does not show truncation.

Human accept: yes. Each tree_sig walks with rglob(recurse_symlinks=False), uses lstat and S_IMODE, streams file bytes in 1 MiB chunks, hashes readlink text for symlinks, and records an unreadable marker on OSError. mtime is not hashed. Call sites are unchanged. The three copies match.

Cloud commit subject is the task text cut mid-word ("says m"). That is a runner finding, not a reason to reject the tree. Cherry-picked as 31a863c with the Built-by trailer. The behavior test is added on this branch in the following commit. It was written before the run.

Pushed false. worktree_removed true.
