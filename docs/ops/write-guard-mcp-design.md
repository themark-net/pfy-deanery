# Write-guard MCP - design

**Status:** Proposed design (implement on this branch as scaffold; full server can follow)  
**Motivation:** Local file writes from agents are a blast-radius risk. Container isolation (agent-cage) helps; an MCP that **mediates filesystem writes** adds a second, policy-driven layer - useful on host *and* in-cage.

## What you may have seen before

Likely sources (not mutually exclusive):

| Pattern | Where it shows up |
|---------|-------------------|
| **MCP filesystem server** limited to a root (`/workspace`) | agent-cage default `mcp-servers.yaml` (`@modelcontextprotocol/server-filesystem`) |
| **Custom write interceptor** (allowlist paths, audit log, deny deletes) | Other harnesses / “sandbox agent” MCP bridges |
| **OS sandbox** (bubblewrap, gVisor, Docker) | cleat, agent-cage, agent-infra/sandbox |

agent-cage today: **full r/w to `/workspace`** via stock filesystem MCP - good boundary vs host home, **not** fine-grained write policy inside workspace.

## Layered model (recommended)

```text
┌─────────────────────────────────────────────────────────┐
│ L3 Host: bind-mount only workspace; secrets not mounted   │
├─────────────────────────────────────────────────────────┤
│ L2 Write-guard MCP: policy on write/edit/delete/rename    │
│     modes: off | audit | enforce                          │
├─────────────────────────────────────────────────────────┤
│ L1 Stock FS MCP roots OR replace with write-guard only    │
├─────────────────────────────────────────────────────────┤
│ L0 Container (agent-cage): network policy + OS isolation  │
└─────────────────────────────────────────────────────────┘
```

Do **not** remove L0 if L2 exists - defense in depth.

## Write-guard MCP - behavior

### Tools (conceptual)

| Tool | Behavior under `enforce` |
|------|---------------------------|
| `read_*` | Allow if path under `WRITE_GUARD_ROOTS` |
| `write_file` / `edit` | Allow only if path matches allow policy; else deny |
| `delete` / `rename` | Default deny unless explicitly allowed |
| `list_dir` / `search` | Read-only under roots |
| `write_status` | Return last N audit events (debug) |

### Policy file (YAML sketch)

```yaml
# config/write-guard/policy.default.yaml
roots:
  - /workspace
deny_globs:
  - "**/.env"
  - "**/.env.*"
  - "**/auth.json"
  - "**/*secret*"
  - "**/*.pem"
allow_write_globs:
  - "/workspace/**"
deny_write_globs:
  - "/workspace/.git/**"      # optional: force git via shell policy instead
modes:
  default: audit              # overridden by WRITE_GUARD_MODE
audit_log: /workspace/.write-guard-audit.jsonl
```

### Modes

| Mode | Writes |
|------|--------|
| `off` | Pass-through (or disable server) |
| `audit` | Allow write; append JSONL audit (path, tool, hash, ts) |
| `enforce` | Deny if policy fails; always audit |

### Deployment

1. **In agent-cage:** add server to `mcp-servers.yaml` (overlay), prefer **replace** stock filesystem write tools or put write-guard **in front** as the only write path.
2. **On host Grok:** optional MCP in `~/.grok/config.toml` pointing at `write-guard` stdio server with roots = repo path - higher friction for local ops; start with **cage-only**.
3. **Image:** install server in a **versioned** cage overlay image when mature (same story as grok-in-image).

## Implementation plan (incremental)

| Phase | Deliverable |
|-------|-------------|
| A | This design + OQ/ADR + env keys in REGISTRY |
| B | Minimal Python stdio MCP: roots + audit + enforce deny secrets globs |
| C | Overlay `mcp-servers.write-guard.yaml` for agent-cage |
| D | Optional human-approve queue for high-risk globs (async) |

## Redesign vs reuse

| Option | Pros | Cons |
|--------|------|------|
| Stock FS MCP only | Simple | No audit/fine policy |
| **Write-guard MCP (new thin server)** | Fits our stack; auditable; profile-aware | We maintain code |
| Full agent-infra/sandbox | Feature-rich | Heavier; may duplicate cage |
| AppArmor/seccomp only | Strong | Harder to iterate policy in YAML |

**Decision lean:** implement a **thin write-guard MCP** we own under `harness/write-guard-mcp/` (or `tools/write-guard-mcp/`), compose it with agent-cage; do not replace agent-cage with a different mega-sandbox unless write-guard proves insufficient.

## Security notes

- Audit logs may include path names - keep under workspace; don't log file contents by default.
- `enforce` + secrets globs reduce accidental key commits from agents.
- Still assume a malicious agent with shell can bypass MCP - L0 container + no host mounts for `$HOME` remains mandatory.
