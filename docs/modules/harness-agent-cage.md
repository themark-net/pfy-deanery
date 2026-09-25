# Module: harness/agent-cage

**Purpose:** **Primary integration lab** — versioned Docker sandbox (PNNL agent-cage) so catalog tools are proven **inside** isolation (network policy + MCP), not only on the host.

## Operator: how to run

From **catalog repo root**:

```bash
./pfy stage --lab          # host only: make cage-doctor → cage-setup → cage-up-mcp
# Names the cage bind (~/.agentcage/workspace/pfy-mentat → /workspace/pfy-mentat). That is not the host checkout.
# Already under /workspace: refuses. Run it on the host.
# Missing Docker: honest skip (lab skipped, not product-ready). Exit 0 on skip.
# Docker present but a make step fails: non-zero; prints which step / target.
# ./pfy start agent-cage stays STUB exit 2 and points at ./pfy stage --lab.

export PATH="$HOME/.local/bin:$PATH"
make cage-doctor
make cage-setup          # CLI + optional pin clone
make cage-init           # once → ~/.agentcage
make cage-up-mcp         # start stack
make cage-status && make cage-test
make cage-shell          # /workspace ← ~/.agentcage/workspace
make cage-down
```

| Path | Role |
|------|------|
| `~/.agentcage` | Runtime project (compose, policies, workspace) |
| `~/.local/share/pfy-mentat/agent-cage` | Optional source pin checkout |
| `harness/agent-cage/PINNED_COMMIT` | Upstream pin |
| `overlays/grok/` | Grok-in-image + OIDC auth mount |
| `overlays/local-ollama/` | Host Ollama allowlist + compose fragment |
| `overlays/write-guard/` | MCP fragment for write-guard (optional enable) |

Package README: [harness/agent-cage/README.md](../../harness/agent-cage/README.md)

## Where variables live

| Variable | Role |
|----------|------|
| `AGENTCAGE_DIR` | Runtime project (default `~/.agentcage`) |
| `POLICY` | Policy file stem under `policies/` |
| `DEPLOY_PROFILE` | Profile for env-check / recipes |
| `OLLAMA_HOST` / `OPENAI_BASE_URL` | Host vs cage URLs — see [REGISTRY](../../bootstrap/env/REGISTRY.md) |
| Cage Grok auth | `make cage-grok-auth-import` → `~/.agentcage/grok-home/auth.json` (agent-owned 0600; host cannot read after import — expected) |
| Sessions store perms | `make -C harness/agent-cage fix-grok-state-perms` — dual host/agent write under `~/.agentcage/grok-state/sessions` (avoids import Permission denied) |
| First-party skills in cage | `make cage-grok-skills-install` (also from `cage-grok`); project `.grok/skills` synced on workspace-sync |
| Host ↔ cage code bridge | **`make cage-code-sync`** (from-cage then to-cage); [docs/ops/cage-code-sync.md](../ops/cage-code-sync.md) — run on host only |
| Catalog in workspace | `make cage-workspace-sync` → `/workspace/pfy-mentat` |
| Grok + filesystem MCP ready | `make cage-grok-ready` (T-0045) |
| Launch Grok session | `make cage-grok` then `cage-grok-shell` or `cage-grok-run` |

## Agent map

| Concern | Detail |
|---------|--------|
| **Invariants** | Integration smokes for catalog tools run **in-cage** (ADR harness practice); `agentcage up` may ignore extra compose `-f` — Grok/local-ollama targets call compose explicitly |
| **Network** | Agent → mitmproxy whitelist only; host Ollama needs gateway + policy (`coding-agent-local`) |
| **Do not** | Confuse runtime `~/.agentcage` with this git repo; commit secrets into compose |
| **ADR** | ADR-0003 (pins), ADR-0006 (profiles), ADR-0007 (write-guard layer) |
| **Smokes** | [examples-smokes.md](examples-smokes.md) |

## Verify

```bash
make cage-status
make cage-test                 # policy tests (stack up)
make smoke-write-guard         # optional tool smokes
```

## Harness filesystem

`./pfy start` prints one of two modes and exports `PFY_FS` and `PFY_FS_ROOT` into the child.

| `PFY_FS` | Root the harness should use | Navigation |
|----------|-----------------------------|------------|
| `direct` | The host repo (`PFY_FS_ROOT`, normally the catalog checkout) | The process sees that directory. No proxy. |
| `cage` | `/workspace/pfy-mentat` when the process is already under `/workspace` | Bind mount of `~/.agentcage/workspace/pfy-mentat`. Grok uses the filesystem MCP on that tree. Host paths are a different directory. |

Host and cage are not one filesystem. `make cage-code-sync` copies commits between them. Docker on PATH does not switch the mode.

## Not yet

- `./pfy start agent-cage` (always STUB exit 2). Docker on PATH is **not** ready.
- Treating cage as product-ready. Optional personal lab is `./pfy stage --lab` / `make cage-*` (doctor → setup → up-mcp). Missing Docker is honest skip. Do not sell cage.
