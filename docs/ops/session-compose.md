# Session compose (honest lane + enabled tools + in-TUI how-to)

Cite **#224** only. Deepens **#225**. Catalog 70-75 HOLD. #198 parked. LIVE_HARD_OFF. Do not reopen #76. Do not re-merge #226.

Loop/pre-launch paint must name:

1. Which **model lane** is active: `local FreeToken-first` vs `cloud/subscription (Grok-sub)` vs `OpenCode free`
2. Which **toolsets** are enabled (READY) vs SKIP/FAIL if not wired
3. On **Launch session**: an in-session brief (AGENTS / skills / prompt card) naming enabled tools and how to invoke them in **that** harness

Never imply unwired tools (no Axon when only codebase-memory, no OpenContext when `oc` is missing, no Grok-sub on the OpenCode-free lane).

## How to run

```bash
python3 scripts/pfy_session_compose_224.py --selftest
python3 scripts/pfy_session_compose_224.py --paint
python3 scripts/pfy_session_compose_224.py --brief
python3 scripts/pfy_launch_wizard_225.py --selftest
python3 scripts/pfy_attach_mode_208.py --selftest
./pfy launch compose
./pfy launch brief
python3 scripts/pfy-gui.py --selftest
bash -n scripts/pfy
```

On Loop (HTML+tk): **lane** uses the honest label; **enabled** lists toolset READY/SKIP/FAIL. Launch writes `$PFY_STATE_DIR/session-compose.md` and merges it into `attach-mode-handoff.md` / `attach-agents.md` / `attach-mode-prompt.md` so the child TUI can read `$PFY_SESSION_BRIEF`.

## Variables

| Name | Where | Purpose |
|------|-------|---------|
| `PFY_SESSION_BRIEF` | child env | `$PFY_STATE_DIR/session-compose.md` (lane + enabled + how-to) |
| `PFY_SESSION_PROMPT` | child env | `$PFY_STATE_DIR/session-compose-prompt.md` (one-line prompt card) |
| `PFY_ATTACH_HANDOFF` | child env (#208) | mode handoff **plus** compose brief on Launch |
| `PFY_ATTACH_AGENTS` | child env (#208) | AGENTS fragment (does **not** rewrite repo `AGENTS.md`) |
| `PFY_ATTACH_PROMPT` | child env (#208) | short prompt + compose card |
| `PFY_STATE_DIR` | `launch-wizard.json`, `session-compose.md` | wizard compose + brief |

Registry: [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md).

## Do not

- Reopen #76 · unpark #198 · catalog 70-75 HOLD
- Re-merge #226
- Label OpenCode-free as Grok-sub (or local as OpenCode-free)
- Claim Axon when the live path is codebase-memory
- Claim OpenContext / MCP / write-guard unless wired
- `LIVE_HARD_OFF`: no cloud embeddings / live catalog writes from this path
