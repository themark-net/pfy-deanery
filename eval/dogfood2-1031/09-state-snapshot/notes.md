# 09 smoke_109 state_snapshot

Why picked: state_snapshot in examples/x-intake-local/smoke_109_111.py still stored the newest mtime. A same-size rewrite with the mtime restored, a chmod, and an unreadable file all compared equal. smoke_128_130.home_sig keeps mtime on purpose and stayed out. The smolvm functions in the same file stayed out.

Gate before: AssertionError 1700000000.0 == 1700000000.0 on the restored-mtime rewrite. Gate after, on this branch: tests.test_state_snapshot_109 plus the 13 tests in tests.test_x_intake_smoke_109_111, 14 OK in 3.014s. Review accept. One attempt. Wall 643 seconds.

Diff: 1 file, 54 insertions, 10 deletions (64 changed lines). Patch is 2892 characters, under the 12000 character review cap. This run is one file and just over the 60 line aim. The review diff is complete.

Human accept: yes. Each path has one value, or None when the path is missing. The value is a hash of streamed file bytes, lstat mode, and symlink text. mtime stays outside the value. An unreadable file stays in the hash, so a tree that contains one differs from an empty directory with the same stamp. The no-bwrap real-home snapshot test still passes.

Cloud commit subject is the task text cut at 72 characters ("records only"). Cherry-picked as 110f24a with the Built-by trailer. The behavior test was written before the run and is added on this branch in the following commit. Leave the subject and the produced function as the runner wrote them.

Pushed false on the cloud branch. worktree_removed true.
