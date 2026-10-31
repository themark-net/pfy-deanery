# RUN-LOG mvp-integrate-1031

Branch `bot/mvp-integrate-1031`. Base `origin/main`. Worktree `~/DEVELOP/pfy-mentat/tmp/mvp-integrate-1031`. No rebase, no force-push, no PR, no merge to main, no tag. No local model. No `--local` on the demo.

Launch: 2026-10-31T20:42:00Z. Wall cap: 2026-11-01T04:42:00Z (8 hours), which is earlier than Sunday 2026-11-01 18:00 PT / 2026-11-02T02:00Z. Stop new items by 2026-11-01T04:22:00Z so the handoff has 20 minutes. Host at launch: 32 cores, MemAvailable about 62 GiB, load about 3.5 (threshold is 64).

Overview: Merge eight origin branches in order when they exist, run the unittest suite once under the heavy lock, optionally switch the cloud runner to the shared classifier when that edit is under 40 lines, then run one real cloud `./pfy build` on a temp fixture and record the receipt. Docs get one MVP note, one pending-handoff section, and one modules row. After the definition of done, take only further MVP gaps that fit this lane's owned files.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria): merge commits for every listed origin branch that exists, one flock suite with counts, one honest cloud demo receipt when both scripts exist, TODO note plus pending-handoff section plus modules row, handoff pushed. No Feature GO. Catalog HOLD unchanged.
1 Goal met:                  suite counts in the handoff; check_receipt.py exit recorded; git shows cloud/ at the receipt commit on the fixture when the demo PASSes
2 Turn cap:                  8 ordered items, then only owned-file gaps from MVP-PARALLEL-1031. Stop at the first exit.
3 Budget cap:                one real cloud ./pfy build. No second demo. No --local. No Ollama. No spend beyond that one call.
4 Wall clock:                2026-11-01T04:42:00Z, or 2026-11-02T02:00Z, whichever is first. Handoff buffer starts 20 minutes earlier.
5 No-progress:               same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:           user stop. Do not ask. Conservative default, one decisions line, continue.
7 Error threshold:           3 consecutive same failures, or the drop-in "same failure twice" rule, then stop
8 External event:            missing origin branch is skipped and logged, not polled. Do not wait hours.
Loop type:                   goal
Human gate:                  no merge to main, no PR, no tag. Push only this bot/ branch.
```

Drop-in exits (checked before every item):

1. Wall cap with the 20 minute handoff buffer above.
2. Lane empty: no remaining item fits the owned files and these rules.
3. No progress: same failure twice with no new information, or 3 skipped items in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: a failure that also fails on the pre-merge base is recorded and that area is skipped. Do not stop the lane.

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-integrate-1031.md` are the binding.

## Phases

- exits | `docs/ops/RUN-LOG-mvp-integrate-1031.md`, `docs/ops/AUTONOMOUS-DECISIONS-mvp-integrate-1031.md` | exit card committed and pushed before any merge | none | lead
- merge | incoming branch files only, merge commits | each of the eight origin branches merged or logged missing, push after each success | exits | lead
- classifier | `scripts/pfy_build_cloud.py` only, under 40 lines | import `classify_cloud_failure` when both copies exist and the edit stays under 40 lines; else name `mvp-dedupe-1031` | merge | lead
- suite | no feature edits | one `nice -n 19 flock` unittest discover; targeted modules green when those files exist | merge | lead
- demo | `eval/mvp-1031/demo-receipt.json`, `eval/mvp-1031/REPORT.md` | one real `./pfy build` when runner and checker both exist; honest receipt even on rate limit or auth failure | suite | lead
- notes | `docs/TODO.md`, `docs/PENDING-HANDOFF.md`, `docs/modules/README.md` | one MVP note, one dated section, one row when `docs/modules/pfy-build.md` exists | demo or recorded skip | lead
- further | owned files only | next MVP gap from the plan that fits, until an exit | notes | lead
- handoff | `docs/ops/HANDOFF-mvp-integrate-1031.md`, this log | SHAs, skips, evidence, fail/recover, cross-lane, gate, next step, final `state:` line, push | earlier phases | lead

Merge order:

