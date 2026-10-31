# Run log mvp-selfhost-1031

Lane: daily-use proof of `./pfy build`. Branch `bot/mvp-selfhost-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-selfhost-1031`. Base `origin/bot/mvp-cloud-1031`. No local model. No `--local`.

Launch: 2026-10-31T20:30:12Z (local 13:30 PDT).
Wall cap: 8 hours from launch, so 2026-11-01T04:30:12Z, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Leave 20 minutes to write the handoff. No new item after 2026-11-01T04:10:12Z.
Clock check before every item. Host at launch: MemAvailable about 64 GiB, 32 cores, load 3.46 (threshold 64).

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria): at least 8 real small backlog items driven through ./pfy build; keep only PASS plus human-accept commits; eval/selfhost-1031/REPORT.md and tests/test_selfhost_1031_log.py green
1 Goal met:             human accept plus the receipt checker (status PASS, subject matches) and the targeted test for that item
2 Turn cap:             one ./pfy build per item, runner retries default 2 (3 attempts); do not start a 9th item after 8 accepts unless the clock still has room and a real item remains
3 Budget cap:           cloud Grok only; a rate-limit receipt (exit 4) is BLOCKED and does not start --local
4 Wall clock:           2026-11-01T04:10:12Z for new items; handoff by 2026-11-01T04:30:12Z
5 No-progress:          the same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:      user stop. No question stops the loop
7 Error threshold:      3 consecutive build failures that are not a recorded skip, then stop
8 External event:       item already on origin/main or on this branch before the build
Loop type:              goal
Human gate:             this lane's human verdict before cherry-pick. No merge, no PR
```

Drop-in exits, same clock:

1. Wall cap: the clock above. On this exit, write the handoff and stop.
2. Lane empty: no item left that fits this lane and the drop-in rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this lane's change. Record them and skip that area. Do not stop the lane.

Skip items that need special hardware, a human decision (an open OQ), a secret, or Mark's hands. Log each skip with a reason. An item that needs an ADR is an OQ draft in the handoff, then a skip. Do not invent architecture.

Orchestrator clock of about 6 hours does not apply. This drop-in sets the 8 hour cap.

## Plan

Overview: Pick real small backlog items that are code, tests, or docs, and that no other MVP lane owns. For each one, clone this worktree under `tmp/`, run `./pfy build` with `--repo`, and cherry-pick only a commit that passed the runner review and a careful human read. Record every run under `eval/selfhost-1031/`. The runner treats any edit under `tests/` as tampering, so the behavior test is planted on this branch before the build and the build may change only non-test files.

Phases:

- loop-card | `docs/ops/RUN-LOG-mvp-selfhost-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-selfhost-1031.md`, `tests/test_selfhost_1031_log.py`, `eval/selfhost-1031/LOG.md` | exits are in this file before the first `./pfy build`; the checker fails a planted bad trailer in a temp repo | depends on nothing | general
- item-loop | product files the task names, `eval/selfhost-1031/<n>-<slug>/` | each item has a log row; PASS plus human-accept is cherry-picked, tested, and pushed | loop-card | general
- report | `eval/selfhost-1031/REPORT.md` | tried, PASS, human accept, SHAs, median wall, runner findings | item-loop | general
- handoff | `docs/ops/HANDOFF-mvp-selfhost-1031.md`, final `state:` line in this log | committed and pushed, no merge | report | general

Risks:

- The runner rejects new or edited test files (`tests-tampered`). Mitigation: plant the behavior test in a commit before the clone. If the build edits a test, do not cherry-pick and do not hand-fix.
- mvp-sixtask-1031 is already spending Grok on MVP-2 tasks t1 through t6 and does not merge those product diffs. Mitigation: do not start those six while that lane is still writing their receipts. Land other gaps first.
- A clone that shares Mark's git dir would touch his checkout. Mitigation: `git clone --no-hardlinks` into this worktree's `tmp/`. The runner adds its worktree inside that clone.
- Full `unittest discover` is a heavy job and can be red for unrelated reasons. Mitigation: pass a targeted `--test-cmd`. Run that same command niced after a cherry-pick.
- Default `--base` is `origin/main`, which is behind this branch. Mitigation: `--base HEAD` on the clone so the cherry-pick applies onto this branch.
- Receipts can contain tokens. Mitigation: runner redact plus a scan before every commit. Raw values are not printed.
- Grok rate limit (exit 4) stops the item. Mitigation: one build at a time. Record BLOCKED. Do not start `--local`.

## Item log

Format: `item | commit | tests | result`

- loop-card | 5d0575b | nice python3 -m unittest tests.test_selfhost_1031_log (2 OK) | PASS
- relative receipt dir | 00dbdd9 | nice python3 -m unittest tests.test_smoke_receipt_absolute (1 OK, was red before the fix) | PASS human-accept

Skips logged before the first build (not three in a row of attempted items; these are out of scope up front):

- T-0091 voice: shelved, needs Mark
- T-0094 local TTS: local model and shelved voice
- T-0095 Pipecat catalog row: catalog work
- T-0070 new scorer: plan D10 excludes a new scorer tonight
- T-0074 eval-auto: needs a local model
- T-0081 OpenCode-in-cage: docker cage, not a small daily edit
- T-0064 EBUSY: ops doc says no code change; copy-import is the mitigation
- T-0043 write-guard mcp-host: parked
- T-0062 Laguna: hardware
- T-0046 re-evaluate AgenC: ADR-0010 already rejects it; human decision
- T-0002 aggregate synthesis: catalog-scale, not a small edit
- T-0016 colibri lab: OQ-0008 and hardware
- T-0005 integration stages: OQ-0003, human, catalog
- T-0124 OpenCode attach fold: not small, and dogfood lane is in enterable code
- G8 pfy-build operator card: mvp-surface-1031 owns that card
- MVP-2 t1-t6 right now: mvp-sixtask-1031 is running those Grok calls; do not double-spend until that lane's receipt for the task exists and this queue still needs items
