# RUN LOG mvp-tmpclean2-1031

Lane: Reviewer follow-ups on main. Branch `bot/mvp-tmpclean2-1031`.
Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-tmpclean2-1031`.
Base at open: `8f944a0` (drop-in) on `fb759e9` on `c0d38af`.
Opened: 2026-10-31T22:47:38Z (15:47 PT).

```text
LOOP EXIT CARD
Goal (success criteria):     Reviewer follow-ups 16 then 1,3,4,5,6,7,8,9,11,13,14,15 closed or skipped with a logged reason. Each code change has a behavior or fail/recover test, a commit, and a push. Fast-forward from origin/main preserved (merge, never rebase). Then the next MVP gap that fits this lane until an exit fires.
1 Goal met:                  Targeted unittest modules green for each item. Handoff written. Run log ends with state: DONE | lane empty | wall cap.
2 Turn cap:                  16 item attempts (listed follow-ups plus a few next gaps). An attempt is one item tried.
3 Budget cap:                No local model. No spend. Cloud Grok only. No pregate unless the runner is idle at the end, once, under the heavy lock.
4 Wall clock:                Stop new items at 2026-11-01T06:27:38Z. Hard stop 2026-11-01T06:47:38Z (8h from 2026-10-31T22:47:38Z). Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z) is later, so the 8h cap binds. Leave 20 minutes to write the handoff.
5 No-progress:               Same failure twice with no new information, or 3 items in a row skipped. Stop.
6 Human interrupt:           User stop. No questions otherwise. Irreversible actions stay inside the pre-authorization (own branch push only).
7 Error threshold:           3 consecutive item failures, or the same failure twice. Record and stop.
8 External event:            origin/main moves: merge it (never rebase) before the next item. A follow-up already done on origin/bot/mvp-followups-fix2-1031 or origin/main: skip that item.
Loop type:                   goal
Human gate:                  No merge, no PR, no tags. Tester plus Reviewer for runtime changes. Pregate plus Reviewer for docs, eval, or test-only changes.
```

Drop-in exits (also checked before every item):

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT, whichever comes first.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before the change. Record them and skip that area. Do not stop the lane.

Overview: Close the hermetic tmp-cleanup hole first (follow-up 16), then the c0d38af reviewer follow-ups that fix2 did not already take. One branch, one worktree, push after each item. Skip 2 and 10 unless trivial. After the list, take the next fitting MVP gap until an exit fires.

Phases:

- FU16 tmp hermetic | tests/test_pfylib_tmp_cleanup.py and pfylib host scratch if it ignores TMPDIR | private child TMPDIR or immune to a foreign /tmp/pfy-* dir; targeted tests green | none | general (lead)
- check-fix2 | origin/bot/mvp-followups-fix2-1031 handoff | F1, F2/FU12, P2, G1 marked done or still open | none | general (lead)
- FU1 ripgrep check | eval-structural workflow and its test | check is not name-only | after FU16 (same branch) | general (lead)
- FU3 version_of coverage | version_of tests | coverage without bwrap | after FU1 | general (lead)
- FU4 lint helper skip | test_pregate_lint_calls_helper | skip keys on PATH python3, not sys.executable | after FU3 | general (lead)
- FU5 pregate inside unittest | same test module | pregate-runs not written under repo tmp by the unittest | after FU4 | general (lead)
- FU6 T-0124 tests | T-0124 session tests | dead-terminal pre-creates the session file; tests for reuse prove, no engine, base drift, mode env, opencontext env | after FU5 | general (lead)
- FU7 toolsets comment | data/toolsets.json | line 89 names the real helper | after FU6 | general (lead)
- FU8 image-pin dup keys | image-pin lint and its test | duplicate keys rejected | after FU7 | general (lead)
- FU9 T-0124 active table | docs/TODO.md | done row leaves the active table | after FU8 | general (lead)
- FU11 run rechecks | bwrap run() tests | mount reason and which bwrap re-checks fail when broken; dir_usable isdir mutant fails | after FU9 | general (lead)
- FU13 proc mount not run | bwrap proc-mount test | asserts binary was not run (no checks, no escape) | after FU11 | general (lead)
- FU14 dry-run flake | tests/test_harness2_local_stage.py | stderr captured; flake cause fixed; test stable | after FU13 | general (lead)
- FU15 handoff note | docs/ops handoff that says "Pregate re-runs at the fix pin" | note matches c0d38af fail and CI 41242021101 rerun success | after FU14 | general (lead)
- skip-2 skip-10 | none unless trivial | reason recorded | any time | general (lead)
- next-gap | files this lane already owns | one more MVP gap or lane empty | after the list | general (lead)
- handoff | docs/ops/HANDOFF-mvp-tmpclean2-1031.md and this log | state line, push | last | general (lead)

Risks:

- Parallel /tmp/pfy-* writers: do not use /tmp. Scratch is this worktree tmp/ with TMPDIR set. FU16 must not depend on a clean host /tmp.
- Shared branch: no second worktree and no parallel implement agents. Lead runs phases in order so commits stay a fast-forward.
- origin/main moves: fetch before each item. Merge, never rebase.
- fix2 already landed some follow-ups: read that handoff before editing. Do not redo F1, F2/FU12, P2, G1.
- Host pressure and the heavy lock: targeted niced unittests only. No discover, no eval, no pregate until the end, and only if the runner is idle.
- Cross-lane files: if a fix needs a file another lane owns, record a request and skip. Do not edit it.

Progress:

- FU16 separate-process immunity | c875e7e | TMPDIR=$PWD/tmp/tmpclean nice -n 19 python3 -m unittest tests.test_pfylib_tmp_cleanup | 3 OK in 61.781s | pass
- state: DONE | tests: tests.test_pfylib_tmp_cleanup 3 OK in 61.781s | files: 2 | err: none
- FU1 ripgrep install step | 8203c43 | TMPDIR=$PWD/tmp nice -n 19 python3 -m unittest tests.test_workflow_image_pin | 20 OK in 13.612s | pass
- state: DONE | tests: tests.test_workflow_image_pin 20 OK in 13.612s | files: 4 | err: none
- FU3 version_of without bwrap | 5b32274 | TMPDIR=$PWD/tmp nice -n 19 python3 -m unittest tests.test_x_intake_smoke_149 | 29 OK in 2.792s | pass
- state: DONE | tests: tests.test_x_intake_smoke_149 29 OK in 2.792s | files: 1 | err: none
- FU4 PATH python3 yaml skip | 2abd8c9 | TMPDIR=$PWD/tmp nice -n 19 python3 -m unittest tests.test_workflow_image_pin | 21 OK in 6.800s | pass
- state: DONE | tests: tests.test_workflow_image_pin 21 OK in 6.800s | files: 1 | err: none
- FU5 lint helper without pregate | SHA5 | TMPDIR=$PWD/tmp nice -n 19 python3 -m unittest tests.test_workflow_image_pin | 21 OK in 0.561s | pass
- state: DONE | tests: tests.test_workflow_image_pin 21 OK in 0.561s | files: 1 | err: none
