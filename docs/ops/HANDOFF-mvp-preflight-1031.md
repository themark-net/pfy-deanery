# Handoff mvp-preflight-1031

Branch `bot/mvp-preflight-1031`. Base `origin/main` `85c53dc`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-preflight-1031`.

Runtime head: `0fbf4261f20a5dcf1da25072d18d58d04b2504e4` (`0fbf426`).
Compare: https://github.com/themark-net/pfy-mentat/compare/main...bot/mvp-preflight-1031
No PR. No merge. No tag.

Exit: lane empty (drop-in exit 2). The classifier definition of done is met, and no further gap in `origin/bot/mvp-plan-1031:docs/plans/MVP-PARALLEL-1031.md` fits this lane's owned files.

Launch `2026-10-31T19:54:16Z`. Wall cap `2026-11-01T03:54:16Z` (8 hours) or `2026-11-02T02:00Z`, whichever comes first. This exit is not the wall cap.

## Done

| Item | SHA | Tests | Result |
| --- | --- | --- | --- |
| Loop exits before code | `8b1fb4b` | none (docs only) | pushed |
| `classify_cloud_failure` | `0fbf426` | `nice -n 19 python3 -m unittest tests.test_build_preflight` | 8 tests OK in 0.001s |

`pfylib/build_preflight.py` exports `classify_cloud_failure(rc, stdout, stderr)`.

Rules, in order, over `stdout + "\n" + stderr`, case insensitive, only when `rc` is not 0:

1. `rate-limit` if the text contains `rate limit`, `usage limit`, `quota exceeded`, `too many requests`, or `429`.
2. `unauthenticated` if the text contains `unauthenticated`, `not logged in`, `please log in`, or `auth.json`.
3. Otherwise `other`.

`rc` 0 is always `other`. The function takes no path, opens no file, and returns only that enum.

## Skipped

Recorded as one lane-empty scan. These were not started, so they do not count as three skipped items.

| Gap | Why it does not fit |
| --- | --- |
| G1-G5, G7-G9 | Other round-1 lanes own the files |
| G6 receipt and exit codes | mvp-cloud-1031. This lane owns the classifier only |
| G10 | Plan decision D18. Not a round-1 lane |
| mvp-dedupe-1031 | Round 2. `origin/bot/mvp-integrate-1031` does not exist. Owns `scripts/pfy_build_cloud.py`, which this lane must not edit |
| mvp-sandbox-gate-1031, mvp-daily-card-1031 | Round 2, and the files are not owned here |
| mvp-local-t5-1031 | Round 2, needs a local model, and this drop-in says needs a local model: no |

Red base: `pfylib/build_preflight.py` is absent on `origin/main`, so there was no pre-existing `tests.test_build_preflight` failure to record. Full discover was not run outside pregate.

## Test evidence

```text
nice -n 19 python3 -m unittest tests.test_build_preflight
Ran 8 tests in 0.001s
OK
```

Ran twice on the committed sources (the second run is the one that matches `0fbf426`). TMPDIR was this worktree's `tmp/`.

## How it fails and how it recovers

| Failure | What would go wrong | Recovery in this change |
| --- | --- | --- |
| `rc` 0 still matches a quota phrase | A success is treated as a rate limit and retried | `rc == 0` returns `other` before any phrase check. Test: text `rate limit` and text `429` / `please log in` with rc 0 |
| Auth phrase matched before rate-limit | The operator is told to log in during an outage | Rate-limit phrases are tested first. Test: each rate phrase plus `not logged in`, including the auth phrase in the other stream |
| Stdout glued to stderr with no newline | A split line `rate ` / `limit` looks like `rate limit` | Join is `stdout + "\n" + stderr`. Test expects `other` for that split |
| Return echoes grok text | A `BEGIN PRIVATE KEY` marker or an `sk_` token leaves the function | Return is only the enum. Test puts both markers in the body and asserts they are absent from the result |
| Function opens `auth.json` | Classification depends on a credential file | No path argument. Test patches `open` and `os.open` so any open fails, and it checks the empty temp directory for a created `auth.json` without reading one |

## Cross-lane requests

- mvp-cloud-1031: keep the inline copy so that branch tests alone. Use the same phrases, in the same order. Do not import `pfylib.build_preflight` on that branch.
- mvp-integrate-1031: after the merges, if both the inline classifier and `classify_cloud_failure` exist, switch `scripts/pfy_build_cloud.py` to the import when that edit is under 40 lines. If it is larger, leave the inline copy and name mvp-dedupe-1031.
- mvp-dedupe-1031: do not start until `origin/bot/mvp-integrate-1031` has a pushed handoff. This lane did not edit `scripts/`.

## Gate

Runtime change. Needs Tester plus Reviewer at `0fbf426` (classifier) plus this handoff commit, which is docs only.

Pregate on `0fbf426` (this handoff commit is docs only and was not a second pregate): OVERALL=PASS, wall=1065s, pass=6, fail=0, skip=1. The skipped check is `suite`, because ubuntu-parity and eval-structural already ran discover. Ubuntu-parity discover: Ran 956 tests in 435.246s, OK (skipped=100).

Summary: `/home/mark/DEVELOP/pfy-mentat/tmp/pregate-runs/0fbf426-20261031T200346Z-1489248/pregate-summary.md`

## Next step

Collect round 1 on mvp-integrate-1031. Merge this branch in the plan's order (after mvp-review-fix-1031, before mvp-surface-1031). Wire the import only when it stays under 40 lines.

## Decisions

`docs/ops/AUTONOMOUS-DECISIONS-mvp-preflight-1031.md` (6 lines).
