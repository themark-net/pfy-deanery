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
Kills after: pending until survivor tests or a review-fix2 re-run
Survivors left: 3 (R7, R8, R9)
Not killed or survived: none
