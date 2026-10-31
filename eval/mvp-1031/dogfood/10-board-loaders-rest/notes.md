# 10 recommend launch catalog loaders

Why picked: two earlier throwaways folded other copies of the same board loader, and these three were still inline on the base. Type: refactor under 50 lines. The check is dogfood_gate.py on the throwaway. It loads a good module, a missing file, and a module that raises, and it rejects a rewrite of _load_live_org_214 or _load_enterable_162.

Gate before exit 1 (missing _load_script). Gate after exit 0. Review accept. One attempt.

Human accept: yes. The helper is the old body with the path and module name as arguments. The three wrappers keep their names and docstrings and return _load_script with the filenames they used to hard-code. _load_live_org_214 is outside the diff. The diff is 10 insertions and 26 deletions, one file. Call sites are unchanged. This is the third time the runner produced this shape. Further copies would not teach more about the runner.

Wall: 166 seconds. Cloud commit fe9ccc5. Pushed false. worktree_removed true.
