# Autonomous decisions: mvp-pass3-review-1031

One line each. Choice, alternatives, why. Append only.

1. 2026-11-01T00:35Z: Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. Choice: follow the drop-in exit list, the agent-loops eight-exit card in `docs/ops/RUN-LOG-mvp-pass3-review-1031.md`, and `docs/ops/HANDOFF-mvp-pass3-review-1031.md`. Alternative: stop and ask. Why: the drop-in already states the exits and the handoff path, and it says not to ask.
2. 2026-11-01T00:35Z: Severity B means blocker (wrong behavior, fail-open, secret, or a test that cannot catch its bug). S means should-fix. N means nit (dead code, doc contradiction, small scratch-path miss). Alternative: treat every finding as a blocker. Why: the drop-in fixes every small S and N inside one function, and fixes a B only when the patch is under 30 lines.
3. 2026-11-01T00:35Z: Fixes stay on this branch, one commit and one push each, lead only. Alternative: one sub-agent per fix in extra worktrees. Why: the drop-in forbids other worktrees under `tmp/`, and two writers on one branch would race the push.
4. 2026-11-01T00:35Z: `scripts/pfy_build_local.py` review code is a cross-lane request even when a finding is small. Alternative: patch the review helpers here. Why: the drop-in names that file as owned by the mvp3 live lane.
5. 2026-11-01T00:50Z: Do not edit `scripts/pfy_build_cloud.py` either. Live lanes mvp-timeoutfix-1031 and mvp-cloud-perf-1031 both name that file. Findings 3, 4, and 7 stay cross-lane. Alternative: patch `diff_aims_at_root` and `_protected` here because each fix is under 30 lines. Why: the drop-in says not to edit a file a live lane owns.
6. 2026-11-01T00:50Z: The ripgrep echo hole is two functions, so two commits. Alternative: one commit for both. Why: the drop-in says one commit per finding that sits inside one function, and each test stays red if only the other function is fixed.
