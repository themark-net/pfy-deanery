# Run log mvp-sixtask-1031

Lane: extra cloud six-task trial. Branch `bot/mvp-sixtask-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-sixtask-1031`. Base `origin/bot/mvp-cloud-1031`. No local model. No `--local`.

Launch: 2026-10-31T20:16:38Z (pid of this session, local 13:16 PDT).
Wall cap: 8 hours from launch, so 2026-11-01T04:16:38Z, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z), whichever comes first. Leave 20 minutes to write the handoff. No new item after 2026-11-01T03:56:38Z.
Clock check before every item. Host at launch: MemAvailable about 64 GiB, 32 cores, load under 4.

## Exits (written before the trial)

1. Wall cap: the clock above. On this exit, write the handoff and stop.
2. Lane empty: no item left that fits this lane and the drop-in rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped. Record and stop.
4. Host pressure: MemAvailable under 16 GiB, or load over 2x cores (64) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this lane's change. Record them and skip that area. Do not stop the lane.

Skip items that need special hardware, a human decision (an open OQ), a secret, or Mark's hands. Log each skip with a reason. An item that needs an ADR is an OQ draft in the handoff, then a skip. Do not invent architecture.

Orchestrator clock of about 6 hours does not apply. This drop-in sets the 8 hour cap.

## Plan

Overview: Re-run MVP-2 tasks t1 through t6 through `./pfy build "<task>"` with review on, real grok, one throwaway clone per task at `997d89264495861a178713ccf7d4447ea828afc4`. Write receipts, diffs, gate reruns, human verdicts, and `eval/mvp-1031/sixtask/REPORT.md` with GO or NO-GO against the MVP-2 cloud baseline (6/6 gate, 6/6 accept, 584 s) and MVP-3 local (5/6 gate, 5/6 loop, 4/6 human, 3860 s). The cloud runner files stay untouched. A runner bug is a finding plus a cross-lane request.

Phases:

- loop-card | `docs/ops/RUN-LOG-mvp-sixtask-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-sixtask-1031.md` | exits and phases are in this file before any trial command | depends on nothing | general
- report-checker | `eval/mvp-1031/sixtask/check_report.py`, `eval/mvp-1031/sixtask/run_task.py`, `tests/test_mvp_1031_sixtask_report.py` | `python3 -m unittest tests.test_mvp_1031_sixtask_report` green; a planted mismatch in a temp dir fails the checker | loop-card | general
- t1 | `eval/mvp-1031/sixtask/t1-smolvm-stderr-first/**` | command, wall, exit, receipt, diff, attempts, gate rerun, review, human verdict | report-checker, merge `origin/bot/mvp-cloud-1031` first | general
- t2 | `eval/mvp-1031/sixtask/t2-tree-sig-119/**` | same evidence | merge cloud base first | general
- t3 | `eval/mvp-1031/sixtask/t3-daemon-stop-fail/**` | same evidence | merge cloud base first | general
- t4 | `eval/mvp-1031/sixtask/t4-timeout-substep/**` | same evidence | merge cloud base first | general
- t5 | `eval/mvp-1031/sixtask/t5-receipts-outside-repo/**` | same evidence | merge cloud base first | general
- t6 | `eval/mvp-1031/sixtask/t6-tree-sig-three/**` | same evidence | merge cloud base first | general
- report | `eval/mvp-1031/sixtask/REPORT.md` | checker accepts the live report; GO or NO-GO stated with reasons | t1 through t6 | general
- variance | `eval/mvp-1031/sixtask/variance/**` | second full pass measured, or skipped because the clock cannot hold it | report, time left | general
- retries0 | `eval/mvp-1031/sixtask/retries0/**` | one pass with `--retries 0` (review still on), or skipped because the clock cannot hold it | variance or time left | general
- handoff | `docs/ops/HANDOFF-mvp-sixtask-1031.md`, final `state:` line in this log | committed and pushed, no merge | earlier phases | general

Risks:

- Grok rate limit (exit 4) stops a task with no branch. Mitigation: run tasks one at a time, never six grok builds at once. Record BLOCKED and do not fall through to `--local`.
- t4 and t5 must edit files under `tests/`. The cloud runner's `tests_tampered` has no `--writable-test` (the local runner does). Mitigation: still run them. If the receipt says `tests-tampered`, that is a finding for mvp-cloud-1031, with command, exit, receipt excerpt, and a suggested patch under this eval dir. Do not edit the runner.
- A clone or worktree registered on Mark's main git dir would touch his checkout. Mitigation: `git clone --no-hardlinks` of this worktree into `tmp/sixtask-clones/`. The runner then adds its own worktree inside that clone.
- Receipts can contain tokens. Mitigation: runner redact plus a scan before every commit. Matches are replaced and the kind is counted. Raw values are not printed.
- Cloud lane may push a new runner mid-trial. Mitigation: `git fetch && git merge --no-edit origin/bot/mvp-cloud-1031` before each task. On a conflict outside owned files, abort the merge and record a cross-lane request. Do not resolve by editing their files.

## Item log

Format: `item | commit | tests | result`

- loop-card | 42d6952 | docs only | PASS
- base-merge | d0adb75 | merge origin/bot/mvp-cloud-1031 (cloud lane empty at d94d2b6) | PASS, runner still has no --writable-test
