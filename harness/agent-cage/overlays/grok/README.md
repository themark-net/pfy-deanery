# Overlay: Grok CLI inside agent-cage

Versioned agent image with Grok CLI. **Primary auth is the same as host Grok Build:** browser/OIDC login stored in `auth.json` — **not** an API key (though `XAI_API_KEY` remains an optional fallback).

## How Grok Build auth works (host)

| Method | When | Where stored |
|--------|------|----------------|
| **Browser / OIDC login** (`grok` or `grok login`) | Default for subscriptions (opens browser → auth.x.ai) | `~/.grok/auth.json` (mode `oidc`, access + refresh tokens) |
| **Device auth** (`grok login --device-auth`) | Headless / Docker / SSH (URL + code in any browser) | same `auth.json` |
| **`XAI_API_KEY`** | CI / console key from [console.x.ai](https://console.x.ai) | env only — used **only if no active session** in `auth.json` |

You authenticated this environment with the web OAuth flow; that session lives in:

```text
~/.grok/auth.json          # mode 0600, contains OIDC tokens (do not commit)
```

Tokens refresh automatically via `refresh_token` until refresh fails (then re-login).

## Cage auth strategies

### 1) Import host session (recommended)

Copies host `auth.json` into the cage’s isolated Grok home (not a live bind of your whole `~/.grok`).
**`make cage-grok` always re-imports** after `grok-up` so cage tokens match a fresh host session
(stale import → interactive login prompt / `Auth: ApiKey` 401).

### Network / “Grok cannot connect to CLI API”

All agent HTTPS goes through the cage **whitelist proxy**. If Grok fails to reach the API:

1. Confirm policy is **`coding-agent-grok`** (not bare `default` / incomplete `coding-agent-local`).  
   `make cage-grok-up` forces `POLICY=coding-agent-grok` and recreates proxy+agent.
2. Run: **`make cage-grok-net-smoke`** — must not show `blocked_by_agent_cage` for `auth.x.ai`, `cli-chat-proxy.grok.com`, `storage.googleapis.com`.
3. Check `~/.agentcage/logs/audit.jsonl` for `"event": "blocked"` on those hosts.
4. **TUI crash / mouse types as text** — Grok TUI died without restoring the terminal. On the **host** shell: `reset` (or close the tab). Unrelated to host Grok outside the cage.

### Sessions (resume old chats)

Grok keys sessions by **absolute cwd**. Cage cwd is `/workspace/pfy-mentat`, which is **not** the same key as host `/home/.../local-llm-dev-tools`.

| Store | Path |
|-------|------|
| Persistent host store | `~/.agentcage/grok-state/sessions` → mounted at `/home/agent/.grok/sessions` |
| Cage repo sessions | `…/sessions/%2Fworkspace%2Fpfy-mentat/<uuid>/` |
| Host-desktop sessions (this repo) | `~/.grok/sessions/%2Fhome%2F…%2Flocal-llm-dev-tools/` |

```bash
make cage-grok-sessions-import-host   # copy host project sessions into cage key (rewrite cwd)
make cage-grok-sessions               # list what Grok sees in cage
make cage-grok-resume                 # grok --continue
make cage-grok-resume ID=019f52c9-…   # specific session
```

### How you actually launch Grok

```bash
# Once per machine (idempotent after first success)
make cage-setup && make cage-init          # if ~/.agentcage missing
make cage-grok-install
make cage-grok-auth-import                 # needs host: grok login
make cage-grok-build

# Daily / re-run (idempotent ladder)
make cage-grok                             # = grok-ensure: up + sync + ready + print next step

# Get into a session
make cage-grok-shell                       # bash at /workspace/pfy-mentat  (then: grok)
make cage-grok-run                         # drop straight into interactive Grok TUI
make cage-grok-run PROMPT='list top-level files'
make cage-grok-run FLAGS='--always-approve' PROMPT='list top-level files'
```

**Prompt quoting:** pass the whole initial message as `PROMPT='…'` (one Make variable).  
Do **not** use unquoted multi-word `ARGS=Read docs/foo.md and …` — Make/shell split it and Grok treats path tokens as extra CLI arguments.

**Not** `make cage-shell` alone if you want the Grok image + catalog tree + MCP preset — use **`cage-grok*`**.

```bash
# Low-level (same as grok-ensure pieces)
make cage-grok-up            # MUST use this — not plain cage-up-mcp (loads compose override)
make cage-workspace-sync     # catalog → /workspace/pfy-mentat + MCP preset
make cage-grok-ready         # smoke
```

### Filesystem MCP on the local (catalog) repo

| Piece | Path |
|-------|------|
| Host catalog | git clone of pfy-deanery |
| Cage workspace tree | `~/.agentcage/workspace/pfy-mentat` ← `make cage-workspace-sync` |
| In-container | `/workspace/pfy-mentat` |
| MCP server | cage **mcp-host** `@modelcontextprotocol/server-filesystem` on **`/workspace`** |
| Grok project config | `/workspace/pfy-mentat/.grok/config.toml` (HTTP URL to mcp-host) |

`make cage-grok-ready` proves: Grok binary + auth, synced catalog tree, MCP initialize, `grok mcp list` shows **filesystem**.

### Can Grok call “local agents”?

| Capability | Status today |
|------------|----------------|
| **Filesystem MCP** on cage `/workspace` (includes catalog) | **Yes** — wired by `grok-mcp-preset` |
| **Grok built-in tools / subagents** (`grok --agent`, `--agents`) | **Yes** — Grok Build CLI feature; runs *inside* the cage process |
| **Host Ollama as model backend** | Separate path: `make local-ollama-up` + LiteLLM smoke; not auto-selected by Grok overlay |
| **AgenC marketplace / multi-agent job bus** | **No** — demoted ([ADR-0010](../../../../docs/adr/0010-reject-agenc-as-primary-runtime.md)); re-eval TODO later |
| **Other CLIs as Grok MCP tools** (Claude/OpenCode) | Not preset; optional future MCP entries |

**Pitfalls fixed in this overlay:**

1. **`agentcage up` ignores compose override** when it passes `-f docker-compose.yaml`. Always use **`make cage-grok-up`** (explicit third `-f` for override).
2. **Do not bind-mount the whole `.grok` tree** — that hid `.grok/downloads/` and broke `grok`. Binary is at **`/usr/local/bin/grok`**; only **`auth.json`** is mounted.
3. **auth.json ownership** — host file is often uid 1000; cage user `agent` is **1001**. If agent cannot read `auth.json`, Grok falls back to **ApiKey** and fails (`401 bad-credentials` or OIDC errors). `make grok-auth-import` and `grok-up`/`grok-smoke` chown the file to `agent` (mode `600`). **Host user cannot open the cage copy after import** — that is expected; redacted mode/email is printed *before* chown. Do not `chmod` the cage file world-readable.

4. **sessions store dual-write** — `~/.agentcage/grok-state/sessions` is bind-mounted into the container. **Do not** `chown -R agent` exclusively on that tree: host `make grok-sessions-import-host` then fails with `Permission denied`. Use `make fix-grok-state-perms` (also run from `grok-state-init` / `grok-up` / import). Parent `grok-state/` stays `0700` host-only; `sessions/` is open `a+rwX` underneath.

Re-import after host re-login if the cage session expires. If import fails mid-way with `Permission denied` on the redacted check, update to a tree that verifies pre-chown (or re-run after pull).

### 2) Device login inside cage (separate session)

No host secrets shared:

```bash
make cage-grok-up
make cage-shell
# [cage] grok login --device-auth
# open URL on any browser, enter code
```

Needs policy allow for `auth.x.ai` / `*.x.ai` (included in `coding-agent-grok`).

### 3) Shared mount of host auth.json (advanced)

Higher coupling: host and cage share the same file; concurrent refresh can race.

```bash
GROK_AUTH_MOUNT=1 make cage-grok-install   # generates mount-based override
```

### 4) API key only

```bash
echo 'XAI_API_KEY=xai-...' >> ~/.agentcage/.env
```

Only if you use console API keys; subscription browser users should prefer (1) or (2).

## Prerequisites

1. Base cage green (`make cage-up-mcp` + tests once).
2. Image `agent-cage-agent:latest` exists.
3. Auth: import, device-login, or API key as above.

## Make targets

| Target | Action |
|--------|--------|
| `grok-overlay-install` | Copy Dockerfile, compose override, policy into `~/.agentcage` |
| `grok-auth-import` | Copy host `~/.grok/auth.json` → `~/.agentcage/grok-home/` |
| `grok-overlay-build` | Build `pfy-mentat/agent-cage-grok:0.1.0` |
| `grok-up` | `up --mcp` with `coding-agent-grok` policy |
| `workspace-sync` | rsync catalog → `workspace/pfy-mentat` + MCP preset |
| `grok-mcp-preset` | project `.grok/config.toml` → filesystem MCP |
| `grok-smoke` | `grok --version` + auth.json readable |
| `grok-ready` | **T-0045** full smoke (version + workspace + MCP) |
| `grok-overlay-uninstall` | Remove overlay files (not host auth) |

Repo root: `make cage-grok-*` / `make cage-workspace-sync` / `make cage-grok-ready`.

## Security

- **Never commit** `auth.json` or cage `grok-home/`.
- Import copies a **credential** into `~/.agentcage/grok-home` — treat that dir like a secret store (`chmod 700`).
- Prefer import or device-auth over mounting full host `~/.grok` (skills/sessions are host-specific).
- Do not bake tokens into the Docker image layer.

## Files

| File | Purpose |
|------|---------|
| `Dockerfile` | FROM `agent-cage-agent:latest` + install Grok CLI binary |
| `docker-compose.override.yaml` | Image + `grok-home` volume + optional key |
| `coding-agent-grok.yaml` | Proxy allowlist including `*.x.ai`, `*.grok.com` |
| `presets/project.grok.config.toml` | Grok MCP → cage filesystem HTTP endpoint |
