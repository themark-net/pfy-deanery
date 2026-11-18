# Attach mode (`bare` | `orchestration` | `code-graph`)

Cite **#208** (mode select), **#213** (orchestration loop start), and **#215** (code-graph Axon path). One attach / one mode at a time. No Env nav tab (Launch env / Stage / Loop env chip unchanged).

## Operator

On **Attach** (and Loop attach row) select a mode, then Attach OpenCode | Hermes | Grok | Codex | Claude. Loop **Launch session** (#225) uses the same modes as wizard toolsets (`bare` · `orchestration` · `code-graph`; catalog is wizard-only SKIP/FAIL). Session compose **#224** merges the honest lane/enabled-tools brief into the same AGENTS/prompt files.

The UI paints `using: <mode>`. Loop also paints last loop/monitor evidence (not slogan-only).

| Mode | What ships into the session | Fail |
|------|-----------------------------|------|
| **bare** | Bare TUI + FreeToken-first local endpoint. Prompt/AGENTS/env say this is not orchestration or code-graph. | Same as attach-usable: no engine → `Launch env or ./pfy up` |
| **orchestration** | `/agent-loops` skill **and** a proved multi-step loop on the FreeToken-first local model (exit card + 2 turns + monitor evidence). Not a thin env/skills inject. | Skill missing → `./pfy setup`. No local engine / loop start fail → `Launch env or ./pfy up` |
| **code-graph** | Axon CLI + MCP (`axon serve --watch`) when `axon` is on PATH. Else already-present `codebase-memory-mcp` as equivalent, painted `path=codebase-memory (not axon)`. | Neither binary → `pip install axoniq · ./pfy catalog ask axon`. Hermes MCP-only → `pip install axoniq` / Attach grok or opencode |

Unwired mode is **FAIL + next**. Never a silent bare session claiming orchestration or code-graph.

## How to run

```bash
python3 scripts/pfy_attach_mode_208.py --selftest
python3 scripts/pfy_orchestration_213.py --selftest
python3 scripts/pfy_code_graph_215.py --selftest
./pfy code-graph
python3 scripts/pfy-board.py --mode orchestration
python3 scripts/pfy-board.py --start grok orchestration
# or select orchestration in HTML/tk, then Attach
```

Named `./pfy start grok|opencode|hermes|codex|claude` prepares the selected mode from `$PFY_STATE_DIR` (default `bare`) and fails closed if that mode cannot be handed off. Orchestration also proves loop start before exec.

## Variables

| Name | Where | Purpose |
|------|-------|---------|
| `PFY_ATTACH_MODE` | child env | `bare` \| `orchestration` \| `code-graph` |
| `PFY_ATTACH_HANDOFF` | child env | `~/.pfy-mentat/attach-mode-handoff.md` (orchestration: loop card) |
| `PFY_ATTACH_PROMPT` | child env | short prompt file (orchestration: continue-from-card) |
| `PFY_ATTACH_AGENTS` | child env | AGENTS fragment (does **not** rewrite repo `AGENTS.md`) |
| `PFY_LOOP_CARD` | child env / Loop | 8-exit card after a started loop (#213) |
| `PFY_LOOP_EVIDENCE` | child env / Loop | last loop/monitor evidence JSON |
| `PFY_LOOP_PROMPT` | child env | continue-from-card prompt |
| `PFY_GRAPH_PATH` | child env / Loop | `axon` \| `codebase-memory` (#215) |
| `AXON_BIN` | child env | Axon CLI - only when path=axon |
| `PFY_STATE_DIR` | `attach-mode`, `attach-mode-when`, `attach-mode-live`, `loop-evidence.json`, `monitor-note`, `graph-evidence.json` | one selected mode + last successful handoff + loop/graph evidence |

Registry: [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md).

## Do not

- Reopen #76 · unpark #198 · catalog 70-75 HOLD (do not merge PR #75)
- Add an Env nav tab
- Paint `ok` / `using: orchestration` without skill handoff **and** loop start/evidence
- Paint `using: code-graph` as Axon when only codebase-memory MCP is live
- `LIVE_HARD_OFF`: no cloud embeddings from this path