1. `origin/bot/backlog-catalog-1030`
2. `origin/bot/pfy-followups-1030`
3. `origin/bot/mvp3-review-retry`
4. `origin/bot/mvp-review-fix-1031`
5. `origin/bot/mvp-preflight-1031`
6. `origin/bot/mvp-surface-1031`
7. `origin/bot/mvp-eval-1031`
8. `origin/bot/mvp-cloud-1031`

Conflict rule: the round-1 owner named in the plan matrix wins. For `docs/TODO.md` and `docs/modules/pfylib.md`, keep both sides' facts. Do not drop a done row. One decisions line per conflict.

## Risks

- Shared host and the heavy lock: the full suite waits on `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`. Do not start a second discover. Do not signal processes this lane did not start.
- Cloud rate limit or auth failure: commit the receipt, mark the demo as not PASS, do not retry with `--local`, do not invent a green result.
- Conflict that rewrites a lane feature: resolve only the conflict hunk. A failure introduced by that resolution is fixed only inside that conflict.
- Parallel lanes: stay in this worktree and these owned writes. A needed edit outside that list becomes a cross-lane request, not a commit.
- One worktree: merges stay serial on the lead. Spawning agents onto this checkout would race the index and the push.

## Item log

Format: `item | commit | tests | result`

exits | 7bb1085 | none | exit card pushed before any merge
merge backlog-catalog-1030 | c75ebcf | none | merged, no conflict
merge pfy-followups-1030 | dc8fdb2 | none | conflict docs/modules/pfylib.md, both still-true facts kept
merge mvp3-review-retry | d97c4f6 | none | conflict docs/TODO.md, MVP-2 note and MVP-3 row kept
merge mvp-review-fix-1031 | 2c223bd | none | clean
merge mvp-preflight-1031 | b34143d | none | clean
merge mvp-surface-1031 | c17d4ef | none | clean
merge mvp-eval-1031 | 71fd74a | none | clean
merge mvp-cloud-1031 | 29bbad4 | none | clean
classifier import | d966e83 | nice -n 19 python3 -m unittest tests.test_pfy_build_cloud tests.test_build_preflight | 35 OK in 6.753s
suite | 444af7b | TMPDIR=$PWD/tmp nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t . | Ran 1048 in 668.761s, FAILED failures=2 skipped=16 (help contract, local-bench TMPDIR). Not rewritten
demo | a73e9ae | ./pfy build on tmp fixture; python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt.json | build exit 0, checker exit 0, PASS, review accept, commit ebef4238a7eff8f938747623f7920b3fde74e586
notes | 0338b67 | nice -n 19 python3 -m unittest tests.test_docs_hygiene tests.test_pfy_build_docs | 7 OK in 0.025s; one TODO note, one pending section, one modules row

prior-state: DONE | exit: lane empty | tests: discover 1048 ran, failures=2, skipped=16; checker exit 0 | files: merges, classifier import, demo receipt, report, TODO note, pending section, modules row, handoff | err: help contract and TMPDIR local-bench recorded, not rewritten

## PASS 2

Operator addendum, checked 2026-10-31T21:16:21Z. Pass 1 state above stays. This section is the pass 2 loop. MemAvailable about 60 GiB. Load about 4.7 on 32 cores. Wall cap still 2026-11-01T04:42:00Z. Handoff buffer still 2026-11-01T04:22:00Z. No pregate in this pass. The operator runs pregate on the final tip.

Overview: Fetch origin. Merge newer tips of the eight pass-1 branches, then the pass-2 lane branches that exist, in the listed order. Skip a missing branch. Do not merge `bot/mvp-selfhost-1031`. Resolve `scripts/pfy_build_cloud.py` in favor of cloudfix when that branch is merged, with one import and no inline classifier. Run the suite once under the lock. Run one real cloud demo on a small real backlog task in a throwaway clone. Commit the receipt even if it does not PASS. Update the handoff with the final tip SHA and push.

## LOOP EXIT CARD PASS 2

