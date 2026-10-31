# Autonomous decisions mvp-sixtask-1031

One line each. Choice, alternatives, why. Conservative and reversible.

- 2026-10-31T20:20Z | Skills `repo-handoff-doc-required` and `write-loop-exits-first` are not on disk under this worktree, `bootstrap/`, or `~/.grok/skills`. Follow the drop-in exit list and handoff section, plus `orchestrator` and `prefer-behavior-and-fail-recover-tests`, which are on disk. Do not invent those two skill files.
- 2026-10-31T20:20Z | Run the six grok builds one at a time in this session. Alternative was six parallel sub-agents. Rejected because they share one branch, one receipt tree, and one Grok rate limit. A parallel burst is the DoD rate-limit failure (exit 4) and a git race.
- 2026-10-31T20:20Z | Do not commit `.project-map/` (gitignored, outside owned files). The map agent may still write it for this session.
- 2026-10-31T20:20Z | Throwaway target is `git clone --no-hardlinks` of this worktree into `tmp/sixtask-clones/<task>`, then `demo-base` at `997d89264495861a178713ccf7d4447ea828afc4` plus the canonical MVP-2 gate commit. Do not `git worktree add` from Mark's main git dir.
- 2026-10-31T20:20Z | Pass `--keep-worktree` so a failed attempt still has a diff. The clone is gitignored. Nothing in the target is pushed.
- 2026-10-31T20:20Z | Leave `HOME` as the operator home so grok can use the existing login. Set `PFY_STATE_DIR` and `TMPDIR` under this worktree's `tmp/` so the launcher does not mkdir `~/.pfy-mentat` and scratch stays out of `/tmp`. Do not read `auth.json`.
- 2026-10-31T20:20Z | Pass `--timeout 900` (seconds per grok call and per gate). Default is 1200 and three attempts with review can exceed the lane clock. 900 is still about five times the slowest MVP-2 cloud task (173 s).
- 2026-10-31T20:20Z | `--retries 0` later means one attempt with review still on. Do not pass `--no-review` for that measurement. The loop's extra attempts are the thing being measured.
- 2026-10-31T20:20Z | Do not edit `docs/TODO.md` or `docs/PENDING-HANDOFF.md`. Plan D11 reserves those for integration. This lane's handoff is `docs/ops/HANDOFF-mvp-sixtask-1031.md`.
- 2026-10-31T20:20Z | Wall time in the report is the `./pfy build` process only, not clone or plant time. That matches the MVP-2 arm timing.
- 2026-10-31T20:20Z | Host load uses the 5-minute load average against 2x cores (64). One spike does not stop the lane. Over the line: pause 10 minutes, recheck, then stop if it persists.
- 2026-10-31T20:20Z | Suspected runner gap (not yet a finding): cloud `tests_tampered` treats every `tests/` edit as tamper and has no `--writable-test`, while t4 and t5 require those edits. Confirm with a real receipt before writing the cross-lane request. Do not skip the tasks and do not patch `scripts/pfy_build_cloud.py`.
- 2026-10-31T21:19Z | Pass 1 is NO-GO against the 6/6 bar. t4 and t5 receipts are `tests-tampered` while the canonical gates are green. The suggested patch stays under `eval/mvp-1031/sixtask/findings/` and is not applied. Variance and `--retries 0` still run: the drop-in asks for those measurements and the clock has hours left. A repeat of `tests-tampered` is a measurement, not another fix attempt.
