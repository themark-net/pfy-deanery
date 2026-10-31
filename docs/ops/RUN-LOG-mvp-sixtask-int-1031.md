# Run log mvp-sixtask-int-1031

Lane: re-measure the MVP-2 six-task bar on the integration tip. Branch `bot/mvp-sixtask-int-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-sixtask-int-1031`. Base `origin/bot/mvp-integrate-1031` at `0c3f133`. No local model. No `--local`. Do not edit the cloud runner.

Launch: 2026-10-31T22:38:30Z.
Wall cap: 8 hours from launch, so 2026-11-01T06:38:30Z, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Leave 20 minutes to write the handoff. No new item after 2026-11-01T06:18:30Z.
Clock check before every item. Host at launch: MemAvailable about 57 GiB, 32 cores, load about 3.7.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     two passes, 6/6 runner PASS, 6/6 review accept, human accept of each diff, or a NO-GO report that names the cause
1 Goal met:                  eval/mvp-1031/sixtask-int/REPORT.md verdict line, checker green against receipts
2 Turn cap:                  20 recorded items (harness, 12 builds, report, findings, handoff). Stop at the cap.
3 Budget cap:                at most 26 cloud ./pfy build invocations. No --local. No third pass unless a pass is missing.
4 Wall clock:                2026-11-01T06:18:30Z for new items. Handoff by 2026-11-01T06:38:30Z.
5 No-progress:               same receipt reason and same diff hash twice on one retried task, or 3 items skipped in a row
6 Human interrupt:           user stop. Do not ask. Conservative choice goes in the decisions file.
7 Error threshold:           3 consecutive harness or auth failures (a measured FAIL is a result, not this counter)
8 External event:            n/a until the handoff. Do not merge.
Loop type:                   goal
Human gate:                  no merge, no PR. Human accept in the report is this lane's diff read, not a ship approval.
```

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-sixtask-int-1031.md` are the binding.

## Exits (drop-in, written before the trial)

1. Wall cap: the clock above. On this exit, write the handoff and stop.
2. Lane empty: no item left that fits this lane and the drop-in rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this lane's change. Record them and skip that area. Do not stop the lane.

Skip items that need special hardware, a human decision (an open OQ), a secret, or Mark's hands. Log each skip with a reason. An item that needs an ADR is an OQ draft in the handoff, then a skip. Do not invent architecture.

Orchestrator clock of about 6 hours does not apply. This drop-in sets the 8 hour cap.

## Plan

Overview: Re-run MVP-2 tasks t1 through t6 twice through `./pfy build "<task>"` on this integration tip, review on, real grok, one throwaway clone per task at `997d89264495861a178713ccf7d4447ea828afc4`. Pass `--writable-test` only for t4 (`tests/test_x_intake_smoke_112_114.py`) and t5 (`tests/test_x_intake_smoke_117_118.py`, `tests/test_x_intake_smoke_119_121.py`). Write receipts under `eval/mvp-1031/sixtask-int/receipts/`, then `REPORT.md` with one row per task and pass and a GO or NO-GO line. Do not edit `scripts/pfy_build_cloud.py`. A remaining runner bug is a findings file, not a patch in this lane.

Phases:

- loop-card | `docs/ops/RUN-LOG-mvp-sixtask-int-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-sixtask-int-1031.md` | exits and phases are in this file before any trial command | depends on nothing | general
- report-checker | `eval/mvp-1031/sixtask-int/run_task.py`, `eval/mvp-1031/sixtask-int/check_report.py`, `tests/test_mvp_1031_sixtask_int_report.py` | targeted unittest green; a planted mismatch fails the checker; argv refuses `--local` | loop-card | general
- pass1 | `eval/mvp-1031/sixtask-int/receipts/pass1/**` | six cloud builds recorded with receipt, diff, gate rerun, review | report-checker | general
- pass2 | `eval/mvp-1031/sixtask-int/receipts/pass2/**` | second six, fresh clones, same flags | pass1 | general
- report | `eval/mvp-1031/sixtask-int/REPORT.md` and `findings/` only if NO-GO | checker accepts the live report; GO or NO-GO with the cause | pass1 and pass2 | general
- handoff | `docs/ops/HANDOFF-mvp-sixtask-int-1031.md`, final `state:` line in this log | committed and pushed, no merge | report | general

