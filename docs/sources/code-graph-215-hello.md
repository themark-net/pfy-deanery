# Code-graph nimo hello-world proof (#215)

**Host:** nimo  
**When:** 2026-09-13 (local)  
**Axon:** not installed (`pip install axoniq` would be next)  
**Equivalent:** `$HOME/.local/bin/codebase-memory-mcp`  
**LIVE_HARD_OFF:** no Axon UI, no cloud embeddings, no catalog PR #75 merge.

## Fail-closed (neither path)

```text
PATH="/tmp/pfy-215-no-graph" python3 scripts/pfy_code_graph_215.py --prove
FAIL: axon missing
  next: pip install axoniq · ./pfy catalog ask axon
# rc=1
```

`python3 scripts/pfy_code_graph_215.py --selftest` → `PASS selftest · code-graph axon|codebase-memory · FAIL+next · never claim axon on MCP`

## Live path on nimo (Axon missing)

```text
$ ./pfy code-graph
PASS code-graph · path=codebase-memory (not axon) · $HOME/.local/bin/codebase-memory-mcp
  axon: missing
  next for Axon: pip install axoniq · ./pfy catalog ask axon
handoff: Attach OpenCode|Grok inherit CODEBASE_MEMORY_MCP
note: do not claim Axon; MCP stub is the live path
export PFY_GRAPH_PATH="codebase-memory"
export PFY_CODE_GRAPH="codebase-memory"
export CODEBASE_MEMORY_MCP="$HOME/.local/bin/codebase-memory-mcp"
```

`./pfy axon` is an alias of `./pfy code-graph`.

Hermes + MCP-only is unwired (no Axon CLI):

```text
PFY_STATE_DIR=/tmp/pfy-215-hermes python3 scripts/pfy_attach_mode_208.py --prepare hermes code-graph
FAIL mode -- code-graph unwired for Hermes (no Axon CLI; MCP-only) · pip install axoniq · Attach grok or opencode for code-graph MCP
# rc=1
```

OpenCode + MCP equivalent is wired and painted **not axon**:

```text
PFY_STATE_DIR=/tmp/pfy-215-oc python3 scripts/pfy_attach_mode_208.py --prepare opencode code-graph
PASS mode · using: code-graph · path=codebase-memory (not axon)
```

## Handoff

Painted verb: `./pfy code-graph` (operate-or-FAIL) plus Attach mode **code-graph** (HTML+tk). Loop/Attach paint `using: code-graph` and `graph path=…`. Never claim Axon when only `codebase-memory-mcp` is live.
