# 06 digest after add

Why picked: HANDOFF-pfy-local-build-mvp says the rehash before git add is back-to-back with the gated digest, so it does not cover a write during git add. The late-rewrite test proves namespace death, not that window. Type: code fix. The check is dogfood_gate.py on the throwaway, not a new file under tests/. The git add -A -f flags stay, because another lane owns that list.

Gate before exit 1 (digest check is still before git add). Gate after exit 0. Review accept. One attempt.

Human accept: yes. The diff deletes the three-line check that sat next to gated_tree and inserts the same three lines after the add's commit-failed return and before the commit call. The timeout return stays. The add argument list is not in the diff. A write that lands after this new check and before commit can still slip. That is a smaller window than the one the handoff named.

Wall: 68 seconds. Cloud commit 6c9db24. Pushed false. worktree_removed true.
