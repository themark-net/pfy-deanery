# Module: Operator launch wizard (`scripts/pfy_launch_wizard_225.py`)

**Purpose:** Loop-primary compose-then-launch: pick runtime, model lane, toolsets, harness, review, then **Launch session** into an enterable TUI with the composed env. Cite **#225**. Honest lane + enabled-tool paint and in-session brief: **#224**. Attach X is secondary re-attach, not the front door.

## Human operator

- What: on **Loop**, the page itself says why each pane exists: local vs cloud, work class, gathered modules, then **Launch session**. Window stays open. Compose wizard (#225) still runs under Launch; it is not the Loop front door.
- How: [docs/ops/launch-wizard.md](../ops/launch-wizard.md)
- Failures: missing runtime → FAIL + `Launch env or ./pfy up`. Unknown lane/harness → FAIL + pick. Orchestration missing skill → FAIL + `./pfy setup`. Code-graph missing Axon and codebase-memory → FAIL + `pip install axoniq`. Catalog not ready / HOLD 70-75 → honest SKIP (not auto-lifted). Incomplete review → FAIL + complete wizard. Launch reuses attach-usable prove (models+smoke) or FAIL+next.
- Recovery: Launch env / `./pfy up`; pick a valid lane and harness; pick a catalog tool on Tools; Attach tab remains for re-attach.

## Agent

- Entry: `scripts/pfy_launch_wizard_225.py` (`--selftest` / `--runtime` / `--lane` / `--toolset` / `--harness` / `--review` / `--launch`); `./pfy launch`; board `POST /wizard` `POST /launch`; HTML+tk Loop.
- Callers: Loop HTML/tk primary CTA; `start_sidecar` for Launch (OpenCode|Grok|Hermes|Codex|Claude); attach mode #208; catalog ask env #209.
- Invariants: no Env nav tab; window stay-open; Attach X demoted on Loop; catalog 70-75 HOLD; LIVE_HARD_OFF; do not reopen #76. Cite **#225**. Session brief / honest lane labels: **#224**.
- Issue **#225** only.

## Architecture link

Operator-stack layer (Loop compose → attach-usable session). Not a catalog triple-write.
