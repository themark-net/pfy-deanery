# ADR-0001: Process docs and multi-file ADR layout

- **Date:** 2026-07-11
- **Status:** Accepted
- **Deciders:** project maintainers

## Context

The catalog and bootstrap are multi-agent and multi-session. Chat history loses pivots, rejected options, and TBDs. We need durable process artifacts that match the portable Grok skills (`adr`, `docs`, `open-questions`) already shipped in `bootstrap/grok-cli/`.

## Decision

Adopt this process layout as source of truth:

| Artifact | Path |
|----------|------|
| Master design (goals + shape) | `docs/DESIGN.md` |
| Architecture snapshot | `docs/ARCHITECTURE.md` |
| ADRs (multi-file) | `docs/adr/README.md` + `docs/adr/NNNN-*.md` |
| Central TODO | `docs/TODO.md` |
| Open questions index | `docs/OPEN_QUESTIONS.md` |
| Optional OQ detail / in-context notes | private ops notesOQ-NNNN-slug.md` and/or notes next to code/docs that **link to OQ IDs** |
| Agent entrypoint | `AGENTS.md` |

Rules:

1. Architecture pivots require an ADR including **paths decided against**.
2. Next steps live in `docs/TODO.md` with references to OQ IDs when blocked or uncertain.
3. Open questions are indexed centrally; context may also live beside the work that raised them, always with an OQ ID back-link.
4. Do not create a second decision log (`docs/DECISIONS.md` alongside `docs/adr/`).

## Rationale

- Multi-file ADRs keep large rationales reviewable in PRs without one giant log.
- Skills already prefer `docs/adr/` for new projects.
- Separating design (intent) from ADR (binding *why*) from TODO/OQ (execution) reduces doc thrash.

Rejected alternatives:

1. **Single-file `docs/DECISIONS.md` only** — Fine for tiny repos; this catalog will accumulate methodology and stack decisions; multi-file scales better and matches skill default for greenfield.
2. **Chat / session memory only** — Not reviewable in PRs; not reliable across agents/machines.
3. **GitHub Issues as sole ADR/TODO store** — Useful as optional mirror later; filesystem stays source of truth for offline and bootstrap reproducibility.

## Consequences

- Agents must read DESIGN + ADR index before non-trivial design work.
- Superseding a decision requires a new ADR and index update; never delete history.
- README and AGENTS.md point here for process.

## References

- `bootstrap/grok-cli/skills/adr/`, `docs/`, `open-questions/`
- DESIGN §6 Process model
