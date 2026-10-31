# RUN-LOG mvp-realfail-1031

Lane `bot/mvp-realfail-1031`. Worktree `tmp/mvp-realfail-1031`. Base `origin/bot/mvp-cloud-1031`. Launch `2026-10-31T20:17:03Z`.

```text
LOOP EXIT CARD
Goal (success criteria): every Failure cases row in the MVP plan has a receipt under eval/mvp-1031/realfail/<case>/ and a REPORT row whose verdict is matches or FINDING. tests.test_mvp_1031_realfail_receipts is green.
1 Goal met:                  the receipt test plus REPORT.md covering the table
2 Turn cap:                  the 10 numbered cases, then any table row they did not cover, then stop on lane empty
3 Budget cap:                cloud Grok only. No --local and no local model. Stop when the same grok failure repeats with no new receipt fact.
4 Wall clock:                8h from 2026-10-31T20:17:03Z. Stop new items at 2026-11-01T03:57:03Z. Hard stop 2026-11-01T04:17:03Z. Sunday 2026-11-02T02:00Z is later, so the 8h cap binds. Leave 20 minutes for the handoff.
5 No-progress:               the same failure twice with no new information, or 3 items skipped in a row
6 Human interrupt:           user stop. Do not ask questions. Push only this branch. No force, no PR, no merge to main.
7 Error threshold:           3 consecutive same failures, then stop
8 External event:            origin/bot/mvp-cloud-1031 moves. Merge it before each item. Repeat a FINDING case after each new cloud commit.
Loop type:                   goal
Human gate:                  no merge and no PR. Push is the requested ship step.
```

Overview: exercise the real cloud runner (`./pfy build`) against the Functional MVP failure table, record a receipt and a verdict for each row, and lock those receipts with a behavior test. A runner bug is a FINDING for lane mvp-cloud-1031, not an edit to the runner.

Phases:
- exits | docs/ops/*-mvp-realfail-1031.md, tests/test_mvp_1031_realfail_receipts.py, eval/mvp-1031/realfail/REPORT.md | exit card and a receipt checker that rejects a bad temp receipt | none | lead
- case-interrupted | eval/mvp-1031/realfail/interrupted-sigint and interrupted-sigterm | exit 1, reason interrupted, no branch, no orphan process this lane started | exits | lead
- case-sigkill-reap | eval/mvp-1031/realfail/sigkill-reap | reap exit 0, receipt ABORTED / no-receipt, planted local sleep survives | case-interrupted | lead
- case-timeout | eval/mvp-1031/realfail/timeout | exit 3, status TIMEOUT, reason timeout, no branch | case-sigkill-reap | lead
- case-dirty-caller | eval/mvp-1031/realfail/dirty-caller | uncommitted and staged caller files stay dirty and out of the commit | case-timeout | lead
- case-gate-red | eval/mvp-1031/realfail/gate-red | exit 1, gate reason, attempts length 3, no branch, gate tail in a later real grok prompt | case-dirty-caller | lead
- case-review-reject | eval/mvp-1031/realfail/review-reject | real unsafe task, review verdict recorded | case-gate-red | lead
- case-auth | eval/mvp-1031/realfail/auth-failure | exit 1, unauthenticated, recovery text, runner does not read auth.json | case-review-reject | lead
- case-rate-limit | eval/mvp-1031/realfail/rate-limit | simulated on the fake-grok seam, exit 4, BLOCKED, rate-limit | case-auth | lead
- case-gitignored | eval/mvp-1031/realfail/gitignored-extra | gitignored extra file absent from the commit; scope-mismatch row recorded real or simulated | case-rate-limit | lead
- case-redaction | eval/mvp-1031/realfail/redaction | planted xai-FAKE0000 redacted in the receipt, or FINDING | case-gitignored | lead
- case-no-change | eval/mvp-1031/realfail/no-change | table row no-change, real grok if it leaves the tree unchanged, else the fake-grok seam labeled simulated | case-redaction | lead
- recheck | FINDING cases only | note fixed or still open after each new origin/bot/mvp-cloud-1031 commit | any FINDING | lead
- handoff | docs/ops/HANDOFF-mvp-realfail-1031.md | final state line, commit, push | all | lead

Risks:
- Orphan grok: record pids this lane starts, signal only those, never pgrep-kill the host.
- Secrets: do not read ~/.grok/auth.json. Grep receipts before every commit.
- Shared host: no local model and no full unittest discover. Targeted tests only.
- Real grok drift: record the observed receipt. Do not repeat a case more than once unless the second run adds a fact.
- Runner edits: never edit scripts/pfy_build_cloud.py, scripts/pfy, or tests/test_pfy_build_cloud.py. A bug becomes a patch under the case dir and a cross-lane request.

Host at launch: MemAvailable about 64 GiB, load 3.6 on 32 cores. Under the pressure floor.

## Log

item | commit | tests | result
exits | 07c45ca | tests.test_mvp_1031_realfail_receipts 3 ok | pass, pushed
merge-cloud | c0cf507 | git merge origin/bot/mvp-cloud-1031 | merged and pushed before interrupted
interrupted | 00d0ec4 | tests.test_mvp_1031_realfail_receipts 3 ok | SIGINT and SIGTERM match DoD
sigkill-reap | (this commit) | tests.test_mvp_1031_realfail_receipts | FINDING stray grok after reap
