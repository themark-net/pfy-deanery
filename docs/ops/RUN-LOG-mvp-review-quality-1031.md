# RUN LOG mvp-review-quality-1031

Lane `mvp-review-quality-1031`. Branch `bot/mvp-review-quality-1031`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-review-quality-1031`. Base `origin/bot/mvp-integrate-1031` at `f877c7d`. Launch `2026-10-31T23:39:22Z`.

Overview: Measure the cloud reviewer on 10 bad and 10 good planted diffs, record false accepts and false rejects, then make one small prompt or input change and measure again. Keep a behavior test that replays recorded reviewer text through the parser. Report before and after in `eval/mvp-1031/review-quality/REPORT.md`.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     20 planted diffs reviewed by the real cloud reviewer; before and after false-accept and false-reject counts in REPORT.md; replay test green
1 Goal met:                  eval/mvp-1031/review-quality/REPORT.md has both passes, and tests.test_review_quality_replay passes
2 Turn cap:                  8 items, and at most 2 measured reviewer passes (baseline, then one remeasure)
3 Budget cap:                cloud Grok only, sequential, no --local; stop the batch on rate-limit
4 Wall clock:                8h from 2026-10-31T23:39:22Z, so stop new items at 2026-11-01T07:19:22Z (20 min handoff reserve). Sunday 2026-11-01 18:00 PT (2026-11-02T02:00:00Z) is later and does not bind
5 No-progress:               same failure twice with no new information, or 3 items skipped in a row
6 Human interrupt:           user stop. No questions while the loop runs
7 Error threshold:           3 consecutive same failures, or 2 rate-limits, then stop
8 External event:            stop a file if origin/main or the integrate base already closed it
Loop type:                   goal
Human gate:                  no merge, no PR, no tag. Push this branch only
```

Drop-in exits (same run, checked before every item):

1. Wall cap: the clock above.
2. Lane empty: no remaining item that fits this lane and these rules.
3. No progress: same failure twice, or 3 skips in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: record tests that fail before the change and skip that area. Do not stop the lane.

Host at launch: MemAvailable 40498608 kB, load 6.40, 6.71, 5.78 on 32 cores. Under the pressure line.

## Phases

- exits | docs/ops/RUN-LOG-mvp-review-quality-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-review-quality-1031.md | exit card committed | none | general
- planted-set | eval/mvp-1031/review-quality/, tests/test_review_quality_replay.py | 10 bad and 10 good diffs, harness calls review_prompt and the grok argv the runner uses | exits | general
- baseline | eval/mvp-1031/review-quality/results/before/ | 20 real grok reviews, false accept and false reject counts | planted-set | general
- prompt | scripts/pfy_build_cloud.py function review_prompt only | smallest prompt or input change aimed at measured false accepts | baseline | general
- remeasure | eval/mvp-1031/review-quality/results/after/, REPORT.md | after counts, replay test green | prompt | general
- next-gap | files this lane owns | next review-quality gap, or lane empty | remeasure | general
- handoff | docs/ops/HANDOFF-mvp-review-quality-1031.md | state line, commit, push | all | general

## Risks

- mvp-cloudfix-1031 is live on scripts/pfy_build_cloud.py. Mitigation: edit only review_prompt, re-read it immediately before the edit, and do not take tests/test_pfy_build_cloud*.py.
- grok --always-approve can edit --cwd. Mitigation: cwd is tmp/review-quality-cwd in this worktree, never the product checkout and never another lane.
- A planted secret could land in git. Mitigation: diffs name the variable PFY_BUILD_TOKEN and print %s. No literal key, bearer, or private-key block. Saved model text is passed through redact() before commit.
- Rate limit. Mitigation: sequential calls, stop the batch on rate-limit, do not pass --local.

## Items

item | commit | tests | result
--- | --- | --- | ---
exits | ebeaa55 | docs only | pass
planted-set | 575c5cc | nice -n 19 python3 -m unittest tests.test_review_quality_replay (5 ok) | pass
baseline | 6f64c19 | real grok, 20 cases, false accept 3, false reject 0, errors 0 after the b01 retry | pass
prompt | 67e7a4a | nice -n 19 python3 -m unittest tests.test_review_quality_replay tests.test_pfy_build_cloud (68 ok) | pass
remeasure | this commit | real grok, 20 cases, false accept 0, false reject 0, errors 0 | pass

state: DONE | false accept 3 to 0, false reject 0 to 0 | tests.test_review_quality_replay 7 ok after both rounds | lane empty, no further review item in owned files
