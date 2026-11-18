# ADR-0007: Write-guard MCP as filesystem write mediation layer

- **Date:** 2026-07-12
- **Status:** Accepted (design); implementation phased

## Context

Agent-cage isolates the agent OS and network, but default MCP filesystem access is **full r/w under `/workspace`**. Operators also reported useful prior art: an MCP that mediated filesystem writes. We need a design that composes with agent-cage rather than replacing it.

## Decision

1. Keep **agent-cage (L0)** as the primary sandbox (network + OS isolation).
2. Add a **write-guard MCP (L2)** that mediates write/edit/delete with modes `off | audit | enforce`, roots, deny-globs for secrets, and JSONL audit.
3. Prefer **cage-first** deployment of write-guard; optional host Grok MCP later.
4. Do **not** treat stock filesystem MCP alone as sufficient for high-risk automation.
5. Implement as a **thin owned server** under this catalog (`harness/write-guard-mcp/` when coded), not a wholesale switch to a different mega-sandbox product-unless write-guard + cage fail empirically.

## Rationale

- Defense in depth: shell can still bypass MCP; container remains required.
- YAML policy + audit matches how we operate policies in agent-cage.
- Thin server is reviewable and pin-able like other tools.

Rejected alternatives:

1. **Stock FS MCP only** - no audit/secret globs.
2. **Replace cage with agent-infra/sandbox only** - duplicates network/OS work we already standardized on PNNL agent-cage.
3. **Host-only write-guard without container** - weaker for network and package installs.

## Consequences

- `WRITE_GUARD_MODE` / `WRITE_GUARD_ROOTS` in env registry.
- Overlay path for agent-cage MCP config.
- Future grok-in-image should include write-guard in the same versioned image story.

## References

- `docs/ops/write-guard-mcp-design.md`
- agent-cage `mcp-servers.yaml` filesystem server
