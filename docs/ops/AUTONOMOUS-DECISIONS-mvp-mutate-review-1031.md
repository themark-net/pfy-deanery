# Autonomous decisions — mvp-mutate-review-1031

One line each. Conservative choice, alternatives, why. No questions.

1. 2026-10-31T21:16Z: Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. Choice: follow the drop-in exit list, the agent-loops eight-exit card in the run log, and `docs/ops/HANDOFF-mvp-mutate-review-1031.md`. Alternative: stop and ask. Why: the drop-in already states the exits and the handoff path, and it says not to ask.
2. 2026-10-31T21:16Z: One workstream shares the harness, the report, and the survivor tests. Choice: the lead implements in order on this branch. The only sub-agent is `project-map`, and it writes only `.project-map/`. Alternative: spawn coding sub-agents. Why: parallel writers on one branch would race commits, and a second worktree is forbidden.
3. 2026-10-31T21:16Z: Mutant ids are R1 through R14. R4 is the Reviewer's M4 (outage treated as reject). R5 is the Reviewer's M7 (retry prompt drops the previous diff). The cap row is three mutants: files off by one loose (R7), lines off by one loose (R8), cap check removed (R9). Alternative: one combined cap mutant. Why: a combined edit can be killed by either bound, which hides a weak assertion on the other bound.
