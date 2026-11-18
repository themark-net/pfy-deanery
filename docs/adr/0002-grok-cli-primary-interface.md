# ADR-0002: Grok CLI as primary operator interface

- **Date:** 2026-07-11
- **Status:** Accepted

## Context

The catalog spans many coding agents and harnesses (Continue, Aider, Claude-compatible tools, etc.). Integration work needs a default operator surface so bootstrap, skills, and MCP wiring are not duplicated for every agent.

## Decision

Treat **Grok CLI** as the **primary** interface for operating this stack initially. Other toolsets remain first-class **catalog entries** and may be recommended as hybrid/fallback when scoring shows a better fit for a task class.

## Rationale

- Repo goals already name Grok CLI as primary.
- Existing operator customizations (skills, MCP) are Grok-native and now replayable via bootstrap.
- Catalog still evaluates alternatives fairly via the rubric.

Rejected alternatives:

1. **Agent-agnostic-only repo (no preferred CLI)** - Delays a working operator path; weakens “integrate” goal.
2. **Continue.dev or Aider as primary** - Strong catalog candidates; not where current skills/MCP wiring live.
3. **Custom greenfield agent harness first** - High cost before catalog value; YAGNI until gaps are scored.

## Consequences

- Bootstrap targets `~/.grok/` and Grok MCP config.
- Integration notes in TOOLS.md prioritize Grok compatibility without ignoring other tags (`#ide-integration`, etc.).
- Revisit if empirical pipeline work shows another harness consistently higher for core workflows (superseding ADR required).
- **2026-07-12:** AgenC trial rejected as primary (TUI/UX) - [ADR-0010](0010-reject-agenc-as-primary-runtime.md) **affirms** this ADR; Grok CLI remains primary.

## References

- README goals; `bootstrap/grok-cli/`; TOOLS.md integration column
- ADR-0010 (AgenC not primary)