Risks:

- Grok rate limit stops a task with no commit. Mitigation: one build at a time. On `rate-limit`, wait 10 minutes and retry that task once. Do not pass `--local`. Two rate-limits on the same task fire the no-progress exit.
- t4 and t5 must edit named tests. Mitigation: pass only those paths to `--writable-test`. The planted acceptance test stays hashed. If the receipt is still `tests-tampered`, that is a finding. Do not edit the runner.
- A worktree add on Mark's main git dir would touch his checkout. Mitigation: `git clone --no-hardlinks` into `tmp/sixtask-int-seed`, then each task clones that seed. Nothing in a target clone is pushed.
- Receipts can contain tokens. Mitigation: redact before write, scan before commit, never print a match.
- Other lanes share the host. Mitigation: no full unittest discover, no pregate unless the finish rule says the runner is idle. Targeted tests only for the new checker.

## Item log

Format: `item | commit | tests | result`

- loop-card | 627fd6d | docs only | PASS
- report-checker | cc3b275 | nice python3 -m unittest tests.test_mvp_1031_sixtask_int_report (11 tests, 1 skipped, OK) | PASS
- pass1 t1 | 6f1c568 | ./pfy build exit 0 wall 163.4s attempts 1 review accept gate_rerun 0 human accept | PASS
- pass1 t2 | f573cf3 | ./pfy build exit 0 wall 65.7s attempts 1 review accept gate_rerun 0 human accept | PASS
- pass1 t3 | 39cc194 | ./pfy build exit 0 wall 366.3s attempts 1 review accept gate_rerun 0 human accept | PASS
- pass1 t4 | 5c14473 | ./pfy build exit 0 wall 337.8s attempts 1 review accept gate_rerun 0 human accept writable tests/test_x_intake_smoke_112_114.py | PASS
- pass1 t5 | 5df0448 | ./pfy build exit 0 wall 215.3s attempts 1 review accept gate_rerun 0 human accept writable tests/test_x_intake_smoke_117_118.py, tests/test_x_intake_smoke_119_121.py | PASS
- pass1 t6 | d12ba6a | ./pfy build exit 0 wall 95.3s attempts 1 review accept gate_rerun 0 human accept | PASS
- pass2 t1 | 53b7e22 | ./pfy build exit 0 wall 150.5s attempts 1 review accept gate_rerun 0 human accept | PASS
- pass2 t2 | da98b97 | ./pfy build exit 0 wall 58.4s attempts 1 review accept gate_rerun 0 human accept | PASS
- pass2 t3 | ef66025 | ./pfy build exit 0 wall 208.1s attempts 1 review accept gate_rerun 0 human accept | PASS
- pass2 t4 | 1d1507f | ./pfy build exit 0 wall 349.0s attempts 1 review accept gate_rerun 0 human accept writable tests/test_x_intake_smoke_112_114.py | PASS
- pass2 t5 | a3aa54e | ./pfy build exit 0 wall 174.3s attempts 1 review accept gate_rerun 0 human accept writable tests/test_x_intake_smoke_117_118.py, tests/test_x_intake_smoke_119_121.py | PASS
- pass2 t6 | 399408a | ./pfy build exit 0 wall 76.0s attempts 1 review accept gate_rerun 0 human accept | PASS
- report | af53460 | nice python3 -m unittest tests.test_mvp_1031_sixtask_int_report (12 tests OK) and check_report.py CHECK_OK | PASS, VERDICT GO, pass1 1243.8s, pass2 1016.3s

state: DONE | pass1 6/6 and pass2 6/6 runner PASS, review accept, and human accept | VERDICT GO | lane empty after the report | pregate not run: operator owns it and Runner.Worker was live
