# ADR-0005: Keep light DESIGN/ADR/TODO/OQ framework (do not replace with heavy tools)

- **Date:** 2026-07-11
- **Status:** Accepted

## Context

We package process best practices as replayable skills + scaffolds. X/community research and classic tooling (Fowler/Nygard ADRs, adr-tools, emerging agent-ADR skills) show strong consensus for **in-repo markdown** decisions for multi-session agents. Heavier options exist (static ADR sites, issue-tracker-only process, experimental ADR enforcement products).

## Decision

1. **Default process kit** remains: `docs/DESIGN.md` + multi-file `docs/adr/` + `docs/TODO.md` + `docs/OPEN_QUESTIONS.md` + `AGENTS.md`, delivered by `bootstrap/project-process/` and skills `/project-process`, `/adr`, `/open-questions`, `/docs`.
2. **Do not** adopt a SaaS process platform or heavy static-site generator as the source of truth.
3. **Optional later:** pin `adr-tools` as a CLI convenience; revisit enforcement tools (e.g. Mneme-class) only if agents repeatedly ignore Accepted ADRs.

## Rationale

- Agent practitioners on X report large gains from local ADR files agents must read/write-not from new products.
- Templates already include **rejected alternatives**, matching industry ADR practice.
- Open-question / parking-lot products are not dominant for agent workflows; markdown fills the gap.
- Lean catalog principle (ADR-0003): avoid embedding platforms we do not customize.

Rejected alternatives:

1. **Replace with adr-tools only** - Numbers files well; no DESIGN/TODO/OQ, no agent skill workflow.
2. **Confluence / Linear as sole ADR+TODO store** - Poor offline/agent read path; optional mirror only.
3. **log4brains / full AKM platform** - Overhead for small multi-agent repos without proven need.
4. **Chat memory only** - Already rejected in ADR-0001.

## Consequences

- New projects use `init.sh` / `/project-process init`.
- Catalog lists adr-tools as optional B-tier companion, not a dependency.
- Revisit this ADR if enforcement or multi-team compliance becomes a measured pain.

## References

- `bootstrap/project-process/skills/project-process/references/evaluation.md`
- X/community: in-repo ADRs for coding agents; Fowler ADR bliki; npryce/adr-tools
- TOOLS.md rows: project-process bootstrap, adr-tools
