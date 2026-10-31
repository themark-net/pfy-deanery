# Run log: mvp-backlog-burn-1031

Lane `bot/mvp-backlog-burn-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-backlog-burn-1031`. Base `origin/bot/mvp-integrate-1031` at `0c3f133`, plus the drop-in commit `56ea234`. Cloud Grok only. No `--local`. No `scripts/pregate.sh`.

Started 2026-10-31T22:38:40Z. Wall cap 2026-11-01T06:38:40Z (8 hours). Stop new items by 2026-11-01T06:18:40Z so the handoff has 20 minutes. Sunday 2026-11-02T02:00Z is later, so the 8 hour cap wins. Host at start: 32 cores, load 3.13, MemAvailable about 57 GiB.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria): six real backlog items, each a cloud ./pfy build whose receipt is PASS and review accept, a human accept of the diff, a cherry-pick, a green targeted test, and a push. Report at eval/mvp-1031/backlog-burn/REPORT.md.
1 Goal met:             receipt status PASS, review accept, human accept, targeted test green, SHA on this branch
2 Turn cap:             8 items attempted (the six plus two more only if the clock still has room). One ./pfy build per item. Runner retries stay at 2 (3 attempts). Do not start a 9th item.
3 Budget cap:           cloud Grok only. Exit 4 (rate-limit) is BLOCKED for that item. Do not start --local.
4 Wall clock:           new items stop at 2026-11-01T06:18:40Z. Hard stop 2026-11-01T06:38:40Z.
5 No-progress:          the same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:      user stop. No question stops the loop.
7 Error threshold:      3 consecutive build failures that are not a recorded skip, then stop
8 External event:       item already on origin/main or on this branch before the build
Loop type:              goal
Human gate:             this lane reads the diff before cherry-pick. No merge, no PR, no tag.
```

Drop-in exits, same clock:

1. Wall cap: the clock above. Write the handoff and stop.
2. Lane empty: no item left that fits this lane and these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 (2x 32 cores) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this lane's change. Record them and skip that area. Do not stop the lane.

Skip items that need special hardware, a human decision (an open OQ), a secret, or Mark's hands. An item that needs an ADR is an OQ draft in the handoff, then a skip. Do not invent architecture.

The orchestrator clock of about 6 hours does not apply. This drop-in sets the 8 hour cap.

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-backlog-burn-1031.md` are the binding. `prefer-behavior-and-fail-recover-tests` is on disk and applies to every test.

## Plan

Overview: Pick small real backlog items that are not already done and that no live wave-4 lane owns. For each one, commit a behavior test that fails while the bug is present, clone this worktree under `tmp/`, run `./pfy build` with `--repo` and a targeted `--test-cmd`, and cherry-pick only a commit that passed the runner review and a careful read of the diff. Push after the item is green. Record every run in `eval/mvp-1031/backlog-burn/REPORT.md`.

Phases:

- loop-card | `docs/ops/RUN-LOG-mvp-backlog-burn-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-backlog-burn-1031.md` | exits are in this file before the first `./pfy build` | depends on nothing | general
- item-01-enterable | `scripts/pfy_enterable_162.py`, `tests/test_enterable_not_ok.py` | not-ok launch drops stale enterable and session steps; targeted test green; pushed | loop-card | general
- item-02-apply | `scripts/catalog_stage_eval.py`, `tests/test_catalog_stage_eval.py` | `--apply` on a temp copy keeps live receipt evidence, does not rewind `last_updated`, and does not lower ceiling or replace potential | item-01 | general
- item-03-entry-149 | `sources/entries/149-mempalace.md`, a new test under `tests/` | the entry's published test count equals the number of test methods in `tests/test_x_intake_smoke_149.py` | item-02 | general
- item-04-hermes-status | `docs/PENDING-HANDOFF.md`, a new test under `tests/` | the 2026-10-19 Hermes bullet matches `docs/eval/HERMES-EVAL-HANDOFF.md` (landed, not still going to land) | item-03 | general
- item-05-and-06 | next verified backlog gaps that fit the file rules | same receipt, review, human accept, test, push bar | item-04 | general
- report | `eval/mvp-1031/backlog-burn/REPORT.md` | one row per item: receipt status, attempts, wall seconds, verdict, landed SHA | each item | general
- handoff | `docs/ops/HANDOFF-mvp-backlog-burn-1031.md`, final `state:` line in this log | committed and pushed, no merge | report | general

Risks:

