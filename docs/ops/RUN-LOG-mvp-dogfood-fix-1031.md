# Run log: mvp-dogfood-fix-1031

Lane: fix daily-use friction the dogfood lanes found.
Branch: `bot/mvp-dogfood-fix-1031`. Worktree: `~/DEVELOP/pfy-mentat/tmp/mvp-dogfood-fix-1031`.
Base: `origin/bot/mvp-integrate-1031` at `0c3f133d4d2ea2bf104f6390416fa8d26f394803`.
Launch: 2026-10-31T22:38:38Z. Wall cap: 2026-11-01T06:38:38Z (8 hours), or 2026-11-02T02:00Z, whichever is first.
Stop new items by 2026-11-01T06:18:38Z so the handoff has 20 minutes.
Needs a local model: no. Cloud Grok only. Never `--local`. Do not run `scripts/pregate.sh`.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     each dogfood friction that would annoy Mark in daily use is fixed with a behavior test, or recorded as already done, skipped, or handed to another lane
1 Goal met:                  targeted unittest modules for the touched behavior, plus the handoff
2 Turn cap:                  8 friction items
3 Budget cap:                no cloud spend, no local model, no --local, targeted tests only
4 Wall clock:                2026-11-01T06:38:38Z or 2026-11-02T02:00Z, leave 20 minutes for the handoff
5 No-progress:               same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:           user stop. Do not ask. Conservative choice goes in the decisions file
7 Error threshold:           3 consecutive item failures, then stop
8 External event:            n/a. Do not merge. Another lane owning the file means skip and record a cross-lane request
Loop type:                   goal
Human gate:                  no merge, no PR, no tag
```

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-dogfood-fix-1031.md` are the binding. Decision logged.

## Drop-in exits (check before every item)

1. Wall cap: 8 hours from launch, or Sunday 2026-11-01 18:00 PT (2026-11-02T02:00Z). Leave 20 minutes for the handoff.
2. Lane empty: no friction item left that fits these rules.
3. No progress: the same failure twice with no new information, or 3 items in a row skipped.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 (2 x 32 cores) for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: record tests that fail on the base and skip that area. Do not stop the lane.

Known red base from the integrate handoff, not re-run yet, skip those areas:

- `tests.test_pfy_build_local.CloudBuildUnchangedTests.test_help_and_dry_run_stay_the_same` (integrate pass 2). Do not edit `tests/test_pfy_build_local.py`.
- `tests.test_local_bench.OutdirPathTests.test_relative_outdir_log_path_safe` when `TMPDIR` is inside the repo.

## Phases

Overview: Read the dogfood handoffs and reports. Fix each daily-use friction (confusing message, missing flag, slow wasted step, unclear receipt, wrong default) with the smallest change and a behavior test. Prefer `scripts/pfy`, docs, and the CLI. Cloud runner edits stay inside one function per item because mvp-cloudfix-1031 also edits that file.

- exits | docs/ops/RUN-LOG-mvp-dogfood-fix-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-dogfood-fix-1031.md | exit card committed before a fix | none | general
- F-subject | scripts/pfy_build_cloud.py `commit_subject` and the one call in `commit_paths`, tests/test_pfy_build_cloud.py | git log subject is whole words, at most 72 characters, and the body keeps the rest of the task | exits | general
- F-redact | `redact` only, plus the operator card sentence | a short fixture assignment stays in the receipt, a real-looking secret value does not | F-subject | general
- F-env | `gate` only | the product gate does not see secret-named parent env vars, and grok still receives the parent env | F-redact | general
- F-base | `resolve_base` only, help text, the two base flag rows | HEAD that is not origin/main exits 2 until `--base` is set. A matching HEAD still defaults to origin/main. A missing origin/main still defaults to HEAD | F-env | general
- F-gate | `before_gate_block` and the one call in `execute`, failure-table rows | a missing gate binary, or the default unittest command failing on import, exits 2 before grok. A custom red gate still reaches grok | F-base | general
- handoff | docs/ops/HANDOFF-mvp-dogfood-fix-1031.md | final state line, pushed, not merged | the items above | general

