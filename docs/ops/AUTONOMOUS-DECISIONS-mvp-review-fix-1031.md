# Autonomous decisions: mvp-review-fix-1031

Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-review-fix-1031`
Branch: `bot/mvp-review-fix-1031`
Started: 2026-10-31T19:50:34Z

1. 2026-10-31T19:50Z: Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. Choice: follow the drop-in exit list, the agent-loops eight-exit card in the run log, and `docs/ops/HANDOFF-mvp-review-fix-1031.md`. Alternative: stop and ask. Why: the drop-in already states the exits and the handoff path, and it says not to ask.

2. 2026-10-31T19:50Z: Do not spawn implementation sub-agents for scope-commit and no-change. Choice: the lead edits the shared runner and tests in order. Alternative: one sub-agent per item in extra worktrees. Why: both items own `scripts/pfy_build_local.py` and the same test modules, the drop-in orders them, and this run may use only this worktree.

3. 2026-10-31T19:50Z: Project map. Choice: spawn the project-map subagent to write `.project-map/index.html` only, and do not commit that directory (it is outside the owned file list). Alternative: skip the map. Why: the user project-map rule asks for the map before a long unattended stretch. Owned-file commits stay explicit paths.
