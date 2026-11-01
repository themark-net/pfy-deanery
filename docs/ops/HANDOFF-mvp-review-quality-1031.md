# Handoff mvp-review-quality-1031

Branch `bot/mvp-review-quality-1031`. Base `origin/bot/mvp-integrate-1031` at `f877c7d` when the lane started. Exit: DONE. The planted measurement is complete and no further item fits this lane.

## Done

| Item | SHA | Result |
|---|---|---|
| Exit card | `ebeaa55` | Run log and decisions before measurement |
| Planted set | `575c5cc` | 10 bad and 10 good diffs, harness, replay test |
| Baseline | `6f64c19` | Real grok. False accept 3, false reject 0 |
| Prompt | `67e7a4a` | `review_prompt` names hash drops, assertion deletes, and token prints |
| Remeasure and report | this commit | False accept 0, false reject 0. `eval/mvp-1031/review-quality/REPORT.md` |

## Skipped

- Pregate: the drop-in says do not run `scripts/pregate.sh`.
- Local review prompt in `scripts/pfy_build_local.py`: another lane owns that file. See cross-lane.
- A third measurement pass: the remeasure cleared the three false accepts and added no false rejects.
- `docs/TODO.md` and `docs/OPEN_QUESTIONS.md`: shared. No new OQ. The prompt sentence is a small rule, not an ADR.

## Test evidence

- `nice -n 19 python3 -m unittest tests.test_review_quality_replay tests.test_pfy_build_cloud`: 68 tests, OK, after the prompt edit (`67e7a4a`).
- `nice -n 19 python3 -m unittest tests.test_review_quality_replay`: 7 tests, OK, after both recorded rounds were on disk. This replays fixture reviewer text and every saved stdout through `parse_verdict` and the root-delete override.
- Before round: `eval/mvp-1031/review-quality/results/before/summary.json` (3 false accepts, 0 false rejects). `b01` first call timed out at 180s with no verdict and was retried at 420s. That retry accepted.
- After round: `eval/mvp-1031/review-quality/results/after/summary.json` (0 and 0). Wall about 381s. No timeout.

## How the change fails and recovers

The cloud reviewer used to accept a diff when the task asked for it, unless the diff deleted tests, added a recursive delete, or aimed a command at the filesystem root. That missed a `:target` content-hash drop, a deleted assertion, and a token printed to stderr.

The new sentence names those three, still when the task asks. Recover on a new miss: add the diff to the planted set, extend that one sentence, rerun the harness. A timeout stays an error and is not counted as an accept. There is no new local regex for the hash drop. The root-delete override is unchanged and still catches only `rm -rf /` and `rm -fr /`.

If someone deletes the new sentence, `test_review_prompt_names_baseline_misses_and_redacts_a_key` fails. If `parse_verdict` stops matching the saved model text, `test_recorded_reviewer_stdout_reparses_to_the_stored_verdict` fails.

## Cross-lane

- `mvp-cloudfix-1031` owns `scripts/pfy_build_cloud.py` and was live. This lane edited only `review_prompt`. At fetch, `origin/bot/mvp-cloudfix-1031` (`0dfc9d1`) had the old sentence. A merge must keep the sentence from `67e7a4a`.
- Local `_review_prompt` in `scripts/pfy_build_local.py` still does not name a hash drop, a deleted assertion, or a token print. This lane did not edit that file.

## Gate

Runtime change in `scripts/pfy_build_cloud.py`: Tester plus Reviewer. The planted set, recordings, and report are eval. Pregate was not run.

## Next

Integrate `bot/mvp-review-quality-1031` and keep the `review_prompt` sentence. If that sentence changes, rerun `python3 eval/mvp-1031/review-quality/run_review.py --round after`.
