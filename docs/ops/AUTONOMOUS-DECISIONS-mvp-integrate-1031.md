# Autonomous decisions mvp-integrate-1031

One line per choice. Conservative default. No questions.

- 2026-10-31T20:42:00Z: Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. Bound the loop to the drop-in exit list, the agent-loops exit card in the run log, and `docs/ops/HANDOFF-mvp-integrate-1031.md`. Alternative was to stop and ask. The drop-in already states the exits and the handoff path.
- 2026-10-31T20:42:00Z: Lead executes every phase on this worktree. Alternative was one sub-agent per merge. The merges share one index, must stay in the listed order, and each successful merge is pushed. Parallel agents would race that checkout.
- 2026-10-31T20:42:00Z: Wall cap used is 2026-11-01T04:42:00Z (8 hours from the observed launch), earlier than 2026-11-02T02:00Z. Handoff buffer starts at 2026-11-01T04:22:00Z.
- 2026-10-31T20:46:00Z: Conflict `docs/modules/pfylib.md` while merging `origin/bot/pfy-followups-1030`. Kept both still-true facts: backlog hyphen wording on the `_legacy` invariant, and followups T-0124 (OpenCode open path is `attach.open_opencode_session`, `pfy_enterable_162_b.py` is the shim, that path writes config, skills, and tools env, four harnesses stay on `open_session`). Dropped the backlog sentence that OpenCode was still its own path, because followups owns `pfylib/attach.py` and that sentence contradicts the landed code. `docs/TODO.md` auto-merged with all 90 row ids from both sides.
