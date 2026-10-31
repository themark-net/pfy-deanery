# Autonomous decisions mvp-realfail-1031

One line each. Choice, alternatives, why.

- 2026-10-31T20:17:03Z: skills write-loop-exits-first and repo-handoff-doc-required are not files in this worktree or ~/.grok/skills. Bound the loop to the drop-in exits, the agent-loops exit card in the run log, and docs/ops/HANDOFF-mvp-realfail-1031.md. Alternative was to stop and ask. The drop-in already names the exits and the handoff path.
- 2026-10-31T20:17:03Z: the failure cases share this worktree, the process table, and a merge of origin/bot/mvp-cloud-1031 before each item. They are one sequential workstream run by the lead. Parallel case subagents would race git and could signal a process this lane did not start. The project-map subagent is the only background agent and it writes only .project-map/.
- 2026-10-31T20:17:03Z: wall clock follows the drop-in (8h from 2026-10-31T20:17:03Z, new items stop 2026-11-01T03:57:03Z) rather than the orchestrator skill's 6h clock. The Sunday 2026-11-02T02:00Z cap is later, so the 8h cap binds.
- 2026-10-31T20:17:03Z: demo targets are tiny git repos under this worktree's tmp/, with --repo and --base HEAD. Alternative was cloning pfy-mentat. A full clone would point grok at the catalog tree. Nothing is pushed from a target repo.
- 2026-10-31T20:17:03Z: push of bot/mvp-realfail-1031 is required by the drop-in. The orchestrator skill's default "do not push" does not apply. No force, no PR, no merge to main.
- 2026-10-31T20:17:03Z: owned paths are eval/mvp-1031/realfail/**, tests/test_mvp_1031_realfail_receipts.py, and the three docs/ops files named in the drop-in. The plan matrix gives other eval/mvp-1031 paths to mvp-eval-1031. Those stay untouched.
- 2026-10-31T20:30:39Z: interrupted runs use --retries 0 --no-review --timeout 30 --base HEAD and a fast gate. Alternative was the default 3 attempts with review. The interrupt is defined on the first grok call, so one implement call is the whole case.
- 2026-10-31T20:32:06Z: sigkill-reap is a FINDING even though the receipt status matches. The DoD also requires no stray grok process. Alternative was to mark matches and mention the orphan only as a note. The stray process is the failure.
- 2026-10-31T20:35:34Z: dirty-caller uses --no-review and one attempt. Alternative was a reviewed pass. The row is about caller dirtiness, and --no-review still commits on a green gate.
- 2026-10-31T20:41:00Z: review-reject uses danger.sh containing rm -rf / instead of deleting tests. Alternative was the drop-in example of deleting the tests directory. That example is classified tests-tampered before review, so the reviewer never sees it. The script case reaches review. The accept result is a FINDING.
