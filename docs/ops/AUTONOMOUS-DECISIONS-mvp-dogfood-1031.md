# Autonomous decisions: mvp-dogfood-1031

- 2026-10-31: Skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. Bound the loop to the drop-in exit list, the agent-loops exit card in the run log, and `docs/ops/HANDOFF-mvp-dogfood-1031.md`. Alternative was to stop and ask. The drop-in already states the exits and the handoff path.
- 2026-10-31: Turn cap is 16 items, not the agent-loops default of 8. The drop-in asks for 5 runs and then more toward 10 or more. A cap of 8 would stop the lane before that aim. Wall clock and no-progress still bind.
- 2026-10-31: Dogfood builds run one at a time in this lead session. Parallel cloud builds would share the rate limit and this branch. Alternative was one subagent per run. Rejected because a second worktree under `tmp/` is forbidden and a shared worktree would race commits.
- 2026-10-31: Project-map and a read-only task scout may run beside the lead. They do not commit. Implementers are not spawned.
- 2026-10-31: `tests/test_mvp_1031_dogfood_reports.py` is in scope because the drop-in names it as an acceptance test. Owned product files of other lanes stay untouched.
- 2026-10-31: Each dogfood gate uses a targeted `--test-cmd`, not `python3 -m unittest discover`. Discover is a heavy job and would run three times per attempt. `--repo`, `--base demo-base`, and `--receipt-dir` are set. `--local` is never set. Default `--retries` and `--timeout` stay so the daily retry path is the one under test.
- 2026-10-31: Do not pass `--keep-worktree` on the first runs. The daily receipt says `worktree_removed` true. If a failure leaves no `cloud/` branch, `diff.patch` states that no branch was created. Revisit only if a failure diff cannot be recovered from the receipt.
- 2026-10-31: Throwaway targets are `git clone --no-hardlinks` of this worktree into `tmp/target-N`, then `checkout -b demo-base`. `--base demo-base`. Nothing is pushed from a target.
