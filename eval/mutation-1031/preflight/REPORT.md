# Preflight and receipt mutation report (2026-10-31)

Harness: `eval/mutation-1031/preflight/run_mutants.py`.

Each mutant is applied to a copy of one target inside `git clone --local --no-hardlinks` under this worktree's `tmp/mutation-1031/preflight/clones/`. The worktree targets are never opened for write. The suite is `nice -n 19 python3 -m unittest`, timeout 90s. A failing suite is killed. A timeout is killed. A missed anchor is `unapplicable` and the process exits 2. Survived means exit 0.

Targets:

- `pfylib/build_preflight.py` (`classify_cloud_failure` and its ordered checks)
- `eval/mvp-1031/check_receipt.py`

Before (`--baseline-only`) runs `tests.test_build_preflight` and `tests.test_mvp_1031_receipt`. After also runs `tests.test_mut_preflight_survivors`. It does not run `tests.test_mut_preflight_harness`, which would start the harness again.

The unmutated suite is scored first. On this run it survived both rounds (20 tests before, 40 tests after). Mutants were scored only after that.

Scored at `b5d57f8` on `bot/mvp-mutate-preflight-1031`. Integrate base in the results file: `0c3f133`. An earlier 18-mutant snapshot at `b5c51f4` (6 killed, 12 survived, baseline-only) was replaced when the catalog grew to 27. The numbers below are the 27-mutant catalog.

Source sha256, same on both rounds:

- `pfylib/build_preflight.py` `050aeff48ca27e50203633f3fcbc115503eb41f758b4f043ef3c84067251d635`
- `eval/mvp-1031/check_receipt.py` `2eb55d7fdce8012e1f07e57237c8b28ea404c1949d1d587b53f9274fddcf1298`

Raw rows: `results/before.json`, `results/after.json`.

Ids skip P4, R6, and R9. Those numbers were not used.

## Counts

| Round | Mutants | Killed | Survived |
|-------|---------|--------|----------|
| Before (product suites only) | 27 | 6 | 21 |
| After (product suites plus survivor tests) | 27 | 26 | 1 |

The one after survivor is P9, which is equivalent. See below.

## Mutant table

| ID | Mutant | Before | After | What went red |
|----|--------|--------|-------|----------------|
| P1 | zero exit still classified | killed | killed | `test_zero_exit_is_other_even_when_the_text_matches` |
| P2 | auth rule runs before rate-limit | killed | killed | `test_each_rate_limit_phrase_wins_even_with_not_logged_in` |
| P3 | 429 phrase removed | killed | killed | same test, phrase `429` |
| P5 | case fold removed | killed | killed | `test_each_auth_phrase_without_a_rate_limit_phrase` |
| P6 | stdout and stderr joined without a newline | killed | killed | `test_phrase_split_across_the_newline_join_is_other` |
| P7 | negative rc treated as success | survived | killed | `test_negative_rc_still_classifies_quota_and_auth` |
| P8 | repeated spaces collapsed before match | survived | killed | `test_double_spaced_phrases_stay_other` |
| P9 | zero float clause added | survived | survived | equivalent, no test |
| P10 | 429 must be a whole token | survived | killed | `test_429_inside_a_longer_token_is_rate_limit` |
| R1 | status check skipped | survived | killed | `test_status_other_than_pass_is_rejected` |
| R2 | reason check skipped | survived | killed | `test_reason_other_than_ok_is_rejected` |
| R3 | exit_code check skipped | survived | killed | `test_nonzero_and_boolean_exit_codes_are_rejected` |
| R4 | gate cmd check skipped | survived | killed | `test_empty_gate_cmd_is_rejected` |
| R5 | invalid json accepted | survived | killed | `test_truncated_json_is_rejected` |
| R7 | pushed 0 accepted | survived | killed | `test_pushed_zero_is_rejected` |
| R8 | attempts accepts any truthy value | survived | killed | `test_attempts_string_is_rejected` |
| R10 | branch prefix allows cloudy | survived | killed | `test_branch_without_the_cloud_slash_is_rejected` |
| R11 | AKIA check skipped | killed | killed | `test_rejects_secret_markers_in_pass_shaped_json` |
| R12 | missing receipt file accepted | survived | killed | `test_missing_receipt_file_is_rejected` |
| R13 | json array accepted | survived | killed | `test_json_array_is_rejected` |
| R14 | commit suffix ignored | survived | killed | `test_commit_suffix_is_rejected` |
| R15 | uppercase commit accepted | survived | killed | `test_uppercase_commit_is_rejected` |
| R16 | review string accepted as verdict | survived | killed | `test_review_string_is_rejected` |
| R17 | usage failure exits 0 | survived | killed | `test_usage_without_a_path_is_rejected` |
| R18 | non-utf8 receipt accepted | survived | killed | `test_non_utf8_receipt_is_rejected` |
| R19 | schema case folded | survived | killed | `test_schema_case_is_rejected` |
| R20 | non-string gate accepted | survived | killed | `test_non_string_gate_is_rejected` |

