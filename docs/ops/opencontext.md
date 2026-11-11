# OpenContext handoff (`oc`) — #205

**Goal:** usable knowledge handoff into FreeToken-first Attach OpenCode | Hermes | Grok | Codex | Claude.  
**Not:** a second bot product; **not** OpenContext GUI inside pfy chrome.

Upstream: [0xranx/OpenContext](https://github.com/0xranx/OpenContext) (MIT) · npm `@aicontextlab/cli` (`oc`).  
Stage-0 receipt: [sources/entries/080-opencontext.md](../../sources/entries/080-opencontext.md).  
Nimo hello-world proof: [docs/sources/opencontext-205-hello.md](../sources/opencontext-205-hello.md).

## Operator

```bash
./pfy context          # prove capture / keyword search / manifest reuse
                       # FAIL + next if node or oc missing
```

| If | Next |
|----|------|
| `FAIL: node missing` or `FAIL: oc missing` | `npm install -g @aicontextlab/cli` then `./pfy context` |
| prove PASS | Attach OpenCode / Hermes / Grok / Codex / Claude inherit `OPENCONTEXT_*` |

Painted control is **only** `./pfy context` (and `python3 scripts/pfy_opencontext_205.py --prove`). It must operate-or-FAIL. No board/tk/HTML OpenContext button. Do not start `oc ui`.

### Hello-world (CLI only)

CLI hello-world — no embedding API, no `oc index build`, no `oc init` in this repo:

```bash
oc folder create pfy-205-hello -d "pfy #205 hello-world"
oc doc create pfy-205-hello handoff.md -d "PFY_OPENCONTEXT_205_HELLO"
oc folder ls --all
oc doc ls pfy-205-hello
oc context manifest pfy-205-hello --limit 10 --format json
```

`oc search --mode keyword` currently requires an embedding API key even in keyword mode (`@aicontextlab/cli` 0.2.2). `./pfy context` records that as SKIP and still PASSes on folder/doc ls + store keyword + manifest. Do **not** run `oc init` inside pfy-deanery (it rewrites `AGENTS.md`).

## Attach handoff (env / config / `./pfy`)

After a PASS prove, `./pfy start grok|opencode|hermes|codex|claude` and HTML+tk **Attach** for those ids export:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENCONTEXT_BIN` | `oc` on PATH | Child can call the CLI |
| `OPENCONTEXT_CONTEXTS_ROOT` | `$HOME/.opencontext/contexts` | Global library |
| `OPENCONTEXT_DB_PATH` | `$HOME/.opencontext/opencontext.db` | Store DB |

Missing `oc` is a **skip** on Attach (Attach still proves models+smoke). The OpenContext verb is `./pfy context`, not Attach paint.

MCP (optional; operator adds — bootstrap fragment stays codebase-memory only so a missing `oc` cannot break Grok):

```toml
[mcp_servers.opencontext]
command = "oc"
args = ["mcp"]
enabled = true
```

OpenCode (user-level, not vendored here):

```json
{ "mcpServers": { "opencontext": { "command": "oc", "args": ["mcp"] } } }
```

Hermes: `oc` on PATH + the same env. No extra GUI.

## Do not

- Put OpenContext desktop/web UI into pfy chrome
- Paint “integrated” / READY for OpenContext without `./pfy context` PASS
- Triple-write TOOLS.md / `data/tools.json` while catalog 70–75 HOLD
- Reopen #76 · unpark #198
- Auto-run `oc index build` (paid embeddings)

## Verify

```bash
python3 scripts/pfy_opencontext_205.py --selftest
./pfy context
```
