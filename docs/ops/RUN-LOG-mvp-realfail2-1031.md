# Run log mvp-realfail2-1031

Lane: E2E coverage of the DoD cases lane mvp-realfail-1031 did not hit, and re-verification of its four FINDINGs. Branch `bot/mvp-realfail2-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-realfail2-1031`. Base `origin/bot/mvp-cloudfix-1031`.

Launch: 2026-10-31T21:23:08Z.
Wall cap: 8 hours from launch, so 2026-11-01T05:23:08Z, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. The 8 hour cap binds first. Leave 20 minutes to write the handoff. No new item after 2026-11-01T05:03:08Z.
Clock check before every item. Host at launch: MemAvailable about 60 GiB, 32 cores, load about 3.7. Pressure line is 16 GiB or load over 64 for 5 minutes.

Cloud Grok only. Never `--local` on a real run. Scratch and `TMPDIR` stay under this worktree's `tmp/`.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     eval/mvp-1031/realfail2/REPORT.md has one row per re-check and per new DoD case, each row matches its receipt or records that the runner wrote none, tests/test_mvp_1031_realfail2_receipts.py is green, and a planted bad receipt fails. New misses are cross-lane requests, not runner edits.
1 Goal met:                  nice -n 19 python3 -m unittest tests.test_mvp_1031_realfail2_receipts is OK, and every non-pending row has meta plus the receipt the runner wrote.
2 Turn cap:                  16 case rows plus the handoff. The agent-loops default of 8 is not the cap. The drop-in says keep taking the next gap until an exit fires.
3 Budget cap:                Cloud Grok only for rows whose original was real or whose clause needs a live model. No local model. No --local. No second try after the same failure with no new fact.
4 Wall clock:                2026-11-01T05:23:08Z, or 2026-11-02T02:00Z, whichever first. Handoff starts 20 minutes earlier (2026-11-01T05:03:08Z).
5 No-progress:               the same failure twice with no new information, or 3 items skipped in a row.
6 Human interrupt:           user says stop. Do not ask questions. Do not merge to main. Push of this bot/ branch is pre-authorized.
7 Error threshold:           3 consecutive same failures, then stop. A red base test is recorded and that area is skipped. It does not by itself stop the lane.
8 External event:            stop a row if origin/main or a newer origin/bot/mvp-cloudfix-1031 already closed it with a committed receipt. git fetch before every item.
Loop type:                   goal
Human gate:                  no merge, no PR, no tag. Pregate plus Reviewer at handoff (docs, eval, and test only, unless a later gap forces a runtime edit this lane does not own).
```

Orchestrator clock of about 6 hours does not apply. This drop-in sets the 8 hour cap.

## Exits (drop-in, written before case runs)

1. Wall cap: the clock above. On this exit, write the handoff and stop.
2. Lane empty: no item left that fits this lane and the drop-in rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this lane's change. Record them and skip that area. Do not stop the lane.

Skip items that need special hardware, a human decision (an open OQ), a secret, or Mark's hands. Log each skip with a reason. An item that needs an ADR is an OQ draft in the handoff, then a skip. Do not invent architecture.

## Plan

Overview: Re-run the four mvp-realfail-1031 FINDINGs on the newest cloud runner and add the DoD rows that lane did not execute (review retry then accept, scope mismatch, missing base, dry-run, usage, `-p`, keep-worktree, protected paths, two concurrent builds, a 4-file review). Evidence lives in `eval/mvp-1031/realfail2/`. This lane does not edit the runner.

Phases:

- loop-card | `docs/ops/RUN-LOG-mvp-realfail2-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-realfail2-1031.md` | exits and phases are in this file before any case run | depends on nothing | general
- scaffold | `eval/mvp-1031/realfail2/**`, `tests/test_mvp_1031_realfail2_receipts.py` | pending report, driver, receipt test green | loop-card | general
- recheck-four | `eval/mvp-1031/realfail2/{sigkill-reap,review-reject,auth-failure,redaction}/` | each row is fixed or FINDING with a receipt | scaffold | general
- e2e-rest | the other case dirs under `eval/mvp-1031/realfail2/` | each listed DoD row has a receipt or an explicit none, and the test is green | recheck-four | general
- handoff | `docs/ops/HANDOFF-mvp-realfail2-1031.md`, final `state:` line | committed and pushed, no merge | e2e-rest | general

One workstream. The report, the test, and this branch are shared, so the cases run in order. No second editor. No extra worktree.

Risks:

- A real grok call can rate-limit or refuse a dangerous fixture. Mitigation: one throwaway clone per case under `tmp/targets/`, `--timeout` on each call, and a wrapper plant only inside that clone when the model cannot be the precondition. Never point `./pfy build` at Mark's checkout.
- Reap or a leftover grok could hit a process this lane did not start. Mitigation: signal only pids this lane started, and only after `/proc` cmdline contains that case's clone path.
- Parallel cloudfix commits land mid-run. Mitigation: `git fetch origin && git merge --no-edit origin/bot/mvp-cloudfix-1031` before every item.
- `-p` copies credential bytes into an isolated home on the clone and may write the jev skill into the harness home. Mitigation: `--cwd` is the clone, delete `grok-home` after the run without printing it, and do not commit the clone. If the pfy worktree gets dirty outside owned files, restore those paths and record the paths only.
- Receipts could capture a token. Mitigation: scan for secret-like strings before commit. Do not read `~/.grok/auth.json`.

## Item log

Format: `item | commit | tests | result`

- loop-card | a480afa | nice -n 19 python3 -m unittest tests.test_mvp_1031_realfail2_receipts | PASS, 4 tests OK. Pending report, no case run yet.
- usage | 34d8c98 | tests.test_mvp_1031_realfail2_receipts | PASS, 4 tests OK. Exit 2, no receipt, daily command and both pointers present.
- dry-run | 2f14df0 | tests.test_mvp_1031_realfail2_receipts | PASS. Exit 0, receipt DRY-RUN, shim grok_calls 0, no branch.
