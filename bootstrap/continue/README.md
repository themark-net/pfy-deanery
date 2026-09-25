# Continue.dev config recipe

Copy this snippet into Continue. Do **not** git-vendor the IDE.

This is an IDE **config recipe**, not a CLI harness. After `./pfy start` (or the ADR-0014 detector), set `apiBase` from `$LOCAL_OPENAI_BASE_URL`. Append `/v1` if it is missing.

Replace the dummy `apiBase` in `config.json` with `$LOCAL_OPENAI_BASE_URL` (ensure `/v1`). The FreeToken example is `:1919`, not Ollama-only.

Detect order (first live wins):

1. FreeToken `:1919`
2. llama-swap `:9292`
3. llama-server `:8080`
4. Ollama `:11434` last

`./pfy start continue` remains **STUB** exit 2. It does not exec the IDE. It writes `$PFY_STATE_DIR/continue-config.json` with `apiBase` taken from `$LOCAL_OPENAI_BASE_URL` (append `/v1` when missing). With no live engine the file uses `http://127.0.0.1:1919/v1` and says so.

## Where the IDE opens

pfy prints `filesystem: direct` or `filesystem: cage` and exports `PFY_FS` / `PFY_FS_ROOT`.

| Mode | What the harness sees | What it is not |
|------|------------------------|----------------|
| `direct` | The repo you launched from (`PFY_FS_ROOT`) | The cage tree |
| `cage` | `/workspace/pfy-mentat` inside the lab. Grok reads that tree through the filesystem MCP | Your host path |

The cage copy on the host is `~/.agentcage/workspace/pfy-mentat`, bind-mounted at `/workspace/pfy-mentat`. Those are two trees. Move commits with `make cage-code-sync`. Open Continue on `PFY_FS_ROOT` for the mode you are in.
