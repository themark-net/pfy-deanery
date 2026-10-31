# MVP-3 trial: local build with review-and-retry

Branch `bot/mvp3-review-retry`. Product change is the review loop in `b25fc35` (`scripts/pfy_build_local.py`). Run 2 did not edit that file. Every arm used base `997d89264495861a178713ccf7d4447ea828afc4`, model `qwen3.6:35b` through Ollama, `./pfy build --local` with review on and `--retries 2`. No cloud arm. Patches under `eval/mvp3/patches/` are evidence. They are not landed.

## Two sessions

The six tasks did not run in one sitting.

Run 1 first model call was 2026-10-30T17:50:52Z (2026-10-30 10:50:52 PDT). Its cap was 2026-10-30T20:50:52Z (13:50:52 PDT). t1, t2, and t3 finished and were committed. At 11:13 PDT the grok CLI hit its 600 s background-wait limit and stopped the trial runner during t4. That was a CLI limit, not a memory breach and not a lockup. The inner build left a PASS receipt that the runner never reviewed. It does not count. It is archived under `tmp/mvp3-runs/run1-archive/t4-receipts-orphan`.

Run 2 first model call was 2026-10-31T03:07:13Z (2026-10-30 20:07:13 PDT). Its own cap was 2026-10-31T06:07:13Z (2026-10-30 23:07:13 PDT). t4, t5, and t6 ran one at a time as detached processes with a foreground poll, and all three finished inside that cap. t6 ended about 2026-10-31T04:09Z. The gap between the sessions is outside both caps.

## Result

No-go for making `./pfy build --local` with the loop the default on build-only runs.

| Arm | Gate pass | Review accept | Wall | Attempts | Timeouts | Memory blocks |
|-----|-----------|---------------|------|----------|----------|---------------|
| MVP-3 local, loop | 5/6 | 5/6 | 3859.9 s | 9 total | 0 | 0 |
| MVP-3 local, human | 5/6 | 4/6 | 3859.9 s | 9 total | 0 | 0 |
| MVP-2 local | 5/6 | 4/6 | 1694.0 s | 1 each | 0 | 0 |
| MVP-2 cloud | 6/6 | 6/6 | 583.6 s | 1 each | 0 | 0 |

Loop accept counts a final `PASS` (the review returned accept, or the gate never reached review). Human accept is a reading of the landed diff. t4 is a gate FAIL, so both reviews reject it. t5 is a gate PASS the loop accepted and the human rejected.

## Per task

Diffs below are `git diff` against the MVP-2 base, so they include the planted acceptance test. Agent-only stats are in the notes.

| Task | Level | Gate | Loop | Human | Attempts | Wall | Per attempt | Diff vs base |
|------|-------|------|------|--------|----------|------|-------------|--------------|
| t1 smolvm stderr first | trivial | PASS | accept | accept | 1 | 145.1 s | 144.4 s PASS | 2 files, +46/-5 |
| t2 tree_sig 119 | trivial | PASS | accept | accept | 1 | 143.7 s | 143.0 s PASS | 2 files, +60/-3 |
| t3 daemon stop fail | medium | PASS | accept | accept | 1 | 421.2 s | 416.5 s PASS | 2 files, +92/-1 |
| t4 timeout substep | medium | FAIL | reject | reject | 3 | 2203.5 s | 982.4 s, 205.9 s, 1014.8 s, all no-change | 1 file, +95/-0 (plant only) |
| t5 receipts outside repo | slightly hard | PASS | accept | reject | 1 | 581.6 s | 580.8 s PASS | 4 files, +99/-2 |
| t6 tree_sig three | slightly hard | PASS | accept | accept | 2 | 364.8 s | 89.9 s no-change, 274.2 s PASS | 4 files, +104/-9 |

Gaming: none. The agent did not weaken a gate or skip a test. Scope creep: t5 only, and it is the runner's commit, described below. Every canonical gate found the planted test unchanged. No arm timed out. No arm was stopped for memory.

