# Module: code-graph handoff (`scripts/pfy_code_graph_215.py`)

**Purpose:** Prove Axon (or already-present `codebase-memory-mcp` equivalent) on the host and hand the live path into FreeToken-first Attach OpenCode | Hermes | Grok | Codex | Claude. Cite #215.

## Human operator

- What: `./pfy code-graph` (alias `./pfy axon`) proves the live path. Attach mode **code-graph** inherits that path - operate-or-FAIL.
- How: [docs/ops/code-graph.md](../ops/code-graph.md)
- Failures: neither Axon nor MCP → `FAIL` + `pip install axoniq · ./pfy catalog ask axon`. Hermes/Codex/Claude with MCP-only → FAIL + install Axon / Attach grok or opencode.
- Recovery: `pip install axoniq` then `./pfy code-graph`. Do not start `axon ui` from pfy.

### Configuration / variables

| Name | Where | Purpose |
|------|-------|---------|
| `PFY_GRAPH_PATH` | child env | `axon` \| `codebase-memory` (never invent axon) |
| `AXON_BIN` | child env | Absolute `axon` path - **only** when path=axon |
| `CODEBASE_MEMORY_MCP` | child env | MCP binary - only when path=codebase-memory |
| `PFY_GRAPH_EVIDENCE` | child env / Loop | `$PFY_STATE_DIR/graph-evidence.json` |
| `PFY_GRAPH_HANDOFF` | child env | `$PFY_STATE_DIR/graph-handoff.md` |

Registry: [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md).

## Agent

- Entry: `scripts/pfy_code_graph_215.py` (`--prove` / `--export-env` / `--selftest` / `--prepare HID`); `./pfy code-graph` → `--prove`.
- Callers: `scripts/pfy` (`cmd_code_graph`, `apply_attach_mode_env`); `pfy_attach_mode_208.py` prepare; board `start_sidecar`; Attach 162/196/202/220/221 via 208 child env.
- Invariants: painted code-graph verb operate-or-FAIL; never claim Axon when only MCP stub; one attach / one mode; catalog HOLD (no TOOLS.md row); do not merge PR #75.
- ADR: ADR-0012 (simple launch) · ADR-0014 (FreeToken-first spine). Issue **#215** only.
- Do not: reopen #76; unpark #198; start #214; auto-merge catalog 70-75.

## Architecture link

Operator-stack layer (`./pfy` affordance + attach child env), not catalog product surface. Stage-0 receipt lives under `sources/entries/`.
