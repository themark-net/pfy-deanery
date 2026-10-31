# 05 board loaders

Why picked: T-0124 says the OpenCode enterable path is still its own loader, and scripts/pfy-board.py copies the same importlib block many times. The full fold is too big for one cloud task. Type: refactor under 50 lines of the first three copies only. The check is dogfood_gate.py on the throwaway. It loads a good module, a missing file, and a module that raises, and it rejects a rewrite of _load_attach_220.

Gate before exit 1 (missing _load_script). Gate after exit 0. Review accept. One attempt.

Human accept: yes. The helper is the old body with the path and module name as arguments. The three wrappers keep their names and docstrings and return _load_script with the same module name and filename they used to hard-code. _load_attach_220 still has its own spec_from_file_location body. The diff is 10 insertions and 26 deletions, one file. Call sites are unchanged. The other copied loaders stay, which is the limit the task set so the diff stayed under 50 lines.

Wall: 133 seconds. Cloud commit 5e44ca0. Pushed false. worktree_removed true.
