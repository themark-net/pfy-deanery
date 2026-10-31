# RUN-LOG mvp-surface-1031

Branch `bot/mvp-surface-1031`. Base `origin/main` `85c53dc`. Worktree `/home/mark/DEVELOP/pfy-mentat/tmp/mvp-surface-1031`. No rebase, no force-push, no PR, no merge to main.

Overview: Write the operator card for the daily command `./pfy build "<task>"` (cloud Grok, review on, nothing pushed) and a contract test that fails when either card drops a required fact or links a file that is not on this branch. No product code. `scripts/pfy` and `docs/modules/README.md` stay untouched.

Launch: 2026-10-31T19:50:33Z. Wall cap: 2026-11-01T03:50:33Z (8 hours), or 2026-11-02T02:00Z, whichever comes first. Stop new items 20 minutes before the cap to write the handoff. Host at launch: MemAvailable about 63.6 GiB, load 3.23, 32 cores.

Phases:
- exits | `docs/ops/RUN-LOG-mvp-surface-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-surface-1031.md` | exit card and phase plan are in this log before the docs | none | lead
- operator card | `docs/ops/pfy-build-daily.md`, `docs/modules/pfy-build.md` | both docs agree on the drop-in contract | exits | lead
- contract test | `tests/test_pfy_build_docs.py` | `python3 -m unittest tests.test_pfy_build_docs` passes and would fail if a required sentence or a resolved link is missing | operator card | lead
- further gaps | owned files only | next plan gap that fits, or lane empty | contract test | lead
- handoff | `docs/ops/HANDOFF-mvp-surface-1031.md`, this log | items, skips, evidence, gate, next step, pushed | further gaps | lead

Risks: a markdown link to `scripts/pfy_build_cloud.py` would dangle (file is not on this branch). Mitigation: inline code only, and the contract test rejects a relative link whose target is missing. The runner is not merged yet, so the card follows the plan failure table instead of a second invented contract. Parallel lanes own `scripts/pfy` and `docs/modules/README.md`. Mitigation: do not edit them. Record the README row as a cross-lane request.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
================================================================
Goal (success criteria):     docs/ops/pfy-build-daily.md and docs/modules/pfy-build.md exist, agree, and tests.test_pfy_build_docs passes
1 Goal met:                  python3 -m unittest tests.test_pfy_build_docs (reads the two docs; does not start a build)
2 Turn cap:                  8 item attempts
3 Budget cap:                no cloud spend, no local model, docs and one test only
4 Wall clock:                2026-11-01T03:50:33Z, or 2026-11-02T02:00Z, whichever first. Leave 20 minutes for the handoff.
5 No-progress:               same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:           user stop. No questions. Conservative default, logged, continue.
7 Error threshold:           3 consecutive same failure, then stop
8 External event:            stop if origin/main already contains both cards and a passing test (do not rewrite landed work)
Loop type:                   goal
Human gate:                  no merge, no PR. Gate for this lane is pregate plus Reviewer. Pregate only if the GitHub runner is idle.
================================================================
```

Drop-in exits (same loop, checked before every item):

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first.
2. Lane empty: no item left that fits this lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this change. Record them and skip that area. Do not stop the lane.

## Items

- exits | a2302df | none (log only) | pushed
- operator card | c73ef00 | link targets and contract strings checked before commit; unittest is the next item | pushed
- contract test | this commit | nice -n 19 python3 -m unittest tests.test_pfy_build_docs : 5 tests OK | green
