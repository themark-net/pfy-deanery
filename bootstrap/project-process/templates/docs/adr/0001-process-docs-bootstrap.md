# ADR-0001: Process docs bootstrap (DESIGN / ADR / TODO / OQ)

- **Date:** {{DATE}}
- **Status:** Accepted
- **Deciders:** project maintainers

## Context

New project needs durable process so multi-session agents do not re-litigate decisions or lose TBDs. This layout is the portable standard from `pfy-deanery` project-process bootstrap.

## Decision

Adopt:

| Artifact | Path |
|----------|------|
| Master design | `docs/DESIGN.md` |
| Architecture snapshot | `docs/ARCHITECTURE.md` |
| ADRs (multi-file) | `docs/adr/` |
| Central TODO | `docs/TODO.md` |
| Open questions | `docs/OPEN_QUESTIONS.md` + optional `docs/open-questions/` |
| Agent entry | `AGENTS.md` |

Rules: pivots → ADR with rejected alternatives; work → TODO; uncertainty → OQ (central index); no second decision log.

## Rationale

- Filesystem markdown is reviewable in PRs and works offline.
- Aligns with agent skills (`/adr`, `/open-questions`, `/docs`).
- Separates intent (DESIGN), binding why (ADR), and execution (TODO/OQ).

Rejected alternatives:

1. **Chat / session memory only** — not durable across agents or machines.
2. **Issue tracker as sole ADR store** — optional mirror later; repo remains source of truth.
3. **Single giant DECISIONS.md only** — acceptable for tiny repos; multi-file preferred for growth.

## Consequences

- Agents must read DESIGN + ADR index before non-trivial design work.
- First domain decisions get ADR-0002+.
- Superseding requires a new ADR; never delete history.

## References

- Scaffolded by `bootstrap/project-process` from pfy-deanery
