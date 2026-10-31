# RUN-LOG mvp-preflight-1031

Branch `bot/mvp-preflight-1031`. Base `origin/main` at `85c53dc`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-preflight-1031`. Launch `2026-10-31T19:54:16Z`. No rebase, no force-push, no PR, no merge to main.

Overview: Add a pure function that classifies a failed cloud grok exit. This branch does not edit the build runner. The cloud lane keeps its own inline copy so it can test alone. Integration, or round 2 `mvp-dedupe-1031`, is what connects them. After that function is green, take only further MVP gaps from `origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md` that fit this lane's owned files.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     classify_cloud_failure(rc, stdout, stderr) returns "rate-limit" | "unauthenticated" | "other" by the ordered rules, and python3 -m unittest tests.test_build_preflight passes
1 Goal met:                  tests.test_build_preflight is green, and no further plan gap fits the owned files
2 Turn cap:                  8 items
3 Budget cap:                no local model, no spend, no cloud API beyond this session
4 Wall clock:                8h from launch (2026-11-01T03:54:16Z) or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Leave 20 minutes (stop new items at 2026-11-01T03:34:16Z) to write the handoff
5 No-progress:               the same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:           user stop. Do not ask questions. Push only this bot/ branch
7 Error threshold:           3 consecutive same failures, then stop. Drop-in no-progress is also 2 identical failures
8 External event:            stop if origin/main already has this contract. Otherwise n/a (do not merge)
Loop type:                   goal
Human gate:                  no merge and no PR. Runtime change needs Tester plus Reviewer later
```

Drop-in exits, checked before every item:

1. Wall cap: the clock above.
2. Lane empty: no item left that fits the lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64 on this 32-core host) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this change. Record them and skip that area. Do not stop the lane for that alone.

Host at launch: MemAvailable 66911448 kB (about 63.8 GiB), load 3.10, cores 32. Under the pressure line.

Phases:
- exits | `docs/ops/RUN-LOG-mvp-preflight-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-preflight-1031.md` | exit card and plan are in this log before any product code | none | general
- classify | `pfylib/build_preflight.py`, `tests/test_build_preflight.py` | the contract holds and `python3 -m unittest tests.test_build_preflight` passes | exits | general
- follow-on | owned files only | the next plan gap that fits these files, or a recorded skip | classify | general
- handoff | `docs/ops/HANDOFF-mvp-preflight-1031.md`, this log | handoff written, final `state:` line, both pushed | all prior | lead

Risks: a second classifier copy can drift from the cloud lane. Mitigation: implement the drop-in phrase list in order and do not edit `scripts/`. A return value can echo grok text. Mitigation: tests require the enum only and reject fixture secret markers in the return. A commit can capture a real credential. Mitigation: fixture markers only, and never read `~/.grok/auth.json`.

## Base check

`origin/main` (`85c53dc`) has no `pfylib/build_preflight.py`. A search of `origin/main` and `origin/bot/mvp-cloud-1031` found no `classify_cloud_failure`. `origin/bot/mvp-integrate-1031` does not exist. The contract is not already done, so the function is new work, not a test-only extension.

Owned files: `pfylib/build_preflight.py`, `tests/test_build_preflight.py`, this log, `docs/ops/AUTONOMOUS-DECISIONS-mvp-preflight-1031.md`, `docs/ops/HANDOFF-mvp-preflight-1031.md`.

## Decisions

See `docs/ops/AUTONOMOUS-DECISIONS-mvp-preflight-1031.md`.

## Items

## State

state: RUNNING | tests: none yet | files: run log and decisions | err: none
