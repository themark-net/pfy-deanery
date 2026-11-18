# Deployment profiles

**Status:** Design accepted in spirit; implementation incremental  
**Related:** [bootstrap/env/REGISTRY.md](../../bootstrap/env/REGISTRY.md), ADR-0006 (profiles), ADR-0007 (write-guard)

## Why

Integrations need a **knob**, not a single hard-coded stack:

| Gradient | Intent |
|----------|--------|
| **local-only** | Airgap-friendly / cost-control / privacy: no cloud required for core agent loops |
| **balanced** | Default: local models for bulk (edit, grep-class, simple gen); cloud (e.g. Grok) for hard planning/reasoning |
| **max-performance** | Quality/latency first: cloud primary; local optional fallback |

Anything between is a **custom profile** (copy `balanced.env` → `config/profiles/custom.env` + `.env` secrets).

## How selection works

```text
DEPLOY_PROFILE=balanced
        │
        ▼
config/profiles/balanced.env   (non-secret defaults)
        │
        ▼
.env / environment             (secrets + operator overrides)
        │
        ▼
tools (Grok, LiteLLM, cage, Ollama, …)
```

Init:

```bash
make env-init                 # .env from example if missing
# edit .env: set DEPLOY_PROFILE and secrets
make env-check                # validate required vars for profile
```

## Routing sketch (LiteLLM + CLI surfaces)

| Profile | Default completion | Operator surface | Fallback |
|---------|-------------------|------------------|----------|
| local-only | `ollama/*` | OpenCode and/or LiteLLM; Grok optional offline | fail closed if local down |
| balanced | local for bulk; Grok/xAI for hard | **OpenCode+Ollama** bulk · **Grok** hard | escalate after error threshold |
| max-performance | Grok / strong cloud | Grok primary | local if rate-limited |

**CLI policy:** [ADR-0011](../adr/0011-hybrid-operator-surfaces-grok-opencode-ollama.md) · [local-cloud-split.md](local-cloud-split.md).

Exact model IDs and cage URLs: **[config/litellm/](../../config/litellm/README.md)** - `local-only.yaml`, `balanced.yaml`, `max-performance.yaml` (T-0012 complete).  
In-cage local smoke: `make smoke-litellm-ollama` (host gateway port **11435** when Ollama is localhost-only).  
Host OpenCode adapter: [bootstrap/opencode/README.md](../../bootstrap/opencode/README.md).
Cloud aliases need `XAI_API_KEY` + `LITELLM_CLOUD_MODEL` in the environment (never commit keys).

### Grok Build auth (not just an API key)

Interactive **Grok CLI / Grok Build** uses **browser OIDC** (`grok login` → `auth.x.ai`) and stores the session in **`~/.grok/auth.json`** (`auth_mode: oidc`, refresh tokens).  

`XAI_API_KEY` from console.x.ai is only a **fallback** when no session exists (CI). For agent-cage, prefer:

1. `make cage-grok-auth-import` (copy host `auth.json` into `~/.agentcage/grok-home/`), or  
2. `grok login --device-auth` inside the cage shell.

See `harness/agent-cage/overlays/grok/README.md`.

## Cage interaction

- **local-only:** cage still useful for isolation; allowlist should include local registries/Ollama host gateway as needed.
- **balanced / max-performance:** cage proxy must allow required cloud API hosts (document per tool in REGISTRY + policy notes).
- Secrets: inject at **runtime** into host processes or cage env files that are **not** committed and **not** baked into images.

## Gradient extensions (future)

- `balanced-cpu` / `balanced-gpu`
- `max-performance-eu` (region-constrained endpoints)
- Cost caps: max cloud tokens/day via LiteLLM budgets

Record new named profiles under `config/profiles/` and a row in REGISTRY when promoted.
