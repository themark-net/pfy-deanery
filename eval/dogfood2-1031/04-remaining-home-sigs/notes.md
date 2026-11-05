# 04 remaining home signatures

Why picked: docs/automation/x-intake-2026-10-16-handoff.md parks mode-000, symlink retarget, and chmod-only as blind spots. smoke_117_118.tree_sig, smoke_148.home_sig, and smoke_149.home_sig still hashed size and mtime. smoke_128_130.home_sig records mtime on purpose, so it was left alone. The copies in smoke_112, smoke_115, smoke_119, and smoke_122 were already done. Type: three product files. The check is tests/test_remaining_home_sigs.py, committed only on the throwaway before the run.

Gate before exit 1 (mtime-only updates changed both kinds of signature). Gate after exit 0, 2 tests. Review accept. One attempt. Wall 661 seconds.

Diff: 3 files, 113 insertions, 17 deletions (130 changed lines). Patch is 6693 characters, under the 12000 character review cap, so this run does not show truncation.

Human accept: yes. tree_sig streams file bytes, uses lstat mode, hashes readlink text, and does not follow links. Each home_sig returns the same WATCHED keys, None when a watched path is missing, and a digest that ignores mtime. The 148 and 149 suites, plus the 117 suite, still pass (46 tests). Those suites expect a planted real-HOME write to fail real_home_unchanged, and they still do.

Cloud commit subject is the task text cut at 72 characters ("says m"). Task 01 used the same opening sentence, so the two subjects match. That is a runner finding. Cherry-picked as 3e4c7ba with the Built-by trailer. The behavior test is added on this branch in the following commit. It was written before the run.

Pushed false. worktree_removed true.
