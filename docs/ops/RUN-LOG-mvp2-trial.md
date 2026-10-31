# RUN-LOG mvp2 trial

Historical note: "Do not merge to main" and the `bot/mvp2-trial` branch text below are historical. The report now lives on main.

Branch `bot/mvp2-trial`. Base for every arm is `997d89264495861a178713ccf7d4447ea828afc4`. No rebase, no force-push, no PR, no merge to main.

Overview: Six small build-only tasks, each with a red acceptance test planted in a fresh worktree, run on local `./pfy build --local` and on one headless cloud Build pass (one retry if the gate fails). Patches stay under `eval/mvp2/patches/`. The trial branch records specs, receipts, and the verdict.

Phases:
- specs | `eval/mvp2/tasks`, `eval/mvp2/gates`, `eval/mvp2/run_trial.py` | six specs, gates red in the sandbox on the base | none | lead
- local arms | `tmp/mvp2-runs` | one local receipt per task, sequential, one model | specs | lead
- cloud arms | `tmp/mvp2-runs` | one cloud gate per task, at most one retry, after the local model is idle | local arms | lead
- handoff | `eval/mvp2/REPORT.md`, `docs/ops/HANDOFF-mvp2-trial.md`, this log | verdict, push `bot/mvp2-trial` | cloud arms | lead

Risks: one GPU and a 32 GiB free-memory guard, so arms are serial. Swap is nearly full, so a second model is not started. Cloud is capped at six tasks plus one retry. Weekly budget percent is not readable here without printing tokens.

## Decisions

See `docs/ops/AUTONOMOUS-DECISIONS-2026-10-27.md`.

## Phases

- specs | proven red in bwrap on 997d892 (failures t1=1 t2=1 t3=1 t4=2 t5=1 t6=3, errors 0).
- local arms | done. Gate 5/6 (t5 FAIL). Review accept 4/6 (t4 reject: overtime timeout labels ls/set/settings as new; t5 reject: PFY_SMOKE_RECEIPT_DIR never set). Wall 1694.0 s. Model unloaded.
- cloud arms | done. Gate 6/6. Review accept 6/6. Wall 583.6 s. Attempts 1. modelCalls 51 across 6 sessions, turnCount 1 each. Weekly percent not readable.
- handoff | done. No-go for local as the default. Report `eval/mvp2/REPORT.md`. Handoff `docs/ops/HANDOFF-mvp2-trial.md`. Patches stay under `eval/mvp2/patches/`.