```text
LOOP EXIT CARD PASS 2
Goal (success criteria): merge commits for every listed pass-2 origin branch that exists, including newer tips of the eight pass-1 branches; cloudfix owns scripts/pfy_build_cloud.py with exactly one classify_cloud_failure import; one flock suite with counts; one honest demo-2 receipt and a Pass 2 report section; handoff names the final tip SHA. No Feature GO. No pregate by this lane. No merge of bot/mvp-selfhost-1031.
1 Goal met:                  suite counts in the handoff; check_receipt.py exit recorded for demo-receipt-pass2.json; REPORT.md Pass 2 section has command, task, wall time, exit, attempts, branch, commit, review verdict, human verdict, and DoD lines 1 to 6
2 Turn cap:                  the pass-2 merge list, the classifier proof, the suite, demo 2, then the handoff. Stop at the first exit.
3 Budget cap:                one real cloud ./pfy build for demo 2. No second cloud call. No --local. No Ollama.
4 Wall clock:                2026-11-01T04:42:00Z, or 2026-11-02T02:00Z, whichever is first. Handoff buffer starts 2026-11-01T04:22:00Z. Checked at 2026-10-31T21:16:21Z, inside the cap.
5 No-progress:               same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:           user stop. Do not ask. Conservative default, one decisions line, continue.
7 Error threshold:           3 consecutive same failures, or the drop-in "same failure twice" rule, then stop
8 External event:            a missing origin branch is skipped and logged, not polled. A lane still running is merged at its current pushed tip and the SHA is recorded.
Loop type:                   goal
Human gate:                  no merge to main, no PR, no tag, no force push. Push only bot/mvp-integrate-1031.
```

Drop-in exits (checked before every pass-2 item):

