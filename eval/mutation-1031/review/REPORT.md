# Mutation report: local review loop

Source: `3396ee7` /home/mark/DEVELOP/pfy-mentat/tmp/mvp-mutate-review-1031
Baseline: pass
Modules: tests.test_pfy_build_local_review, tests.test_pfy_build_local, tests.test_pfy_build_local_review_ci
Red base modules skipped: none
Model audit: No targeted test calls a model. Exclude list is empty. Stubs only: in-process Ollama, stub opencode, in-process HTTP reviewer. Cloud dry-run does not execute grok. opencode --help is not a model call.
Excluded tests: none

| id | reviewer | mutant | result | seconds | first failure |
| --- | --- | --- | --- | --- | --- |
| R1 |  | review skipped | killed | 184.954 | FAIL: test_a_reviewer_that_keeps_rejecting_stops_at_three_attempts |
| R2 |  | verdict inverted | killed | 162.67 | FAIL: test_a_reviewer_that_keeps_rejecting_stops_at_three_attempts |
| R3 |  | reviewer outage treated as accept | killed | 146.347 | FAIL: test_reviewer_http_error_is_not_a_reject_and_is_not_retried |
| R4 | M4 | reviewer outage treated as reject | killed | 197.447 | FAIL: test_reviewer_http_error_is_not_a_reject_and_is_not_retried |
| R5 | M7 | retry prompt missing previous diff | killed | 147.325 | FAIL: test_previous_diff_reaches_the_retry_prompt |
| R6 |  | missing gate tail in feedback | killed | 147.096 | FAIL: test_gate_fail_is_retried_and_the_tail_reaches_the_next_prompt |
| R7 |  | file cap off by one | survived | 146.814 |  |
| R8 |  | line cap off by one | survived | 147.688 |  |
| R9 |  | size cap removed | survived | 146.605 |  |
| R10 |  | allow list ignored | killed | 145.824 | FAIL: test_out_of_scope_patch_is_rejected_and_the_retry_passes |
| R11 |  | git add -A -f scope check bypassed | killed | 148.024 | FAIL: test_gitignored_extra_file_is_absent_from_the_commit |
| R12 |  | no-change counted as PASS | killed | 146.621 | FAIL: test_green_gate_and_empty_diff_is_no_change_when_retries_are_spent |
| R13 |  | attempts not recorded | killed | 146.856 | ERROR: test_missing_wiring_names_the_module_and_the_retry_wires_both |
| R14 |  | stub env read in production | killed | 147.083 | FAIL: test_stub_binds_stay_off_unless_the_test_seam_is_on |

Kills before: 11 (R1, R2, R3, R4, R5, R6, R10, R11, R12, R13, R14)
Survivors before: 3 (R7, R8, R9)
Kills after: 14 (R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14)
Survivors left: none
Not killed or survived: none

## Kills after

`origin/bot/mvp-review-fix2-1031` had not moved past the merge in `3396ee7`, so R1-R6 and R10-R14 were not re-run. Their kill in the table above stands.

R7, R8, and R9 were applied one at a time on a fresh clone of `1c332e8`. The only module was `tests.test_mut_review_size_cap` (`--modules`, timeout 180s). That module's baseline passed. The worktree runner was not mutated.

| id | result | seconds | first failure |
| --- | --- | --- | --- |
| R7 | killed | 2.669 | FAIL: test_four_files_are_rejected_and_three_files_pass |
| R8 | killed | 2.673 | FAIL: test_two_hundred_fifty_one_lines_are_rejected_and_two_hundred_fifty_pass |
| R9 | killed | 2.296 | FAIL: test_four_files_are_rejected_and_three_files_pass |

R7 dies when 4 files are accepted. R8 dies when 251 lines are accepted. R9 dies on the 4-file case (the 251-line case would also fail it). No `expectedFailure`. No runner edit.
