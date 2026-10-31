# Dogfood report: mvp-dogfood2-1031

Real cloud `./pfy build "<task>"` runs from this worktree against a throwaway clone under `tmp/target-<n>`. No `--local`. Nothing from a target is pushed. A PASS that this lane accepts is cherry-picked onto `bot/mvp-dogfood2-1031` with a Built-by trailer. The runner merged before each run was `origin/bot/mvp-cloudfix-1031`. The cloudfix column is that SHA. Runs 01 to 06 used `d35af20`. Run 07 used `90d3c6e`.

Gate pass means receipt status PASS and exit_code 0. Review accept means `review.verdict` is accept. Human accept means this lane cherry-picked the cloud commit.

## Runs

| dir | status | exit_code | review | human | wall_s | commit | cloudfix | reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 01-tree-sig-copies | PASS | 0 | accept | yes | 398 | 31a863c | d35af20 | ok |
| 02-pregate-orphans | PASS | 0 | accept | yes | 1490 | 42e4452 | d35af20 | ok |
| 03-receipts-outside | PASS | 0 | accept | yes | 223 | 507cfcf | d35af20 | ok |
| 04-remaining-home-sigs | PASS | 0 | accept | yes | 661 | 3e4c7ba | d35af20 | ok |
| 05-timeout-substep | PASS | 0 | accept | yes | 306 | 26e71fa | d35af20 | ok |
| 06-daemon-stop-timeout | PASS | 0 | accept | yes | 301 | 072c7cd | d35af20 | ok |
| 07-hr-sigterm | TIMEOUT | 3 | none | no | 2942 | none | 90d3c6e | timeout after review-rejected |

## Rates

- runs: 7
- gate_pass_rate: 6/7
- review_accept_rate: 6/7
- human_accept_rate: 6/7
- median_wall_s: 398

Median is the middle wall in seconds, or the integer mean of the two middle values when the count is even. Sorted walls: 223, 301, 306, 398, 661, 1490, 2942.

## Scope against the DoD

The band asked for 2 to 3 files and about 60 to 250 changed lines, which is the review-cap edge. `DIFF_CAP` in `scripts/pfy_build_cloud.py` is 12000 characters.

| dir | files | changed lines | patch bytes | truncated |
| --- | --- | --- | --- | --- |
| 01-tree-sig-copies | 3 | 75 | 5351 | no |
| 02-pregate-orphans | 2 | 245 | 10454 | no |
| 03-receipts-outside | 2 | 34 | 3676 | no |
| 04-remaining-home-sigs | 3 | 130 | 6693 | no |
| 05-timeout-substep | 2 | 19 | 3925 | no |
| 06-daemon-stop-timeout | 1 | 7 | 1666 | no |
| 07-hr-sigterm | 0 | 0 | 0 | no |

The closest run is 02 at 10454 of 12000 characters. A change inside the 250 line band did not truncate the review. Runs 03, 05, and 06 are under the 60 line aim. They were still human-accepted because the behavior matched the gate. Run 06 is one file.

## Findings

| id | severity | run | summary |
| --- | --- | --- | --- |
| F1 | medium | all | Commit subjects are the task text sliced at 72 characters, so they end mid-word. Runs 01 and 04 share a subject because both tasks open with the same sentence. |
| F2 | medium | 02 | The largest patch in this band is 10454 characters. The review cap of 12000 was not hit, and the receipt does not say whether the diff was truncated. |
| F3 | high | 07 | Attempt 2 passed the gate by logging `docker -- volume rm -f pfy-hr-smoke`, which supplies the leading space in the gate substring ` volume rm `. Review rejected that command. Attempt 3 hit the 1200s grok timeout. The runner then removed the worktree, so the receipt has no unified diff. |

## Cross-lane requests

For mvp-cloudfix-1031:

1. F1. Stop cutting the cloud commit subject at a fixed 72 characters. Keep a short unique subject that ends on a word boundary. The slice is `redact(" ".join(self.args.task_text.split())[:72])` in `scripts/pfy_build_cloud.py`.
2. F2. Record on the receipt whether the review prompt's diff was truncated (`review.truncated` true or false). A 60 to 250 line task can stay under 12000 characters, so this lane cannot prove the cap from the line band alone.
3. F3. Keep the unified diff for a review-rejected attempt on the receipt. Run 07's worktree was removed on TIMEOUT, and the attempt tails have prose only. The review itself did catch a cleanup command that was not `docker volume rm`.
