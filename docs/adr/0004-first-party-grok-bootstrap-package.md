# ADR-0004: First-party Grok bootstrap under `bootstrap/grok-cli/`

- **Date:** 2026-07-11
- **Status:** Accepted

## Context

Operator customizations (portable skills, ponytail path, codebase-memory MCP, config defaults) lived only on a single machine. The catalog’s “integrate” goal requires replay on new environments.

## Decision

Ship a **first-party integration package** at `bootstrap/grok-cli/` with:

- Vendored first-party skills (`adr`, `docs`, `open-questions`, `karpathy-guidelines`)
- External skills snapshot (ponytail) via `[skills].paths`
- Idempotent `install.sh` + surgical `merge_config.py`
- Manifest pins for upstream captures
- Catalog rows for bootstrap, codebase-memory-mcp, ponytail, karpathy

Do **not** store secrets or `auth.json` in-repo.

## Rationale

- Turns environment setup into versioned, reviewable code.
- Aligns with Grok-first interface (ADR-0002) without embedding the Grok binary.

Rejected alternatives:

1. **Document-only setup (README steps, no scripts)** - Drift-prone; hard to re-run.
2. **Subtree whole ponytail / codebase-memory repos** - Oversized vs skills snapshot + binary install; fails lean default (ADR-0003).
3. **Only publish skills to a separate skills repo** - Extra hop; this catalog is the integration home for the stack.

## Consequences

- Bootstrap is the supported install path for the operator env.
- Skill source of truth for first-party skills is under `bootstrap/grok-cli/skills/` (refresh via install).
- Config merge must remain surgical (preserve unrelated TOML / array tables).

## References

- `bootstrap/grok-cli/README.md`, `manifest.json`, TOOLS.md “Grok CLI bootstrap” row
