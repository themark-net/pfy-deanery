# Module: Session compose (`scripts/pfy_session_compose_224.py`)

**Purpose:** Deepen the #225 launch wizard so Loop/pre-launch paint names the **model lane** and **enabled toolsets** honestly, and Launch writes an in-session brief (AGENTS / skills / prompt card) the harness can actually follow. Cite **#224**. Never imply unwired tools.

## Human operator

- What: on **Loop**, lane shows `local FreeToken-first` vs `cloud/subscription (Grok-sub)` vs `OpenCode free`. **enabled** lists toolsets as READY / SKIP / FAIL. Launch session writes `$PFY_STATE_DIR/session-compose.md` into the same handoff/AGENTS/prompt files the TUI already reads.
- How: [docs/ops/session-compose.md](../ops/session-compose.md)
- Failures: selected toolset not wired → FAIL or honest SKIP + next (`./pfy setup`, `pip install axoniq`, pick a catalog tool). Catalog 70-75 HOLD is never auto-lifted. Missing `oc` is SKIP (do not claim OpenContext).
- Recovery: complete the #225 wizard; Launch env / `./pfy up` if runtime is down. Attach tab remains secondary re-attach.

## Agent

- Entry: `scripts/pfy_session_compose_224.py` (`--selftest` / `--paint` / `--brief`); `./pfy launch compose` · `./pfy launch brief`; wizard Launch (`pfy_launch_wizard_225.launch_session`); attach-mode `#208` merge into `attach-mode-handoff.md` / `attach-agents.md` / `attach-mode-prompt.md`.
- Callers: Loop HTML/tk paint (`wizard_lane_label`, `wizard_enabled`); Launch session; `apply_child_env` (`PFY_SESSION_BRIEF`, `PFY_SESSION_PROMPT`).
- Invariants: do not call OpenCode-free Grok-sub or vice versa; do not claim Axon when only codebase-memory is live; do not rewrite repo `AGENTS.md`; catalog 70-75 HOLD; LIVE_HARD_OFF; do not reopen #76; do not re-merge #226. Cite **#224** only.
- Issue **#224** only.

## Architecture link

Operator-stack layer (Loop compose → attach-usable session brief). Not a catalog triple-write.