1. Wall cap with the 20 minute handoff buffer above.
2. Lane empty: the pass-2 list, the classifier proof, the suite, demo 2, and the handoff are done, or no remaining item fits the owned files.
3. No progress: same failure twice with no new information, or 3 skipped items in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: a failure that also fails before this pass's change is recorded and that area is skipped. Do not stop the lane. A failure another lane owns is recorded with that lane. Fix only a failure this pass's conflict resolution caused.

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are still not files. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-integrate-1031.md` stay the binding.

## Pass 2 phases

- exits-2 | this log, `docs/ops/AUTONOMOUS-DECISIONS-mvp-integrate-1031.md` | pass-2 exit card committed and pushed before any pass-2 merge | none | lead
- merge-2 | incoming branch files only, merge commits | each listed origin branch merged at its current tip or logged missing; push after each success; selfhost not merged | exits-2 | lead
- classifier-2 | `scripts/pfy_build_cloud.py` only when the merge does not already leave one import | cloudfix version wins; exactly one import; no inline duplicate; `tests.test_pfy_build_cloud*` and `tests.test_build_preflight` | merge-2 | lead
- suite-2 | no feature edits | one `TMPDIR=$PWD/tmp nice -n 19 flock` unittest discover; conflict-caused failures fixed inside the conflict; other failures recorded with the owning lane | merge-2 | lead
- demo-2 | `eval/mvp-1031/demo-receipt-pass2.json`, `eval/mvp-1031/REPORT.md` | one real `./pfy build` on `tmp/demo2-target`; honest receipt even when it does not PASS | suite-2 | lead
- handoff-2 | `docs/ops/HANDOFF-mvp-integrate-1031.md`, this log | final tip SHA, skips, evidence, fail/recover, cross-lane, gate, next step, final `state:` line, push. No pregate | demo-2 | lead

Pass 2 merge order:

1. Newer tips: `origin/bot/backlog-catalog-1030`, `origin/bot/pfy-followups-1030` (c0d38af or newer), `origin/bot/mvp3-review-retry` (d624535 or newer), `origin/bot/mvp-review-fix-1031`, `origin/bot/mvp-preflight-1031`, `origin/bot/mvp-surface-1031`, `origin/bot/mvp-eval-1031`, `origin/bot/mvp-cloud-1031`
2. `origin/bot/mvp-cloudfix-1031`
3. `origin/bot/mvp-review-fix2-1031`
4. `origin/bot/mvp-intfix-1031`
5. `origin/bot/mvp-followups-fix2-1031`
6. `origin/bot/mvp-tmpclean-1031`
7. `origin/bot/mvp-docs-1031`
8. `origin/bot/mvp-mutate-cloud-1031`
9. `origin/bot/mvp-mutate-review-1031`
10. `origin/bot/mvp-realfail-1031`
11. `origin/bot/mvp-realfail2-1031`
12. `origin/bot/mvp-sixtask-1031`
13. `origin/bot/mvp-dogfood-1031`
14. `origin/bot/mvp-dogfood2-1031`
15. `origin/bot/mvp-gom-dogfood-1031`

Not merged: `origin/bot/mvp-selfhost-1031` (Mark cherry-picks from it).

Conflict rule: round-1 owner wins when the plan matrix names one. For `docs/TODO.md` and `docs/modules/pfylib.md`, keep both sides' facts. Do not drop a done row. For `scripts/pfy_build_cloud.py`, cloudfix wins: one import, no inline duplicate classifier. One decisions line per conflict.

## Pass 2 risks

- Shared host and the heavy lock: the full suite waits on `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`. Do not start a second discover. Do not signal processes this lane did not start.
- A branch whose lane is still running is merged at the fetched tip. Later commits on that branch are not polled.
- Cloud rate limit or auth failure on demo 2: commit the receipt, mark the demo as not PASS, do not retry with `--local`, do not invent a green result.
- Classifier overlap: do not keep both the pass-1 import commit and an inline copy. Cloudfix's file is the source when that branch merges.
- Demo 2 target is a throwaway clone under `tmp/demo2-target`. The integrate branch is not the task target. Do not commit `tmp/`.
- One worktree: merges stay serial on the lead.

## Pass 2 item log

Format: `item | commit | tests | result`

exits-2 | 6eb5d83 | none | pass 2 exit card pushed before any pass 2 merge
merge pfy-followups-1030 | 0f478ed | none | tip c0d38af, clean
merge backlog-catalog-1030 | already e04e926 | none | no new commits
merge mvp3-review-retry | already d624535 | none | pin already in HEAD
merge mvp-review-fix-1031 | already 1140434 | none | no new commits
merge mvp-preflight-1031 | already 100348d | none | no new commits
merge mvp-surface-1031 | already 30cdd24 | none | no new commits
merge mvp-eval-1031 | already 1768037 | none | no new commits
merge mvp-cloud-1031 | already d94d2b6 | none | no new commits
merge mvp-cloudfix-1031 | 52354f0 | none | tip 57c6dad, conflict scripts/pfy_build_cloud.py, took cloudfix file, one import
merge mvp-review-fix2-1031 | 21b8b57 | none | tip 23ea0cd, clean
merge mvp-intfix-1031 | 51eb0b3 | none | tip 13e967d drop-in, clean
merge mvp-followups-fix2-1031 | 808bc6c | none | tip c328da2, clean
merge mvp-tmpclean-1031 | 0287ffb | none | tip db1ca11 drop-in, clean
merge mvp-docs-1031 | 9af137d | none | tip bc6d5e0 drop-in, clean
merge mvp-mutate-cloud-1031 | 791c682 | none | tip 6e34a1b drop-in, clean
merge mvp-mutate-review-1031 | 280e12d | none | tip a6fbf18 exit card, clean
merge mvp-realfail-1031 | 06fa79c | none | tip d09647a, clean
merge mvp-realfail2-1031 | 074f5e9 | none | tip 884a16a drop-in, clean
merge mvp-sixtask-1031 | 9dbf718 | none | tip a8a7ca4, clean
merge mvp-dogfood-1031 | 4d0991e | none | tip e404b42, clean
merge mvp-dogfood2-1031 | 94612ca | none | tip b6d5b76 drop-in, clean
merge mvp-gom-dogfood-1031 | 6921552 | none | tip 86639b7 exit card, clean
merge mvp-cloudfix-1031 catch-up | 152448f | none | tip f316036, clean, still one import
merge mvp-review-fix2-1031 catch-up | 284c2c9 | none | tip 187efde, clean
merge mvp-intfix-1031 catch-up | 3fa6062 | none | tip 7209ff2 exit card, clean
merge mvp-sixtask-1031 catch-up | 31438fd | none | tip dbf104a, clean
merge mvp-docs-1031 catch-up | 135eebb | none | tip 981f1d7 exit card, clean. Freeze. selfhost 62ae324 not merged
classifier-2 | 135eebb | nice -n 19 python3 -m unittest tests.test_pfy_build_cloud tests.test_build_preflight | 54 OK in 10.080s, one import, no inline copy
suite-2 | 135eebb | TMPDIR=$PWD/tmp nice -n 19 flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock python3 -m unittest discover -s tests -t . | Ran 1098 in 731.925s, FAILED failures=2 skipped=16. Same help contract and TMPDIR local-bench. Not rewritten
demo-2 | 7997dd6 | ./pfy build on tmp/demo2-target; python3 eval/mvp-1031/check_receipt.py eval/mvp-1031/demo-receipt-pass2.json | build exit 0, checker exit 0, PASS, review accept, human yes, commit 535d000075744709b2752cec7511d087801f2aa5, wall 91s, attempts 1

prior-state: DONE | exit: goal met | tests: discover 1098 ran, failures=2, skipped=16; cloud+preflight 54 OK; checker exit 0 | files: pass 2 merges, cloudfix conflict kept their runner, demo-receipt-pass2.json, REPORT pass 2, handoff 7997dd6, this stamp is the tip | err: help contract and TMPDIR local-bench recorded, not rewritten. selfhost not merged. pregate not run by this lane

## PASS 3

Operator addendum, checked 2026-10-31T23:26:00Z. Pass 1 and pass 2 prior-state lines stay. Pass 2 tip `0c3f133` passed pregate (operator: 6 pass, 1 skip). HEAD at this card is `f10926d` (reopen plus the pass 3 drop-in). `origin/main` `c0d38af` is already in this branch. MemAvailable about 52 GiB. Load about 5.0 on 32 cores. Wall cap still 2026-11-01T04:42:00Z. Handoff buffer still 2026-11-01T04:22:00Z. About 5 hours remain. No pregate in this pass. The operator runs pregate on the final tip. `Runner.Worker` was running at the check. This lane does not run pregate anyway.

Overview: Fetch origin. Merge the pass 3 lane branches that exist, in the listed order, each at the tip present when this lane reaches it. Skip a missing branch. Do not merge `bot/mvp3-followups-1031`. Do not merge `bot/mvp3-review-retry` past what is already in. On `scripts/pfy_build_cloud.py`, keep cloudfix structure and dogfood-fix behavior, with one classifier import and no inline copy. After each merge, run the targeted tests named in that lane's handoff. Fix only integration breakage with a small commit. Run the suite once under the lock. Target 0 failures. Record a failure that belongs to a lane. Run one real cloud demo on a 3 to 5 file backlog task in a throwaway clone. Commit the receipt even if it does not PASS. Record GO or NO-GO for cloud-default daily use from the sixtask-int report when that file is present. Update the handoff with the pass 3 tip SHA and push.

## LOOP EXIT CARD PASS 3

```text
LOOP EXIT CARD PASS 3
Goal (success criteria): merge commits for every listed pass-3 origin branch that exists; dogfood-fix behavior kept on the cloudfix cloud runner; one flock suite with counts and a target of 0 failures; one honest demo-3 receipt and a Pass 3 report section; GO or NO-GO copied from the sixtask-int report when present; handoff names the pass 3 tip SHA. No Feature GO. No pregate by this lane. No merge of bot/mvp3-followups-1031. No extra merge of bot/mvp3-review-retry.
1 Goal met:                  suite counts in the handoff; check_receipt.py exit recorded for demo-receipt-pass3.json; REPORT.md Pass 3 section has command, task, wall time, exit, attempts, branch, commit, review verdict, human verdict, and the sixtask-int GO or NO-GO line
2 Turn cap:                  the pass-3 merge list with each lane's targeted tests, the suite, demo 3, then the handoff. Stop at the first exit.
3 Budget cap:                one real cloud ./pfy build for demo 3. No second cloud call. No --local. No Ollama.
4 Wall clock:                2026-11-01T04:42:00Z, or 2026-11-02T02:00Z, whichever is first. Handoff buffer starts 2026-11-01T04:22:00Z. Checked at 2026-10-31T23:26:00Z, inside the cap.
5 No-progress:               same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:           user stop. Do not ask. Conservative default, one decisions line, continue.
7 Error threshold:           3 consecutive same failures, or the drop-in "same failure twice" rule, then stop
8 External event:            a missing origin branch is skipped and logged, not polled. A lane still running is merged at its current pushed tip and the SHA is recorded.
Loop type:                   goal
Human gate:                  no merge to main, no PR, no tag, no force push. Push only bot/mvp-integrate-1031.
```

Drop-in exits (checked before every pass-3 item):

1. Wall cap with the 20 minute handoff buffer above.
2. Lane empty: the pass-3 list, the suite, demo 3, and the handoff are done, or no remaining item fits the owned files.
3. No progress: same failure twice with no new information, or 3 skipped items in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: a failure that also fails before this pass's change is recorded and that area is skipped. Do not stop the lane. A failure another lane owns is recorded with that lane. Fix integration breakage with a small commit. Do not rewrite a lane feature.

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are still not files. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-integrate-1031.md` stay the binding.