Risks:

- Cloudfix edits `scripts/pfy_build_cloud.py` in parallel. Mitigation: one function per commit, named in the handoff.
- Refusing a HEAD that differs from origin/main changes a locked test. Mitigation: `--base origin/main` keeps the old "do not include caller-only commits" result. Dry-run with no origin/main stays HEAD.
- Scrubbing the grok environment could drop the operator API key. Mitigation: scrub the gate env only.
- Treating every `No module named` as usage would block a red product import that the task is meant to fix. Mitigation: that check applies only to the default unittest command.

## Friction queue

Sources: `origin/bot/mvp-dogfood-1031` handoff and `eval/mvp-1031/dogfood/REPORT.md`, `origin/bot/mvp-dogfood2-1031` run log and notes (no handoff file on that tip), `origin/bot/mvp-gom-dogfood-1031` handoff and `eval/gom-dogfood-1031/REPORT.md`, `origin/bot/mvp-daily-card-1031` handoff. Cloudfix handoff checked so this lane does not repeat finished work.

| id | source | friction | disposition |
| --- | --- | --- | --- |
| F1 | dogfood run 02, gom item 1 | a new test file was `tests-tampered` | already done on this base. Do not re-apply |
| F-subject | dogfood2 notes 01 through 05 | cloud commit subject is the task cut at 72 characters, mid-word | fix |
| F-redact | gom item 4 | receipt rewrites `user_key` and `token` fixture values | fix, inside `redact` |
| F-env | gom item 5 | the gate inherits secret-named parent env vars | fix, inside `gate` only |
| F-base | gom item 3 | default base is origin/main even when `--repo` HEAD is a different branch, so the run builds the wrong tree | fix, inside `resolve_base` |
| F-gate | gom item 2 | a missing interpreter or a default unittest import error is scored as a product FAIL and spends grok retries | fix |
| F-cap | dogfood2 run log | review diff cap is 12000 characters | skip. The closest patch was 10454 characters. No truncation was observed |
| F-wall | dogfood2 run 02 | one run took 1490 seconds | skip. That is model time, not a default this lane can shrink without an ADR |
| F-emdash | dogfood2 run 02 notes | a produced comment contains an em dash | skip. That is model output on a throwaway commit, not the CLI |
| F-adr | dogfood handoff OQ | two docs link a missing ADR-0017 file | skip. Open question, and `docs/modules/README.md` is not this lane's file. The draft already sits in the dogfood handoff |
| F-card | daily-card handoff | the demo section copies a real PASS | no friction to fix. Flag rows change only when F-base or F-gate changes the contract |

## Items

item | commit | tests | result
F-subject | 13a63ea | tests.test_pfy_build_cloud.CloudBuildFailureTests.test_long_task_subject_stops_on_a_word_and_the_body_keeps_the_rest and test_short_task_subject_is_the_whole_task, 2 OK | PASS
F-redact | 599d2d2 | test_receipt_keeps_fixture_ids_and_still_hides_secret_assignments plus the two existing redact tests and tests.test_pfy_build_docs, 8 OK | PASS
F-env | 50ac9ba | tests.test_pfy_build_cloud 50 OK, including test_gate_drops_secret_env_and_grok_still_sees_it | PASS
F-base | 2348080 | test_head_that_is_not_origin_main_exits_2_before_grok, test_explicit_origin_main_still_excludes_caller_only_commits, test_dry_run_uses_origin_main_when_it_matches_head, dry-run and help and docs, 11 OK | PASS

## States

state: exits written | tests: none yet | files: 2 | err: none
state: F-subject PASS | tests: 2 OK in 0.265s | files: pfy_build_cloud.py commit_subject plus one call in commit_paths | err: none
state: F-redact PASS | tests: 8 OK in 0.395s | files: redact only, plus one card sentence | err: none
state: F-env PASS | tests: tests.test_pfy_build_cloud 50 OK in 10.465s | files: gate env scrub only | err: none
state: F-base PASS | tests: 9 OK in 0.354s plus help 2 OK | files: resolve_base, --base help, two card rows, pfy help line | err: none