## How the edits are applied

- P1 drops the `rc == 0` guard, so a zero exit is classified from the text.
- P2 runs the auth phrases before the rate-limit phrases.
- P3 deletes the `429` phrase.
- P5 stops calling `.lower()` on the joined log.
- P6 joins stdout and stderr with no newline.
- P7 treats every `rc <= 0` as `other`.
- P8 collapses a double space before matching.
- P9 adds `or rc == 0.0` beside `rc == 0`.
- P10 matches `429` only as a whitespace-separated token.
- R1 through R4 skip status, reason, exit_code, and gate.cmd.
- R5 returns success on invalid JSON.
- R7 compares `pushed` with `!=` instead of `is not`, so JSON `0` passes.
- R8 treats any truthy attempts value as a non-empty list.
- R10 accepts a branch that starts with `cloud` and has no slash.
- R11 skips the AKIA scan.
- R12 exits 0 when the receipt path is missing.
- R13 skips the JSON-object check, so a list crashes or is not rejected as an object.
- R14 accepts a commit that merely starts with 40 hex chars.
- R15 accepts uppercase hex in the commit.
- R16 treats a non-dict review value as the verdict.
- R17 exits 0 on usage errors.
- R18 exits 0 when the file is not utf-8.
- R19 compares the schema case-insensitively.
- R20 rejects only an empty string, so a missing gate or a bare string passes.

## P9 is equivalent

`rc == 0 or rc == 0.0` does not change the result of `rc == 0` for a real exit code. `0.0 == 0` is already true, and so is `False == 0`. Checked on `0`, `0.0`, `1`, `-1`, `2`, `False`, `True`, `None`, `"0"`, `""`, and `0.1`: the two conditions match on every value. A custom object that treats `0` and `0.0` differently is not an exit code this function receives. No behavior test can fail on one side and pass on the other. P9 stays survived on purpose. It is not a product bug and not a weak assertion.

## What the new tests lock

- A negative exit that names a quota or a login failure is still classified. Only an exact zero skips the phrases.
- A double space does not invent `rate limit` or `not logged in`.
- `429` inside a longer token (`14290`, `x429y`) is still rate-limit.
- A PASS-shaped receipt is rejected when status, reason, exit code, gate, pushed, attempts, branch, commit, review, or schema is wrong in the ways listed above.
- Truncated JSON, a JSON array, a missing file, a usage error, and a non-utf8 file exit 1 with one reason line and no traceback.

No product source was edited. No test is marked `expectedFailure`.

## Re-run

```bash
nice -n 19 python3 eval/mutation-1031/preflight/run_mutants.py --baseline-only --label before
nice -n 19 python3 eval/mutation-1031/preflight/run_mutants.py --label after
```

Use `--baseline-only` to score the product suites without `tests.test_mut_preflight_*`. If an anchor no longer matches, the row is `unapplicable` and the command exits 2. Update that anchor. Do not treat it as survived. If a new row is `survived` and it is not equivalent, add a behavior test under `tests/test_mut_preflight_survivors.py`. Do not edit `pfylib/build_preflight.py` or `eval/mvp-1031/check_receipt.py` from this lane.
