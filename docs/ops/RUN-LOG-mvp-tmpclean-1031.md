# RUN-LOG mvp-tmpclean-1031

Branch `bot/mvp-tmpclean-1031`. Base `origin/bot/mvp-integrate-1031` `19c2710`. Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-tmpclean-1031`. No rebase, no force-push, no PR, no merge to main.

Overview: Make `tests/test_pfylib_tmp_cleanup.py` hermetic so a sibling process creating `/tmp/pfy-*` cannot fail it, keep a planted leak that must fail the checker, point hardcoded temp dirs in owned tests and helpers at `tempfile` defaults (`TMPDIR`), and run the suite once under the heavy lock with `TMPDIR=$PWD/tmp`.

Launch: 2026-10-31T21:15:31Z. Wall cap: 2026-11-01T05:15:31Z (8 hours), or 2026-11-02T02:00Z, whichever comes first. Stop new items at 2026-11-01T04:55:31Z to write the handoff. Host at launch: MemAvailable 62489136 kB (about 59.6 GiB), load 4.90, 32 cores (stop floor is load above 64 for 5 minutes, or MemAvailable under 16 GiB).

Phases:
- exits | `docs/ops/RUN-LOG-mvp-tmpclean-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-tmpclean-1031.md` | exit card and this plan are committed before the cleanup test changes | none | lead
- reproduce-red | no product code | the current cleanup test fails while this lane holds a `/tmp/pfy-hr-*` dir it created, then that dir is removed | exits | lead
- hermetic-test | `tests/test_pfylib_tmp_cleanup.py`, non-collected leaker helper under `tests/` | private child `TMPDIR` is empty after the real modules; a sibling `/tmp/pfy-hr-*` does not fail the test; a planted leaker makes the checker fail | reproduce-red | lead
- honor-tmpdir | owned `tests/*.py` and helpers that create `/tmp/pfy-*` while ignoring `TMPDIR` | those sites use `tempfile` defaults; sandbox binds that intentionally use `/tmp` are recorded and left alone | hermetic-test | lead, after a read-only audit
- full-suite | no new product scope | `TMPDIR=$PWD/tmp nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t .` | honor-tmpdir | lead
- further-gaps | owned files only | next MVP gap that fits, or lane empty | full-suite | lead
- handoff | `docs/ops/HANDOFF-mvp-tmpclean-1031.md`, this log | items, skips, evidence, fail/recover, cross-lane requests, gate, next step, pushed | further-gaps | lead

Risks: the cleanup test runs many modules and can take many minutes. Mitigation: one red run on the unchanged test, then one green run, no third retry of the same failure. A fix in `scripts/pfy_build_cloud.py`, `scripts/pfy_build_local.py`, `tests/test_pfy_build_local*.py`, catalog, or `sources/entries/` is out of ownership. Mitigation: cross-lane request, do not edit. Outer `bwrap` over `/tmp` would nest inside sandbox tests. Mitigation: do not wrap the child that way. Scratch stays in this worktree `tmp/` except the one interferer dir the drop-in requires on `/tmp`, which this lane creates and removes.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
================================================================
Goal (success criteria):     cleanup test stays green while a sibling creates /tmp/pfy-hr-*; a planted leaker fails that checker; owned hardcoded /tmp creators honor TMPDIR; full discover ran under the lock with TMPDIR=$PWD/tmp
1 Goal met:                  nice unittest of tests.test_pfylib_tmp_cleanup (sibling dir present, and the planted-leak case red on purpose) plus the locked discover
2 Turn cap:                  8 item attempts
3 Budget cap:                no cloud spend, no local model, no --local
4 Wall clock:                2026-11-01T05:15:31Z, or 2026-11-02T02:00Z, whichever first. Leave 20 minutes for the handoff.
5 No-progress:               same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:           user stop. No questions. Conservative default, logged, continue.
7 Error threshold:           3 consecutive same failure, then stop
8 External event:            stop rewriting a file if origin/main or the base already has the same hermetic checker
Loop type:                   goal
Human gate:                  no merge, no PR. Tester plus Reviewer if runtime code changes. Pregate plus Reviewer if the diff stays tests and docs. Pregate only if the GitHub runner is idle.
================================================================
```

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-tmpclean-1031.md` are the binding. Decision logged.

Drop-in exits (same loop, checked before every item):

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first.
2. Lane empty: no item left that fits this lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this change. Record them and skip that area. Do not stop the lane.

## Items

- exits | adb4168 | none (log only) | pushed
- reproduce-red | pending commit | nice -n 19 python3 -m unittest tests.test_pfylib_tmp_cleanup, TMPDIR=$PWD/tmp, sibling /tmp/pfy-hr-x created 2s after start | FAIL in 50.955s, AssertionError set difference was only '/tmp/pfy-hr-x'. Dir removed by this lane's cleanup. Tree stayed clean.

## Finish
