# Run log: mvp-dogfood2-1031

Lane: dogfood the daily cloud runner on medium real pfy-mentat tasks.
Branch: `bot/mvp-dogfood2-1031`. Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-dogfood2-1031`.
Base: `origin/bot/mvp-integrate-1031` at `19c27109fc8d273c79fc4d1025551468d1f9e14a` plus the drop-in commit.
Launch: 2026-10-31T21:23:19Z. Wall cap: 2026-11-01T05:23:19Z (8 hours), or 2026-11-02T02:00Z, whichever is first.
Stop new tasks by 2026-11-01T05:03:19Z so the handoff has 20 minutes.
Needs a local model: no. Cloud Grok only. Never `--local`.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     8 or more medium cloud ./pfy build runs recorded under eval/dogfood2-1031, REPORT.md rows match receipts, Built-by trailers match PASS human-accept receipts, tests/test_dogfood2_1031_report.py fails on a planted mismatch
1 Goal met:                  python3 -m unittest tests.test_dogfood2_1031_report plus the report rates and findings
2 Turn cap:                  12 dogfood runs (aim 8, stop at 12 even if more gaps exist)
3 Budget cap:                cloud Grok only, default retries (2 extra, 3 total), default timeout 1200s per grok call, no --local, no second model
4 Wall clock:                2026-11-01T05:23:19Z or 2026-11-02T02:00Z, leave 20 minutes for the handoff
5 No-progress:               same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:           user stop. Do not ask. Conservative choice goes in the decisions file
7 Error threshold:           3 consecutive dogfood failures with the same reason, then stop
8 External event:            origin/bot/mvp-cloudfix-1031 merged before each task; if that merge cannot be applied, stop that task
Loop type:                   goal
Human gate:                  no merge, no PR. Human accept in this lane is the cherry-pick decision, logged per row
```

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files. This card, the drop-in exits, and `docs/ops/HANDOFF-mvp-dogfood2-1031.md` are the binding. Decision logged.

## Drop-in exits (check before every item)

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z). Leave 20 minutes for the handoff.
2. Lane empty: no medium task left that fits these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 (2 x 32 cores) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: record tests that fail on the base and skip that area. Do not stop the lane.

## Phases

Overview: Pick medium tasks (2 to 3 files, about 60 to 250 changed lines) from open TODO rows and handoff gaps, run the real cloud runner against a throwaway clone, record receipts, cherry-pick only a PASS that a human would accept, then lock the report with a test that fails on a planted mismatch.

- prep | docs/ops/RUN-LOG-mvp-dogfood2-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-dogfood2-1031.md | exit card committed before a dogfood run | none | general
- select | this log, task queue below | each task names source, files, and why it is not a repeat | prep | general
- dogfood | eval/dogfood2-1031/<n>-<slug>/, tmp/target-<n> | receipt, diff, command, wall, exit, attempts, review, human | select | general, lead only (one branch, one runner)
- report | eval/dogfood2-1031/REPORT.md, tests/test_dogfood2_1031_report.py | rows match receipts, trailers match, planted mismatch exits 1 | dogfood | general
- handoff | docs/ops/HANDOFF-mvp-dogfood2-1031.md | final state line, pushed, not merged | report | general

Risks:
- Review diff cap is 12000 characters in `scripts/pfy_build_cloud.py` (`DIFF_CAP`). A 60 to 250 line diff sits on that edge. Mitigation: keep the full diff in `diff.patch` and treat a truncated review that still accepts a bad diff as a finding for mvp-cloudfix-1031. Do not hand-fix the produced code.
- A new or edited test can fail `tests-tampered`. Mitigation: precommit the behavior test on the throwaway only, and do not pass `--writable-test` for it. The model may add a new test file. It may not edit the gate.
- Full `unittest discover` would hold the shared host. Mitigation: `--test-cmd` is the affected module. Recorded in the decisions file.
- Throwaway clone must not be Mark's checkout or another lane's worktree. Mitigation: `git clone` into this worktree's `tmp/target-<n>` only.
- Secrets in receipts. Mitigation: runner redaction plus a class-only scan before commit. Never print a matched value.

## Task queue

Not repeats of mvp-dogfood-1031 or mvp-selfhost-1031. Not catalog, `sources/entries/`, `TOOLS.md`, `data/tools.json`, or the MVP-owned runner files.

| n | slug | source | files | why it fits |
| --- | --- | --- | --- | --- |
| 01 | tree-sig-copies | docs/automation/x-intake-2026-10-16-handoff.md parked blind spots, and the note that smoke_119 still uses mtime | smoke_119_121.py, smoke_112_114.py, smoke_115_116.py | 3 copies, content plus mode plus symlink, not smoke_122 which selfhost owns |
| 02 | pregate-orphans | docs/ops/HANDOFF-pregate.md known gap: chdir plus reparent is missed and not signalled | scripts/pregate.sh, scripts/pregate_orphans.py, tests/test_pregate_orphans.py | 3 files, behavior is specified, not the latest-summary or lock tasks |
| 03 | later | next handoff gap that is still 2 to 3 files and 60 to 250 lines | confirm before the run | filled after 01 so a bad first result can change the queue |

Skipped up front, with reasons, in the decisions file: the open TODO rows that need a voice shelf, a local model, docker, a parked env, hardware, an ADR, or an open OQ.

## Items

item | commit | tests | result
01-tree-sig-copies | 31a863c | tests.test_tree_sig_copies 5 OK | PASS human-accept wall 398s attempts 1 review accept cloudfix d35af20
02-pregate-orphans | 42e4452 | tests.test_pregate_orphans 5 OK | PASS human-accept wall 1490s attempts 1 review accept cloudfix d35af20
03-receipts-outside | 507cfcf | tests.test_mvp2_t5_receipts plus two gitignore tests, 3 OK | PASS human-accept wall 223s attempts 1 review accept cloudfix d35af20

## States

state: prep written | tests: none yet | files: 2 | err: none
state: 01 PASS | tests: tests.test_tree_sig_copies 5 OK | files: 3 smoke copies | err: none
state: 02 PASS | tests: tests.test_pregate_orphans 5 OK | files: pregate.sh + pregate_orphans.py | err: none
state: 03 PASS | tests: tests.test_mvp2_t5_receipts and two gitignore tests 3 OK | files: 117 and 119 test modules | err: none
