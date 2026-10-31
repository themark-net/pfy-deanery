# 08 next board loaders

Why picked: run 05 folded the first three copied loaders on another throwaway, and this base still has the rest inline. A docs-plus-check was skipped because the only broken docs links need ADR-0017. Type: refactor under 50 lines of the next three loaders. The check is dogfood_gate.py on the throwaway. It loads a good module, a missing file, and a module that raises, and it rejects a rewrite of _load_enterable_162 or _load_recommend_207.

Gate before exit 1 (missing _load_script). Gate after exit 0. Review accept. One attempt.

Human accept: yes. The helper is the old body with the path and module name as arguments. The three wrappers keep their names and docstrings and return _load_script with the filenames they used to hard-code. _load_enterable_162 and _load_recommend_207 are outside the diff. The diff is 10 insertions and 26 deletions, one file. Call sites are unchanged.

Wall: 130 seconds. Cloud commit 51f4cd7. Pushed false. worktree_removed true.
