# Pending handoff

Git plus this file is the handoff when another checkout may be open. Do not commit, reset, or stash on an open founder Build branch.

## 2026-10-04 — land Sep 25 Grok Build: CLI catalog cards + eval-auto

- **Branch:** `build/pfy-cli-catalog-cards-0925` (rebased onto `origin/main` @ `53b24ec`)
- **Backup:** `backup/main-local-20261004` @ pre-rebase `3afd13b`; WIP snapshot `backup/wip-uncommitted-20261004`
- **What the Build session did (Sep 25):**
  1. **Loop / launch** — launch wizard fills missing compose defaults and names the agent (`pfylib/loop_paint.py`, GUI board/loop paint, `test_launch_compose_defaults`).
  2. **pfy CLI harness polish** — short product help; shimmy last after ollama; ollama start health + default model; share Hermes/Claude/Codex installers between CLI and Attach; read Gemini/Exo installers from registry; Continue recipe names direct vs cage filesystem.
  3. **Catalog stage cards** — every TOOLS.md row must have an integration-stage card; handoff cards for all 50 stage rows (`data/catalog_stage_handoff.json`, `catalog_stage_methods.json`, `tool_integration_stages.json`, `catalog_stage_eval.py`).
  4. **Eval-auto WIP (included)** — `scripts/eval_auto_candidates.py` + `eval-auto.sh` candidate loop + receipt (T-0074); `examples/eval-harness/tasks/013-stage-card/` structural scorer (T-0070).
- **Verify (ran green on nimo 2026-10-04):** `make catalog-check` · `make eval-structural` (126 pfylib unittests + text scorers incl. 013) · `make smoke-product-levers` · targeted unittest pack for new adapters/catalog/eval-auto.
- **GUI / launch paths:** YES — first commit touches `gui/operator/frontend/*`, `scripts/pfy-gui.py`, `scripts/pfy-board.py`, launch wizard. **Needs Reviewer launch check** before merge.
- **Not in this PR:** `.env.bak` (gitignored via `*.bak`, never committed); `scripts/.pfy.expanded.sh` (stale scratch, gitignored); LOOP-243 design docs (already on main via #244); stashes and other worktrees left untouched.
- **Next:** Reviewer launch check on GUI/loop; merge when checks green. Do not auto-lift catalog HOLD entries 70–75.

## 2026-09-28 — founder standings into portable skills SoT

- **Branch:** `bot/skills-port-standings-20260928` (from main `bd35bad`)
- **Prior:** stalled `bot/skills-port-standings-20260925` @ `d262300` cherry-picked here. That branch was never a PR. Do not force-push `main`.
- **Landed:** `prefer-behavior-and-fail-recover-tests`, `ui-is-the-app-design-in-loop`, `best-effort-and-bot-budget-build-max`
- **SoT:** `bootstrap/grok-cli/skills/<name>/` (org bot skills stay pointers). Project mirror: `.grok/skills/`.
- **Out of scope:** catalog 70–75 HOLD, LIVE_HARD_OFF, product UI, Feature GO.
- **Verify:** `make smoke-grok-skills`
- **Next:** merge the docs/skills PR when checks are green. Pattern: [port-bot-doctrine-to-pfy-sot.md](ops/port-bot-doctrine-to-pfy-sot.md).