Supervisor samples of MemAvailable+SwapFree stayed at or above 38.879 GiB (t6). The floor is 32 GiB. t4's receipt `min_available_gb` is 27.494. That field is MemAvailable alone, the runner kills at 16 GiB, and the 120 s sum samples on that arm stayed at or above 44.365 GiB. It is not counted as a memory block.

### t4 and t5

Neither miss was caught by the review and fixed by a retry.

t4 produced no diff. Three attempts read the smoke and the tests, named the right edit (`timeout_reason` at `new` and at `fest --version`, plus the two assertion strings), and never wrote a file. The tool trace is Read, Grep, and Glob. The review model never ran, because a no-change attempt has no diff to review. The planted gate still fails the two new assertions (`overtime timeout after 0.4s`, `festival timeout after 0.4s`). MVP-2 local t4 was green and too broad (the whole overtime block labeled `new`). This run did not reproduce that patch and did not fix the task.

t5 wired both modules on the first attempt. Each `setUp` makes a temp directory, `_env` sets `PFY_SMOKE_RECEIPT_DIR`, and `_receipt` reads that directory. That matches `tests/test_x_intake_smoke_112_114.py`, aside from the name `_RECEPTS` and no `tearDown`. The wiring check passed. The model review accepted and said no other file changed. The commit `4b017e4` also adds `pipelines/smoke/kander/latest.json`. That path is gitignored. `git status` hid it from the scope check. `git add -A -f` then committed the receipt the red gate had already written. The task says only the two test modules may change, and those tests must not create that receipt. Loop accept, human reject. This is a false accept. It is not an agent cheat.

### t6 retry

Attempt 1 was no-change (89.9 s). Attempt 2 copied the content hash into the three named files. Each `tree_sig` still returns None when the path is missing, hashes file bytes in 1 MiB chunks, writes `:dir` for other entries, and writes `:unreadable` on `OSError`. Commit `9b61b75` is those three files only. Loop and human both accept. The retry did what it should on this task.

### Accepted diffs

t1 checks stderr for `Pulling image` before the stdout cache line, and a cache-only stdout line still returns. The agent edited only `smoke_109_111.py`. t2 and t6 match the `smoke_122_124.py` content hash, including `:dir` and `:unreadable`. t3 returns 1 when daemon stop times out and the lock is not alive, and it keeps the step record. t6 is the one above.

### False rejects

None. The loop did not reject a patch the human accepted. MVP-2 local had accepted t1, t2, t3, and t6. The loop accepted those four as well. The one disagreement is t5, where the loop accepted a tree the human rejects.

## Task copies

`eval/mvp3/tasks/` differs from `eval/mvp2/tasks/` only by a `files:` line on each task, plus this line on t5:

```text
require: PFY_SMOKE_RECEIPT_DIR in tests/test_x_intake_smoke_117_118.py, tests/test_x_intake_smoke_119_121.py
```

No other hint was added.

## What is still missing

The scope check reads `git status`. The commit then runs `git add -A -f`, which picks up gitignored files the status hid. t5 is the case. A review that only sees the status diff will accept a tree that contains the red gate's receipt. Recovery today is to read the commit, not only the attempt diff. `--no-review` does not close the hole, because the add is after the review.

t4 still needs a model that writes the narrow catch. Three no-change retries spent 2203.5 s and left the gate red. The MVP-2 failure mode (a green test with too broad a label) was not measured again.

Wall time got worse. 3859.9 s against MVP-2 local 1694.0 s and MVP-2 cloud 583.6 s. t4 is 2203.5 s of that.

## Go / no-go

No-go. Gate pass is still 5/6, human accept is still 4/6, and the run is slower. The loop did not fix t4, and it accepted t5's landed receipt. Keep `./pfy build --local` off the default for build-only runs until the commit and the scope check see the same files, and until a local t4 run lands the sub-step catch instead of an empty diff.

The gate for this branch is Tester plus Reviewer at the pinned SHA, because Part 1 changes runtime. No PR and no merge from this run.
