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
