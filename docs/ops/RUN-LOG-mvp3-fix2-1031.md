# Run log: mvp3-fix2-1031

Branch `bot/mvp3-review-retry`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp3`. Started `2026-11-01T00:10:14Z`. Wall cap `2026-11-01T03:10:14Z`.

```text
LOOP EXIT CARD
Goal: BX1, BX2, B2 (M10 M17 M18), S7, S8, and the doc lines are fixed, tested, and pushed.
1 Goal met: targeted tests green, then the full suite under the heavy lock. Probes red before the fix and green after.
2 Turn cap: 3 tries on one item, then record blocked and move on.
3 Budget cap: stubs only. No real --local model trial. No pregate.
4 Wall clock: 3h from 2026-11-01T00:10:14Z.
5 No-progress: 3 identical failures on one item.
6 Human interrupt: user stop.
7 Error threshold: 3 failed tries on one item.
8 External event: n/a (no merge, no PR).
Loop type: goal
Human gate: Tester plus Reviewer after this branch. No merge from this run.
```

state: running

| Item | Commit | Tests | Result |
|------|--------|-------|--------|
| BX1 | 4c7c5f6 | red then green: test_gate_rewrite_of_reviewed_file_does_not_commit. Review module 25 OK in 70.327s | gate rewrite no longer commits. Reason gate-modified-reviewed-file, one attempt, no retry |
| BX2 | this commit | red: in-scope symlink was scope-commit-mismatch after the reviewer saw the target; out-of-scope leaked into 3 patch.diff files and the agent prompt. Green: both symlink tests plus empty-diff. Review module 27 OK in 72.882s | symlink to outside is out of scope. Target bytes are not in the diff, the prompt, or receipts |
