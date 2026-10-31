# pfy local build MVP-3: resume run 2 (t4 to t6, then REPORT)

Follow the orchestrator skill (`~/.grok/skills/orchestrator/SKILL.md`). This run is pre-authorized and autonomous. Do not ask questions. Decide conservatively, log each decision as one line in `docs/ops/AUTONOMOUS-DECISIONS-2026-10-30.md`, and keep going.

Read `docs/build-dropins/pfy-local-build-mvp3.md` first. Its hard rules, exits, Part 2 method, report spec and deliverables all still apply, except where this file changes them. Then read `docs/ops/RUN-LOG-mvp3-review-retry.md` and `docs/ops/HANDOFF-mvp3-review-retry.md`.

## State at resume

- Branch `bot/mvp3-review-retry`. Part 1 (the review loop, `b25fc35`) is done and the suite is green. Do not redo Part 1 and do not change `scripts/pfy_build_local.py` unless a trial exposes a real bug. If you change it, run the full suite before you continue, and record why.
- t1, t2 and t3 are done and committed (`eval/mvp3/results`, `eval/mvp3/patches`). Do not re-run them.
- Run 1 died at t4 because the grok CLI ended its background trial task after 600 s. t4 has no result. t5 and t6 never started.

## Hard rules (repeat)

No sudo. Make new commits only and push only `bot/mvp3-review-retry`. No PR, no merge, no force push. Do not use `/tmp`; scratch goes under this worktree's `tmp/`. Never print secrets and never read `~/.grok/auth.json`. No em dashes. Use only `qwen3.6:35b` and keep the 32 GiB MemAvailable+SwapFree floor. Never stop or signal processes you did not start. Unload only our own model, and only when it is the only one loaded.

## Fresh wall cap

Before the first new model call, move `tmp/mvp3-runs/first-model-call.txt` to `tmp/mvp3-runs/run1-archive/first-model-call.run1-original.txt` if it still exists. Run 1's copy is already archived there. The runner writes a new clock at the first new `arm` call, and that file is the 3h cap for run 2. Record the new start and cap times (UTC and PDT) in the run log.

## Running the arms so the CLI cannot end them

Run the arms one at a time, in this order: `t4-timeout-substep`, `t5-receipts-outside-repo`, `t6-tree-sig-three`.

Do not leave an arm as a CLI background task that you then stop waiting on. For each arm:

1. Check the exits and the memory floor. If an exit fires, mark the remaining tasks as not-run with the reason, and go straight to the report.
2. Start the arm as a detached process with its own log and pid file under `tmp/mvp3-runs/`:
   `setsid nohup python3 eval/mvp3/run_trial.py arm L <task> > tmp/mvp3-runs/run2-<task>.stdout 2>&1 < /dev/null & echo $! > tmp/mvp3-runs/run2-<task>.pid`
3. Poll it in the foreground with bounded waits (for example `sleep 240`, then check the pid, the stdout tail, `ollama ps` and free memory). Keep polling until the stdout shows `ARM_DONE`, or the pid is gone. Never end your turn while an arm is running.
4. Then unload `qwen3.6:35b`, but only if it is the only loaded model (Ollama API `keep_alive: 0`).
5. Review the result as a human reviewer would, as in the original drop-in. Append the per-task line to the run log, commit the result JSON and patch, and push.

The per-arm wrapper allows up to 3 attempts at 1200 s each. If an arm pid outlives 4500 s, or its process group outlives the runner's timeout by more than 60 s, treat it as a lockup exit. Stop only the process group you started, and record it.

## After t6 (or an exit)

Write `eval/mvp3/REPORT.md` per the original drop-in. It covers all 6 tasks (t1 to t3 from run 1, t4 to t6 from run 2) and compares against MVP-2 local (gate 5/6, review 4/6, 1694.0 s) and MVP-2 cloud (6/6, 6/6, 583.6 s). It must note honestly that the trial ran in two sessions, why, and that each session had its own 3h cap.

Then update `docs/ops/HANDOFF-mvp3-review-retry.md`: status, results, what is left, and the gate (Tester plus Reviewer, because Part 1 changes runtime). Finish the run log with a final `state:` line. Commit and push. Do not open a PR and do not merge.

## Exits

1. Done: t4 to t6 have results, and the report and handoff are pushed.
2. The 3h wall cap from run 2's first model call.
3. Memory or lockup signs, as listed in the original drop-in.
4. No progress: the same failure twice with no new information.

On any exit, still write the report, run log and handoff with what exists, then push.
