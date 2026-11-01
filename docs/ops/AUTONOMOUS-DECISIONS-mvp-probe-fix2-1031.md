# Autonomous decisions mvp-probe-fix2-1031

1. Choice: treat `repo-handoff-doc-required` and `write-loop-exits-first` as the drop-in states them (exit card in the run log before probe work, handoff on every exit). Alternatives: block until those skill files appear. Why: no SKILL.md with either name is in this checkout or `~/.grok/skills`. `prefer-behavior-and-fail-recover-tests` and `agent-loops` are present and are followed.

2. Choice: the five parenthetical variants are the new probe families (hardlink, symlink to a directory, rename plus edit, NFC vs NFD, gate mode bits), each aimed at the blocker it extends, with a few neighbor cases so a single happy path cannot hide a miss. Alternatives: a full 5x5 matrix, or only the five names with no neighbors. Why: the parenthetical lists five families; neighbors stay inside the same blocker and still finish inside the wall cap.

3. Choice: scratch repos and TMPDIR stay under this worktree `tmp/`. Hardlink targets live in the stub-notes directory the test seam already bind-mounts, so the probe does not need the host `/tmp`. Alternatives: put sentinels in `/tmp`. Why: the drop-in forbids `/tmp`.

4. Choice: a probe is a FINDING only when the tip commits bytes or a mode the reviewer did not see, leaks sentinel bytes into a receipt or review prompt, mangles a name, or accepts a review body that should fail closed. A fail-closed result is a hold. Alternatives: treat every non-PASS as a bug. Why: S7's old bug was a false fail, so a legitimate rename or unicode path that still fails closed is also a FINDING. Speculative policy beyond those two shapes waits for a probe result.
