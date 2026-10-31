# Autonomous decisions: mvp-review-fix2-1031

One line each. Choice, alternatives, why. Append only.

1. 2026-10-31T20:42Z: Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. Choice: follow the drop-in exit list, the agent-loops eight-exit card in the run log, and `docs/ops/HANDOFF-mvp-review-fix2-1031.md`. Alternative: stop and ask. Why: the drop-in already states the exits and the handoff path, and it says not to ask.
2. 2026-10-31T20:42Z: Listed items share `scripts/pfy_build_local.py` and the review tests. Choice: the lead implements them in order in this worktree. Alternative: one sub-agent per item in extra worktrees. Why: the orchestrator spawns only independent workstreams, this drop-in forbids other worktrees under `tmp/`, and each item must commit and push on this branch before the next starts.
3. 2026-10-31T20:55Z: Reviewer outage uses exit code 1 with status `REVIEW-ERROR` and reason `review-unavailable`. Alternative: exit 3 TIMEOUT, or exit 4 BLOCKED. Why: the agent did not time out and the host is not blocked. The build did not pass. The status string keeps it off the reject path.
4. 2026-10-31T21:10Z: `PFY_STUB_*` binds are read only when `PFY_LOCAL_BUILD_TEST_SEAM=1`. Alternative: a private function argument tests monkeypatch. Why: the runner is a subprocess in the tests, so an env seam is the flag the child actually sees. Production leaves it unset and the receipt `sandbox_extra_rw` stays empty.