## Pass 3 phases

- exits-3 | this log, `docs/ops/AUTONOMOUS-DECISIONS-mvp-integrate-1031.md` | pass-3 exit card committed and pushed before any pass-3 merge | none | lead
- merge-3 | incoming branch files only, plus a small integration fix when a conflict breaks a targeted test | each listed origin branch merged at its current tip or logged missing; targeted tests from that lane's handoff; push after each green step | exits-3 | lead
- suite-3 | no feature edits beyond an integration fix | one `TMPDIR=$PWD/tmp nice -n 19 flock` unittest discover; target 0 failures; a lane-owned failure is recorded with the lane name | merge-3 | lead
- demo-3 | `eval/mvp-1031/demo-receipt-pass3.json`, `eval/mvp-1031/REPORT.md` | one real `./pfy build` on `tmp/demo3-target`; honest receipt even when it does not PASS; sixtask-int GO or NO-GO recorded when that report exists | suite-3 | lead
- handoff-3 | `docs/ops/HANDOFF-mvp-integrate-1031.md`, this log | pass 3 tip SHA, skips, evidence, fail/recover, cross-lane, gate, next step, final `state:` line, push. No pregate | demo-3 | lead

Pass 3 merge order:

1. `origin/bot/mvp-review-fix2-1031`
2. `origin/bot/mvp-cloudfix-1031`
3. `origin/bot/mvp-dogfood-fix-1031` (keep cloudfix structure plus dogfood-fix behavior on `scripts/pfy_build_cloud.py`)
4. `origin/bot/mvp-mutate-preflight-1031`
5. `origin/bot/mvp-ci-cover-1031`
6. `origin/bot/mvp-realfail3-1031`
7. `origin/bot/mvp-followups-fix2-1031`
8. `origin/bot/mvp-selfhost-1031` (include it; 13 human-accepted cloud-built product commits)
9. `origin/bot/mvp-gom-dogfood-1031`
10. `origin/bot/mvp-sixtask-1031`
11. `origin/bot/mvp-sixtask-int-1031`
12. `origin/bot/mvp-tmpclean2-1031`
13. `origin/bot/mvp-backlog-burn-1031`

