# OpenContext nimo hello-world proof (#205)

**Host:** nimo  
**When:** 2026-09-08 (local) / 2026-09-09 UTC  
**CLI:** `@aicontextlab/cli` 0.2.2 → `$HOME/.npm-global/bin/oc`  
**Node:** v22.23.0  
**LIVE_HARD_OFF:** no `oc index build`, no embedding/cloud keys, no `oc ui`, no FreeToken start.

## Install

```text
npm install -g @aicontextlab/cli@0.2.2
# added 966 packages
```

## Fail-closed (node/oc missing)

```text
PATH="/usr/bin:/bin" python3 scripts/pfy_opencontext_205.py --prove
FAIL: oc missing
  next: npm install -g @aicontextlab/cli
# rc=1
```

`python3 scripts/pfy_opencontext_205.py --selftest` → `PASS selftest · missing-oc fail-closed`

## Capture / search / reuse

Store: `~/.opencontext/contexts` · db: `~/.opencontext/opencontext.db`

```text
$ ./pfy context
PASS context · oc $HOME/.npm-global/bin/oc
store: $HOME/.opencontext/contexts
db: $HOME/.opencontext/opencontext.db
  capture folder: Folder ready at "pfy-205-hello".
  capture doc: exists
  capture body: $HOME/.opencontext/contexts/pfy-205-hello/handoff.md
  reuse manifest: 1 docs
  search folder ls: hit
  search doc ls: hit
  search store keyword: hit
  search oc keyword: SKIP (Error: API key not configured. Set OPENAI_API_KEY or configure in ~/.opencontext/config.toml)
handoff: Attach OpenCode|Hermes|Grok inherit OPENCONTEXT_* via ./pfy start / Attach
MCP (stdio): oc mcp
Grok: [mcp_servers.opencontext] command="$HOME/.npm-global/bin/oc" args=["mcp"]
OpenCode: mcpServers.opencontext command=oc args=["mcp"]
note: oc ui / desktop stay out of pfy chrome
export OPENCONTEXT_BIN="$HOME/.npm-global/bin/oc"
export OPENCONTEXT_CONTEXTS_ROOT="$HOME/.opencontext/contexts"
export OPENCONTEXT_DB_PATH="$HOME/.opencontext/opencontext.db"
```

Token `PFY_OPENCONTEXT_205_HELLO` is in `pfy-205-hello/handoff.md`. Manifest JSON lists that doc + `stable_id`. `oc search --mode keyword` SKIP is expected without an embedding key (native searcher still asks for `OPENAI_API_KEY`); local folder/doc ls + store keyword satisfy search without calling cloud.

## Handoff

Painted verb: `./pfy context` only (operate-or-FAIL). No OpenContext control in pfy HTML/tk/Tauri chrome. Attach OpenCode|Hermes|Grok inherit `OPENCONTEXT_*` when `oc` is on PATH (`scripts/pfy_opencontext_205.py apply_child_env`).
