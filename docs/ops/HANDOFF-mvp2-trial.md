# Handoff: pfy local build MVP step 2 trial

Historical note: "Do not merge to main" and the `bot/mvp2-trial` branch text below are historical. The report now lives on main.

Branch `bot/mvp2-trial`. Base `997d89264495861a178713ccf7d4447ea828afc4`. Not a Feature GO. No PR. Do not merge to main. Catalog HOLD 70-75 was not touched. The head SHA is whatever `git rev-parse HEAD` prints after the commit that adds this file. A commit cannot record its own SHA.

Worktree: `/home/mark/DEVELOP/pfy-mentat/tmp/mvp2`. The main checkout and other worktrees were not used. Raw logs and arm worktrees stay under `tmp/mvp2-runs/` (gitignored). Receipts and reviews: `eval/mvp2/results/`. Patches: `eval/mvp2/patches/`. Report: `eval/mvp2/REPORT.md`. Decisions: `docs/ops/AUTONOMOUS-DECISIONS-2026-10-27.md`. Run log: `docs/ops/RUN-LOG-mvp2-trial.md`.

## Verdict

No-go for making `./pfy build --local` the default on build-only runs.

Gate pass: local 5/6, cloud 6/6. Review accept: local 4/6, cloud 6/6. Wall: local 1694.0 s, cloud 583.6 s. Attempts: 1 each. Timeouts: 0. Memory blocks: 0. Gaming: none. Scope creep: none.

Weekly Build percent was not readable. That sentence is an operator observation with no receipt field. `~/.grok/auth.json` exists and is non-empty. Six cloud sessions, `turnCount` 1 each, `modelCalls` 9+5+9+9+12+7 = 51. Token fields were not copied.

## Per task

| Task | L | C | Land? |
|------|---|---|-------|
| t1 smolvm stderr first | PASS, accept, 113.9 s | PASS, accept, 113.5 s | either patch |
| t2 tree_sig 119 | PASS, accept, 196.7 s | PASS, accept, 18.7 s | either patch |
| t3 daemon stop is a fail | PASS, accept, 463.9 s | PASS, accept, 118.6 s | prefer C (HOME check stays first) |
| t4 timeout names the substep | PASS, reject, 286.7 s | PASS, accept, 173.1 s | C only. L labels `ls`/`set`/`settings` as `new` |
| t5 receipts outside the repo | FAIL, reject, 461.4 s | PASS, accept, 118.3 s | C only. L never set `PFY_SMOKE_RECEIPT_DIR` |
| t6 tree_sig in three smokes | PASS, accept, 171.4 s | PASS, accept, 41.4 s | either patch |

Local handles a one-function change, an in-repo hash copy, and one new fail return. It missed precise control flow (`t4`) and two-file test wiring (`t5`). The measured gap is a review step. A retry was not tried. No arm hit the 1200 s agent timeout, so a bigger context is not what this run showed was missing.

## Commands and gates

Prove-red, before any model: `python3 eval/mvp2/run_trial.py prove-red`. Six gates failed in bwrap on the base for the intended assertion (failures 1, 1, 1, 2, 1, 3; errors 0).

Local: `python3 eval/mvp2/run_trial.py all-local`. Cloud: `python3 eval/mvp2/run_trial.py all-cloud`. The runner unloads `qwen3.6:35b` between local arms when that model is the only one resident. The 32 GiB floor was not lowered. After the local run, `ollama ps` was empty.

## Not done

Task diffs are not on this branch except as patches. Landing default, as an owner override: prefer the cloud (C) patches; never land the local t4/t5 patches. No second local attempt. No cloud retry. Weekly Build percent is still unknown. That reading is an operator observation with no receipt field.

## Landing (2026-10-30 PT)

Branch `bot/mvp2-report`: the five `bot/mvp2-trial` commits (50220ce and parents) cherry-picked unchanged onto `origin/main` 1e99251 so main can fast-forward. Worktree `tmp/mvp2r`. Scope is docs and eval only: `docs/build-dropins/`, `docs/ops/`, `docs/TODO.md`, `eval/mvp2/`. No runtime code changes; the local t4/t5 diffs are only evidence files under `eval/mvp2/patches/`, not landed code. The `eval/mvp2/gates/test_mvp2_*.py` gates are red on base by design and sit outside `tests/`, so CI's `unittest discover -s tests` does not collect them. Gate rule: docs/eval only, so pregate plus Reviewer, no Tester. Follow-up: MVP-3 review-and-retry loop on `bot/mvp3-review-retry` ([pfy-local-build-mvp3.md](../build-dropins/pfy-local-build-mvp3.md)). That file is not on this branch or on main. It lands with MVP-3 on branch `bot/mvp3-review-retry`.

## Known gaps

Prove-red has no standalone receipt. It is backed only by the local `tests_before` field (failures 1, 1, 1, 2, 1, 3; errors 0). Cloud receipts lack `tests_before`. This note does not add a receipt.

None reported a truncated prompt. That sentence is an operator observation with no receipt field. The same wording is in `eval/mvp2/REPORT.md`.

Weekly Build percent was not readable. That sentence is an operator observation with no receipt field.