Not merged: `origin/bot/mvp3-followups-1031`. `origin/bot/mvp3-review-retry` stays at whatever is already in this branch. mvp3 is gated separately.

Conflict rule: round-1 owner wins when the plan matrix names one. For `docs/TODO.md` and `docs/modules/pfylib.md`, keep both sides' facts. Do not drop a done row. For `scripts/pfy_build_cloud.py`, keep cloudfix's structure plus dogfood-fix's behavior, exactly one `classify_cloud_failure` import, no inline duplicate. One decisions line per conflict.

## Pass 3 risks

- Shared host and the heavy lock: the full suite waits on `~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`. Do not start a second discover. Do not signal processes this lane did not start.
- A branch whose lane is still running is merged at the fetched tip. Later commits on that branch are not polled.
- Cloud rate limit or auth failure on demo 3: commit the receipt, mark the demo as not PASS, do not retry with `--local`, do not invent a green result.
- Dogfood-fix touches a few functions in the cloud runner. Do not take either file wholesale if both sides changed those functions. Keep cloudfix structure and add the dogfood-fix behavior.
- Selfhost is now in scope. Do not drop its product commits during a conflict.
- Demo 3 target is a throwaway clone under `tmp/demo3-target`. The integrate branch is not the task target. Do not commit `tmp/`.
- One worktree: merges stay serial on the lead.
- Suite target is 0 failures. The pass 2 help-contract and TMPDIR local-bench failures may still be present. If they still fail the same way, record them with the owning lane and do not rewrite those tests. Fix a new failure only when this pass's merge caused it.

## Pass 3 item log

Format: `item | commit | tests | result`