- The runner rejects edits to existing test files (`tests-tampered`). Mitigation: plant the behavior test in a local commit before the clone. Do not pass `--writable-test` unless the task must edit an existing test. A new test file is not in the base snapshot.
- Default `--test-cmd` is full `unittest discover`, which is a heavy job and can be red for unrelated reasons. Mitigation: pass a targeted `--test-cmd`. Run that same command niced after a cherry-pick.
- Default `--base` is `origin/main`, which is behind this branch. Mitigation: `--base HEAD` on the clone.
- A clone that shares git objects via hardlinks can touch another checkout. Mitigation: `git clone --no-hardlinks` into this worktree's `tmp/`.
- Wave-4 lanes own the cloud runner, the local runner, `scripts/pfy`, preflight, CI workflows, `pfylib/attach.py`, `tests/test_attach.py`, `docs/ops/pfy-build-daily.md`, `docs/modules/`, and `eval/mvp-1031/` outside `backlog-burn/`. Mitigation: do not edit those paths. Record a cross-lane request.
- mvp-selfhost-1031 is landing x-intake tree signatures and `examples/x-intake-local/smoke.py`. Mitigation: do not edit those files.
- mvp-dogfood-fix-1031 owns dogfood friction on `scripts/pfy` and pregate. Mitigation: do not take those items.
- Grok rate limit (exit 4). Mitigation: one build at a time. Record BLOCKED. Do not start `--local`.
- Receipts can contain tokens. Mitigation: runner redaction plus a scan before every commit. Raw values are not printed.
- A red planted test must not be the only commit on origin. Mitigation: push the exit card first. Push the test commit only together with the green fix, or drop the unpushed test commit if the build is rejected.

## Item queue

1. `arm_launch_env_session` not-ok returns before storing the stripped `next_steps`. Integrate handoff next step. Test is new `tests/test_enterable_not_ok.py`, not `tests/test_attach.py`.
2. `scripts/catalog_stage_eval.py --apply` drops live ATG and harness2 receipt evidence, rewinds `last_updated` to 2026-09-25, lowers the ATG tier ceiling, and replaces `measured-probe` with the older handoff potential. Backlog-catalog handoff. The behavior is specified there. Not a new ADR.
3. `sources/entries/149-mempalace.md` still says 18 stub tests. The module has more `test_` methods. HANDOFF-x-intake-149-b2 known gap. The dated automation handoff stays as the record of that day.
4. `docs/PENDING-HANDOFF.md` 2026-10-19 still says the Hermes branch lands on main. `docs/eval/HERMES-EVAL-HANDOFF.md` says it landed. Backlog-catalog handoff next step.
5. Next verified gap after item 4, chosen only if it fits the file rules.
6. Next verified gap after item 5.

Skips logged before the first build:

- T-0005 stage promotion: OQ-0003, human stage letter. The `--apply` data loss is item 2. The promotion is not.
- T-0091 voice: shelved.
- T-0094 local TTS: local model and shelved voice.
- T-0110 TODO row split: dogfood run 03 already named it. Leave it to mvp-dogfood-fix-1031.
- T-0062 Laguna and issue 25: hardware and a local model.
- T-0016 colibri lab: OQ-0008 and hardware.
- T-0081 OpenCode-in-cage: docker.
- T-0074 `make eval-auto`: local model.
- T-0070 new scorer: no next scorer is named. Do not invent one.
- T-0043 write-guard mcp-host: parked.
- T-0064 auth EBUSY: parked env work.
- T-0046 re-evaluate AgenC: ADR-0010 already rejects it.
- T-0124 full fold into `pfylib/attach.py`: not small, and that file is owned by the followups lane. Item 1 is only the not-ok assignment in the shim.
- ADR-0017 file: missing ADR. OQ draft already in the backlog handoff. Do not write the ADR here.
- runx receipt schema: needs an ADR. Skip.
- Dogfood pregate lock, pregate latest summary, board loader copies, splice socket close: other lanes own `scripts/pregate.sh` and `scripts/pfy_build_local.py`.
- Help-text test and local-bench TMPDIR: intfix already merged those fixes onto the base.
- x-intake tree signatures and `examples/x-intake-local/smoke.py`: mvp-selfhost-1031 is landing those now.
- Entry 149 date line and `smoke_149.py`: backlog handoff left those to Run A. Item 3 edits only the published count in the entry plus a new test.

## Item log

Format: `item | commit | tests | result`

- loop-card | d3d6377 | docs only, no product tests | PASS pushed
- enterable not-ok | c354d9c (cloud 9b7eafdade3b09d473cf7b0805bd042e99561f36) | nice python3 -m unittest tests.test_enterable_not_ok (2 OK) | PASS human-accept wall 53s attempts 1
- catalog apply | 5f7ce36 (cloud a3f267a4e514f014981aa0803778518615c081bc) | nice python3 -m unittest tests.test_catalog_stage_eval (4 OK) | PASS human-accept wall 784s attempts 2
- entry 149 count | 42fc4e1 (cloud 3faeaa2e0a48a8e65aeeda9d57bea304511c02bd) | nice python3 -m unittest tests.test_entry_149_count (1 OK) | PASS human-accept wall 28s attempts 1
- hermes landed | 6e0ae87 (cloud 954dc026b9a7be35172e6481ca27cf6f0b5513b2) | nice python3 -m unittest tests.test_hermes_landed_status (1 OK) | PASS human-accept wall 37s attempts 1
- ATG pin and score | dfe915f (cloud 84c2cbf4068430ec8915a426b5d4824401f05a66) | nice python3 -m unittest tests.test_catalog_stage_pin_score tests.test_catalog_stage_eval (5 OK) | PASS human-accept wall 116s attempts 1

## Checks

Host before each item: MemAvailable and load. Skip the item area on a red base test. Do not stop the lane for a red base.
