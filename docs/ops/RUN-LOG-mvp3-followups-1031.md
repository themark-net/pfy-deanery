# RUN-LOG mvp3-followups-1031

Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp3-followups-1031`
Branch: `bot/mvp3-followups-1031`
Base: `6664713` (parent of the drop-in `a9dc798`). `origin/main` at start is `c0d38af`, an ancestor. No merge. Never rebase. Never push `bot/mvp3-review-retry`.
Launch: `2026-10-31T23:09:23Z`
Wall cap: `2026-11-01T07:09:23Z` (8 hours). Calendar cap `2026-11-02T02:00:00Z` is later, so the 8 hour cap wins. Stop new items at `2026-11-01T06:49:23Z` and leave 20 minutes for the handoff.
Host at launch: MemAvailable about 80 GiB, load 3.74, 32 cores. Pressure line is MemAvailable under 16 GiB, or load over 64 for 5 minutes.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal: close reviewer follow-ups 1 to 10 on 582414b/6664713, then the next MVP gap that fits this lane, without editing files another live lane owns.
1 Goal met: each item is pushed, or recorded skipped with a reason. Tests for any code this lane changes. Handoff written.
2 Turn cap: 10 listed items, then at most 3 further gaps. Stop on lane empty.
3 Budget cap: no cloud spend, no local model, no pregate.sh. Stubs only.
4 Wall clock: 2026-11-01T07:09:23Z, handoff buffer from 2026-11-01T06:49:23Z. Calendar backstop 2026-11-02T02:00:00Z.
5 No progress: the same failure twice with no new information, or 3 items in a row skipped for the same blocker.
6 Human interrupt: user stop. No questions. Conservative choice goes in the decisions file.
7 Error threshold: 3 consecutive same test failures, then stop that area.
8 External event: if origin/main moves, merge it (never rebase) before the next item. If another lane already owns the file, do not edit it.
Loop type: goal
Human gate: Tester plus Reviewer for runtime. Pregate plus Reviewer for docs or test-only. This run does not merge.
```

## Plan

Overview: The ten follow-ups are one workstream on the local review loop. `bot/mvp-review-fix2-1031` already owns the runner and the review tests and has a divergent tip (`c114c7f`). This lead does not spawn a second editor. Docs that no other lane owns land here. Code in owned files is a cross-lane request, not a second copy.

Phases:
- exits | `docs/ops/RUN-LOG-mvp3-followups-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp3-followups-1031.md` | card committed before item edits | none | lead
- item 1 | `docs/ops/HANDOFF-pfy-local-build-mvp.md` Usage | the 3-file / 250-line cap and PASS-REJECT are in the operator --local docs | exits | lead
- item 2 | owned: `scripts/pfy_build_local.py`, `tests/test_pfy_build_local_review.py` | cross-lane, do not edit | exits | lead
- item 3 | same owned runner | cross-lane | exits | lead
- item 4 | Usage doc, receipt field is owned | docs sentence here; receipt cross-lane | item 1 | lead
- item 5 | owned runner | cross-lane | exits | lead
- item 6 | owned `tests/test_pfy_build_local.py`; note in this lane's handoff | pin is cross-lane; inversion noted | exits | lead
- item 7 | owned runner | cross-lane | exits | lead
- item 8 | owned `docs/ops/HANDOFF-mvp3-review-retry.md` | cross-lane | exits | lead
- item 9 | this lane's handoff, plus a bwrap-hidden run of the review module | explanation of ubuntu skips; code only if review E2E does not run and the test file is not owned | exits | lead
- item 10 | `docs/ops/RUN-LOG-mvp3-review-retry.md` process note | current practice is `TMPDIR=$PWD/tmp` in the worktree | exits | lead
- handoff | `docs/ops/HANDOFF-mvp3-followups-1031.md` | SHAs, skips, fail/recover, gate, next step | all items | lead

Risks:
- Editing `scripts/pfy_build_local.py` while review-fix2 is live would fork the runner. Mitigation: do not edit owned files. Name the remaining gap in the handoff.
- An in-repo `TMPDIR` fails `test_relative_outdir_log_path_safe`. Mitigation: record it if a full discover is run. Do not point `TMPDIR` at the main checkout.
- Three owned-file skips in a row trip exit 5 if they are the same blocker. Mitigation: the owned-file skips are one recorded decision, not three failed attempts. A skip with a new reason still counts. If items 2, 3, and 5 are the first three and all are the same ownership blocker, stop after recording them and still write the handoff. Items that this lane can land are done before that stop is applied to the remaining list, so the docs items are not dropped.

## Items

- exits | `0f6fa08` | none (card only) | pushed
- item 1 | `d3e73f6` | docs only, no test | Review section in the operator usage doc: default on, cap 3 files / 250 lines, larger legitimate diffs are PASS-REJECTED
- item 4 | `16f7c07` | docs only, no test | Same section now says the reviewer is the same local model as the agent. Receipt field is cross-lane.
- item 10 | (this commit) | docs only, no test | Standing TMPDIR note is now TMPDIR=$PWD/tmp in the worktree. The old tmp/pgs line stays as history of that run.

## Host checks

- 2026-10-31T23:09:23Z MemAvailable about 80 GiB, load 3.74, 32 cores. Under the pressure line.
