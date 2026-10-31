# Autonomous decisions: mvp-selfhost2-1031

One line each. Choice, alternatives, why. No secrets.

- 2026-10-31T23:26:06Z: Skills write-loop-exits-first and repo-handoff-doc-required are not files in this worktree or ~/.grok/skills. Choice: bind the loop to the drop-in exit list, the eight-exit card in docs/ops/RUN-LOG-mvp-selfhost2-1031.md, and docs/ops/HANDOFF-mvp-selfhost2-1031.md. Alternative: stop and ask. Why: the drop-in already names the exits and the handoff path, and it says not to ask. prefer-behavior-and-fail-recover-tests and orchestrator are on disk and are followed.
- 2026-10-31T23:26:06Z: Builds stay serial in this worktree. Alternative: one sub-agent per item. Why: every item cherry-picks onto bot/mvp-selfhost2-1031 and shares one git index. Parallel agents would race that checkout. The project-map agent is the only extra agent, and it may write only .project-map/.
- 2026-10-31T23:26:06Z: Turn cap is 16 build attempts, not a hard stop at 10 landed items. Alternative: stop at 10. Why: the drop-in says aim for 10 and then keep taking the next fitting gap until an exit fires. Sixteen attempts bounds cloud spend if items keep failing.
