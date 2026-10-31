# Autonomous decisions mvp-followups-fix2-1031

One line per decision. No questions asked. Conservative and reversible.

1. Choice: the lead executes every item in this worktree, in order, and does not spawn implementation sub-agents. The project-map sub-agent may write only `.project-map/` (gitignored). Alternatives: parallel sub-agents on `build/<phase>` worktrees, or shared-checkout sub-agents. Why: the request forbids other worktrees and requires a push of this branch after every item. Items 1 to 3 share the lint files. The run log and handoff are shared.

2. Choice: follow `repo-handoff-doc-required` and `write-loop-exits-first` as the drop-in states them (handoff doc on every exit; exit card in the run log before item work) plus `.grok/skills/agent-loops`. Alternatives: block until those skill files appear. Why: no `SKILL.md` with either name is in this checkout or `~/.grok/skills`. `prefer-behavior-and-fail-recover-tests` is present and is followed.
