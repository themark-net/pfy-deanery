# Code-graph handoff (Axon preferred) — #215

**Goal:** usable code-graph path into FreeToken-first Attach OpenCode | Hermes | Grok | Codex | Claude.  
**Not:** catalog PR merge; **not** Axon UI inside pfy chrome.

Upstream: [harshkedia177/axon](https://github.com/harshkedia177/axon) (MIT) · PyPI `axoniq` (`axon`).  
Stage-0 receipt: [sources/entries/082-axon.md](../../sources/entries/082-axon.md).  
Nimo hello-world proof: [docs/sources/code-graph-215-hello.md](../sources/code-graph-215-hello.md). Live path on nimo at ship: **codebase-memory MCP** (Axon not installed).

Catalog PR [#75](https://github.com/themark-net/pfy-deanery/pull/75) stays HOLD — this slice does **not** merge it.

## Operator

```bash
./pfy code-graph        # prove Axon, else codebase-memory equivalent
./pfy axon              # alias
                       # FAIL + next if neither path is live
```

| If | Next |
|----|------|
| `FAIL: axon missing` (and no MCP) | `pip install axoniq` then `./pfy catalog ask axon` |
| Axon prove fails, MCP present | PASS `path=codebase-memory (not axon)` — do not claim Axon |
| prove PASS `path=axon` | Attach OpenCode / Hermes / Grok inherit `AXON_BIN` |
| prove PASS `path=codebase-memory` | Attach OpenCode / Grok inherit MCP; Hermes still FAIL |

Painted control is **`./pfy code-graph`** plus Attach mode **code-graph** (HTML+tk). Both operate-or-FAIL. Loop/Attach paint `using: code-graph` and `graph path=…`. Do not start `axon ui`.

### Hello-world (CLI only)

Prefer Axon when installable. LIVE_HARD_OFF: `--no-embeddings`, no cloud keys, no `axon ui`.

```bash
pip install axoniq
axon analyze . --no-embeddings
axon serve --watch    # MCP (stdio); do not paint as live unless this binary exists
```

Equivalent already on nimo when Axon is missing: `codebase-memory-mcp` (bootstrap `--with-codebase-memory`). Paint **path=codebase-memory (not axon)**.

## Attach handoff (env / config / `./pfy`)

After a PASS prove or a successful Attach prepare, HTML+tk **Attach** and `./pfy start grok|opencode|hermes|codex|claude` export:

| Variable | When | Purpose |
|----------|------|---------|
| `PFY_GRAPH_PATH` | always on wired code-graph | `axon` or `codebase-memory` |
| `AXON_BIN` | path=axon only | Child can call the CLI |
| `CODEBASE_MEMORY_MCP` | path=codebase-memory only | MCP binary |

Unwired (neither binary) is **FAIL + next** on Attach mode code-graph. Never a silent bare session claiming code-graph.

MCP (Axon live):

```toml
[mcp_servers.axon]
command = "axon"
args = ["serve", "--watch"]
enabled = true
```

OpenCode (STATE `opencode.json` when path=axon):

```json
{ "mcp": { "axon": { "type": "local", "command": ["axon", "serve", "--watch"], "enabled": true } } }
```

Hermes: Axon CLI on PATH (env). MCP-only is unwired for Hermes.

## Do not

- Merge or cherry-pick catalog PR #75
- Triple-write TOOLS.md / `data/tools.json` while catalog 70–75 HOLD
- Claim Axon when only `codebase-memory-mcp` is live
- Put Axon web UI into pfy chrome
- Reopen #76 · unpark #198 · start #214
- `LIVE_HARD_OFF`: no cloud embeddings from this path

## Verify

```bash
python3 scripts/pfy_code_graph_215.py --selftest
python3 scripts/pfy_attach_mode_208.py --selftest
./pfy code-graph
bash -n scripts/pfy
```
