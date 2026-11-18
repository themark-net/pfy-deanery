# Module: Attach mode (`scripts/pfy_attach_mode_208.py`)

**Purpose:** Operator-selected Attach mode `bare` | `orchestration` | `code-graph` with `using: <mode>` paint and operate-or-FAIL handoff into OpenCode | Hermes | Grok | Codex | Claude. Cite #208. Orchestration is a started multi-step local loop (#213), not a thin skill inject.

## Human operator

- What: pick a mode on Attach (HTML+tk), then Attach a harness - or pick the same toolset on the Loop launch wizard (#225) then **Launch session**. Loop/Attach show `using: <mode>`.
- How: [docs/ops/attach-mode.md](../ops/attach-mode.md)
- Failures: unwired mode → FAIL + next (never silent bare).
- Recovery: `bare` always; orchestration needs `./pfy setup`; code-graph needs Axon (`pip install axoniq`) or `codebase-memory-mcp` (painted as not Axon).

## Agent

- Entry: `scripts/pfy_attach_mode_208.py` (`--selftest` / `--set` / `--prepare` / `--export-env`); `scripts/pfy_orchestration_213.py` (`--selftest` / `--start HID` / `--export-env`); `scripts/pfy_code_graph_215.py` (`--selftest` / `--prove` / `--prepare HID`).
- Callers: `start_sidecar` / `POST /mode` / `POST /start`; Attach 162/196/202/220/221 child env; `./pfy start` payload.
- Invariants: one mode at a time; no Env nav tab; do not rewrite repo `AGENTS.md`; catalog HOLD; do not reopen #76. Orchestration missing runtime → FAIL+next (never silent bare). Code-graph never claims Axon when only MCP is live.
- Issue **#208** (mode select) · **#213** (orchestration loop start) · **#215** (code-graph Axon path).

## Architecture link

Operator-stack layer (board/gui + attach child env), not catalog product surface.
