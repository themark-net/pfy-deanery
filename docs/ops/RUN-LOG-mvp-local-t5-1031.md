# RUN LOG mvp-local-t5-1031

Lane: mvp-local-t5-1031
Branch: bot/mvp-local-t5-1031
Worktree: ~/DEVELOP/pfy-mentat/tmp/mvp-local-t5-1031
Base: origin/bot/mvp-integrate-1031 @ 0c3f133d4d2ea2bf104f6390416fa8d26f394803 (exists)
Launch: 2026-10-31T21:57:09Z
Wall cap: 2026-11-01T05:57:09Z (8h from launch). Sunday 2026-11-01 18:00 PT is 2026-11-02T02:00Z and is later, so the 8h cap binds.
Handoff reserve: stop new items at 2026-11-01T05:37:09Z (20 minutes left for the handoff).
Loop type: goal (measurable rerun) with a hard wall clock.
Model: qwen3.6:35b only, and only under `flock ~/DEVELOP/pfy-mentat/tmp/heavy-1030.lock`.

Preflight at launch (no model loaded by this lane):
- MemAvailable 61386572 kB (~58.5 GiB) + SwapFree 144 kB. Sum is over 32 GiB, so a later load is allowed.
- ollama ps listed no models.
- load 4.73 on 32 cores (under 2x cores).

Named skills `write-loop-exits-first` and `repo-handoff-doc-required` are not files in this worktree or `~/.grok/skills`. This card, the drop-in exit list, and `docs/ops/HANDOFF-mvp-local-t5-1031.md` are the binding. Decision logged.

## LOOP EXIT CARD

```text
LOOP EXIT CARD
Goal (success criteria):     t5 rerun recorded under eval/mvp-1031/local-rerun/ with receipt, exit code, and gitignored-path result. t4 only if t5 is recorded and the wall cap has room. Model this lane loaded is unloaded. Handoff pushed. No edits under scripts/ or pfylib/.
1 Goal met:                  note + receipt on disk, ollama ps clean for qwen3.6:35b (or recorded as pre-loaded by someone else), handoff committed
2 Turn cap:                  8 items. Ordered DoD is 5 steps. Further MVP gaps only after DoD and only inside owned files.
3 Budget cap:                local model only (qwen3.6:35b). No cloud build. No second model. One t5 run, one optional t4 run.
4 Wall clock:                2026-11-01T05:57:09Z, or 2026-11-02T02:00Z, whichever first. Leave 20 minutes to write the handoff.
5 No-progress:               same failure twice with no new information, or 3 items in a row skipped
6 Human interrupt:           user stop. Do not ask questions. Conservative decision, one line in the decisions file, keep going.
7 Error threshold:           3 consecutive same failure, or the drop-in "same failure twice" exit, whichever fires first
8 External event:            base branch missing, or review-fix (scope-commit-mismatch or equivalent) absent on the base: record and stop. Do not branch from main.
Loop type:                   goal
Human gate:                  no merge, no PR, no force-push. Push only bot/mvp-local-t5-1031.
```

## Drop-in exits (check before every item)

1. Wall cap: now >= 2026-11-01T05:37:09Z means write the handoff and stop. Hard stop 2026-11-01T05:57:09Z.
2. Lane empty: no owned-file MVP gap left after the DoD.
3. No progress: same failure twice with no new information, or 3 items skipped in a row.
4. Host pressure: MemAvailable under 16 GiB, or load over 64 for 5 minutes. Pause 10 minutes, then stop if it persists.
5. Red base: tests that fail on the base before this lane's change. Record them and skip that area. Do not stop the lane.

Also stop before load when MemAvailable + SwapFree is under 32 GiB, or when another ollama model is already loaded ("host busy").

## Phases

Overview: Rerun MVP-3 t5 (and t4 only if time remains) on the fixed `./pfy build --local` path. Add a flock-contract wrapper script, record the receipt, unload the model, and hand off. Do not change the default to local. Do not edit product code. A product bug is a cross-lane request.

Phases:
- exits-and-base | docs/ops/RUN-LOG-mvp-local-t5-1031.md, docs/ops/AUTONOMOUS-DECISIONS-mvp-local-t5-1031.md | exit card committed; base ref resolves | none | lead
- confirm-review-fix | read-only scripts/pfy_build_local.py | scope-commit-mismatch or an equivalent staged-set check is present on this base | exits-and-base | lead
- rerun-script | eval/mvp-1031/rerun_local.py and a behavior test beside it | no-task and unknown-task exit 2 and do not call ollama; commit and push | confirm-review-fix | lead
- run-t5 | eval/mvp-1031/local-rerun/ | one t5 run under the flock; receipt and NOTE.md committed and pushed | rerun-script | lead
- run-t4 | eval/mvp-1031/local-rerun/ | run t4 only if t5 is recorded and the handoff reserve is still ahead; otherwise the note says why | run-t5 | lead
- unload-and-handoff | docs/ops/HANDOFF-mvp-local-t5-1031.md, run log, decisions | qwen3.6:35b unloaded if this lane loaded it; handoff pushed; no merge | run-t4 | lead

Risks:
- Another lane holds the heavy lock or a model: do not start, record host busy, write the handoff, stop. Do not kill processes this lane did not start.
- t5 wall time eats the cap: skip t4, unload, handoff.
- Review-fix missing on the base: cross-lane request, stop. Do not patch scripts/pfy_build_local.py.
- A gitignored path lands in the t5 commit: record the rerun as failed. Do not rewrite the commit to hide it.
- Flock detection from inside the script is racy: the script refuses to run unless the operator passes an explicit under-flock flag. The drop-in wrapper is the contract.

Lead runs these phases in order. They share the run log and eval/mvp-1031, so they are not parallel workstreams. The project-map subagent may write only `.project-map/`.

## Review-fix check

`git grep scope-commit-mismatch origin/bot/mvp-integrate-1031 -- scripts/pfy_build_local.py` hits `_stage_reviewed`. A staged set that differs from the reviewed names returns `scope-commit-mismatch`, resets the index, and does not commit. The check is on the base at `0c3f133`. This lane does not patch `scripts/` or `pfylib/`.

## Item log

exits-and-base | 358de84 | none | base origin/bot/mvp-integrate-1031 at 0c3f133 present
confirm-review-fix | 358de84 | git grep scope-commit-mismatch on the base | staged-set check present, no product patch
rerun-script | b8b1003 | TMPDIR=tmp/scratch nice -n 19 python3 eval/mvp-1031/test_rerun_local.py | 11 tests OK, no model

## t5 launch

2026-10-31T22:13Z: heavy lock held by pregate c0d38af, with unittest discover and two more pregates waiting. t5 waits until 2026-11-01T03:57Z, then runs. This lane does not signal those processes.

Lock acquired 2026-10-31T22:52:31Z. Runner finished 2026-10-31T23:02:02Z. Gate PASS ok, attempts 1, review on, retries 2, model qwen3.6:35b, model_was_loaded false, unloaded true. Commit 4aa36fd34d1b9007bbf4887dcd729977aded3ee2. Diff is the two allowed test modules. No gitignored path was added. ollama ps was empty after the wrapper.

run-t5 | 771cc1f | receipt eval/mvp-1031/local-rerun/t5-receipts-outside-repo/receipt.json | PASS ok, diff has no new gitignored path, model unloaded
