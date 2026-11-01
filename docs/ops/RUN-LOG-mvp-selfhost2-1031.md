# Run log: mvp-selfhost2-1031

Launch: 2026-10-31T23:26:06Z
Wall cap: 2026-11-01T07:26:06Z (8 hours from launch). Sunday 2026-11-02T02:00Z is later, so the 8 hour cap wins.
Stop new items by 2026-11-01T07:06:06Z so the handoff has 20 minutes.
Host at launch: MemAvailable 52068896 KiB, 32 cores, load 4.97 4.41 4.34. Pressure line is MemAvailable under 16 GiB or load over 64 for 5 minutes.
Branch: bot/mvp-selfhost2-1031. Base: origin/bot/mvp-integrate-1031. Tip at launch: c5d81bd.

LOOP EXIT CARD
Goal (success criteria): at least 10 real open product items, each built by cloud ./pfy build (never --local), reviewed by this lane, and cherry-picked only when the diff is accepted. Each landed item has a behavior or fail/recover test when code changed, a commit, a push, and one run-log line with receipt status, attempts, wall, review verdict, this lane's verdict, and landed SHA. Then keep taking the next fitting gap until an exit fires.
1 Goal met:                  10 accepted items pushed, handoff written, and no further fitting gap remains (lane empty). Ten items alone do not stop the loop.
2 Turn cap:                  16 build attempts. A skip counts. After 16, write the handoff even if fewer than 10 landed.
3 Budget cap:                cloud Grok only. No --local, no Ollama, no 127.0.0.1:11434. One ./pfy build per attempt. Do not retry the same task after two identical failures.
4 Wall clock:                2026-11-01T07:26:06Z. No new item after 2026-11-01T07:06:06Z.
5 No-progress:               the same failure twice with no new information, or 3 items skipped in a row. Record and stop.
6 Human interrupt:           user stop. No question stops the lane. A conservative choice goes in the decisions file.
7 Error threshold:           3 consecutive build or test failures that are the same error. Stop.
8 External event:            stop an item when origin/main or the integrate base already contains the change. Skip that item. Do not stop the lane for one duplicate.
Loop type:                   goal
Human gate:                  no merge, no PR, no tag. Push only bot/mvp-selfhost2-1031. This lane is the reviewer that accepts or rejects each cloud commit before cherry-pick.

Drop-in exits (checked before every item):
1. Wall cap above. Leave 20 minutes for the handoff.
2. Lane empty: no remaining item that fits these rules.
3. No progress: same failure twice with no new information, or 3 skips in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this change. Record and skip that area. Do not stop the lane.

Overview: More real product work built by ./pfy build. Read the mvp-selfhost-1031 report and handoff, and the live mvp-backlog-burn-1031 branch, and do not repeat their items. Pick open rows from docs/TODO.md and the backlog. For each, run cloud ./pfy build, read the diff, and cherry-pick only an accepted commit onto this branch with a Built-by trailer and the receipt. Record runner friction for mvp-cloudfix-1031. Do not run scripts/pregate.sh. Pregate at the end only if the GitHub runner is idle and the heavy lock is free.

Phases:
- exits | docs/ops/RUN-LOG-mvp-selfhost2-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-selfhost2-1031.md | exit card is in this file before any ./pfy build | depends on none | general
- survey | read-only git and docs/TODO.md | a candidate list that selfhost-1031 and backlog-burn-1031 did not take, and that parallel lanes do not own | depends on exits | general
- items | product files the chosen tasks touch, plus their tests, plus this run log | each accepted build is cherry-picked, tested, and pushed | depends on survey | general
- handoff | docs/ops/HANDOFF-mvp-selfhost2-1031.md, this log | state line, push, no merge | depends on items | general

Risks:
- Parallel lanes can edit the same product files. Mitigation: read their drop-ins and live branches before each item and skip a path another lane owns. Record a cross-lane request instead of editing it.
- A cloud build can wander, touch secrets, or change files outside the task. Mitigation: read the full diff. Reject and do not cherry-pick. The cloud branch stays unmerged.
- A receipt or log can capture a token. Mitigation: never open ~/.grok/auth.json. Redact before any write. Do not print secret values.
- Host pressure from other lanes. Mitigation: check MemAvailable and load before every item. Targeted tests only, niced. No full discover, no docker, no pregate until the end, and only if the runner is idle.
- The cloud review verdict can be wrong. Mitigation: this lane's verdict decides the cherry-pick. Log every disagreement as a cloudfix finding.

Named skills write-loop-exits-first and repo-handoff-doc-required are not files in this worktree or ~/.grok/skills. This card, the drop-in exit list, and docs/ops/HANDOFF-mvp-selfhost2-1031.md are the binding. Decision logged.

Builds run one at a time in this worktree. Parallel sub-agents would race one index and one branch. The project-map agent may write only .project-map/.

Item log (append one line each):
item | commit | tests | result

Survey skips, recorded before item 01, not a no-progress streak: T-0091 voice shelved; T-0094 local TTS; T-0081 docker cage; T-0064 EBUSY parked; T-0043 write-guard parked; T-0062 Laguna hardware; T-0046 AgenC already rejected by ADR-0010; T-0016 colibri needs OQ-0008 and hardware; T-0005 stage letter is OQ-0003. Not repeated: the 13 selfhost accepts, the 2 selfhost rejects (smolvm t1 and the bad symlink oracle), the 6 backlog-burn accepts, and dogfood2's tree-sig copies, home sigs, receipt tests, timeout labels, daemon stop, and pregate orphans. No cache-tree hash of smoke_149 or smoke_109. No edit of runner, pregate, scripts/pfy, catalog_stage_eval, or enterable files.

01 ad-snap | 4a0fe4e | tests.test_agentdescent_snap tests.test_agentdescent_trial_harness 74 OK | PASS receipt, attempts 1, wall 457s, review accept, human accept. Cloud SHA 35b7585.
02 kolibri-receipt A | none | worktree gate OK, archive recheck FAIL on tests.test_x_intake_smoke_103_111_receipts | FAIL receipt, attempts 3, wall 1866s, review accept on the small write() (attempts 1 and 3), review reject on a git-init side effect (attempt 2), human accept of the small diff, no SHA. Retry with only the behavior test.
02 kolibri-receipt | cdf4d68 | tests.test_kolibri_receipt_absolute tests.test_x_intake_smoke_103_111_receipts 2 OK | PASS receipt, attempts 1, wall 135s, review accept, human accept. Cloud SHA 7a79465.
03 typed-receipt | 36bc071 | tests.test_typed_decisions_receipt_absolute 1 OK | PASS receipt, attempts 1, wall 167s, review accept, human accept. Cloud SHA a586ad1.
