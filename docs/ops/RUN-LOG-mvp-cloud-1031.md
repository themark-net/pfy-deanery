# Run log: mvp-cloud-1031

Launch: 2026-10-31T20:00:40Z
Wall cap: 2026-11-01T04:00:40Z (8 hours from launch), or 2026-11-02T02:00Z, whichever comes first.
Stop new items by 2026-11-01T03:40:40Z so the handoff has 20 minutes.
Host at launch: MemAvailable 66849300 KiB, 32 cores, load 3.32 3.00 2.92.

LOOP EXIT CARD
Goal (success criteria): ./pfy build "<task>" with a fake grok meets the lane DoD (PASS receipt pfy-cloud-build/1, failure receipts, dispatch). Checked by tests/test_pfy_build_cloud.py and tests.test_pfy_build_p.
1 Goal met:                  tests.test_pfy_build_cloud and tests.test_pfy_build_p green, handoff written
2 Turn cap:                  8 ordered items, then only gaps that fit owned files
3 Budget cap:                no local model, no Ollama, no 127.0.0.1:11434, no paid retry loop
4 Wall clock:                2026-11-01T04:00:40Z or 2026-11-02T02:00Z, earlier one wins
5 No-progress:               same failure twice with no new information, or 3 items skipped in a row
6 Human interrupt:           user stop. No question stops. Conservative choice goes in the decisions file.
7 Error threshold:           3 consecutive same test failures, then stop
8 External event:            stop if origin/main already contains this runner and the DoD tests pass
Loop type:                   goal
Human gate:                  no merge, no PR. Push only bot/mvp-cloud-1031.

Drop-in exits (checked before every item):
1. Wall cap above. Leave 20 minutes for the handoff.
2. Lane empty: no remaining item that fits owned files and these rules.
3. No progress: same failure twice with no new information, or 3 skips in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this change. Record and skip that area. Do not stop the lane.

Overview: Add the daily cloud build. ./pfy build "<task>" creates a worktree, runs cloud Grok, gates, reviews, and commits on a cloud/ branch with a receipt. ./pfy build --local and ./pfy build -p stay on their current scripts. Tests use a fake grok. Nothing is pushed and no PR is opened by the runner.

Phases:
- exits | docs/ops/RUN-LOG-mvp-cloud-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-cloud-1031.md | exit card is in this file before product code | depends on none | general
- confirm-base | read-only git | origin/main has no scripts/pfy_build_cloud.py | depends on exits | general
- skeleton | scripts/pfy_build_cloud.py, tests/test_pfy_build_cloud.py | no task exits 2; --dry-run exits 0, starts no grok, writes no branch, receipt status DRY-RUN and commit null | depends on confirm-base | general
- dispatch | scripts/pfy (build help and cmd_build only), tests/test_pfy_build_cloud.py | -p reaches scripts/pfy_build_p.py; a positional task reaches scripts/pfy_build_cloud.py | depends on skeleton | general
- pass | scripts/pfy_build_cloud.py, tests/test_pfy_build_cloud.py | fake grok PASS: branch and commit match the receipt, caller porcelain unchanged | depends on dispatch | general
- retries | same paths | gate red then PASS; review reject then accept; final reject leaves no branch | depends on pass | general
- no-change | same paths | gate tail is in the second prompt; spent no-change exits 1 with no branch; a gitignored extra file is not in the commit | depends on retries | general
- failures | same paths | rate-limit exit 4; auth exit 1; dirty caller stays dirty; SIGTERM interrupted; reap writes ABORTED and does not signal a local-only pid | depends on no-change | general
- gitignore | .gitignore one line, tests | pipelines/dogfood/build-cloud/ ignored; tests.test_pfy_build_p and the new module green | depends on failures | general
- handoff | docs/ops/HANDOFF-mvp-cloud-1031.md, this log | state line, push, no merge | depends on gitignore | general

Risks:
- Parallel lanes share the host. Mitigation: owned files only, no Ollama, targeted tests with nice -n 19, never signal a process this run did not start.
- Receipt or log could capture a token. Mitigation: redact before write, never open auth.json, never read ~/.grok/auth.json.
- A cloud commit could include a gitignored file or a caller dirty file. Mitigation: add only the reviewed relative paths, then require git diff --cached --name-only to match; worktree is detached from the caller checkout.
- Caller hooks or gpgsign could hang or add files. Mitigation: commit with commit.gpgsign=false and an empty core.hooksPath inside the worktree. Do not edit caller git config.

Confirmed: origin/main does not contain scripts/pfy_build_cloud.py or pfylib/build_preflight.py (git fetch at launch). No remote branch has scripts/pfy_build_cloud.py. The runner is new work.

exits | 9903e70 | none (docs only, before code) | PASS
confirm-base | 9903e70 | origin/main has no scripts/pfy_build_cloud.py | PASS
skeleton | 62d7e3a | nice -n 19 python3 -m unittest tests.test_pfy_build_cloud (3 tests OK) | PASS

state: IN PROGRESS | tests: tests.test_pfy_build_cloud 3 OK | files: 2 | err: none
