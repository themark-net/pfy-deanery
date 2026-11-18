# ADR-0009: Hybrid skill-port strategy (first-party core + paths snapshots)

- **Status:** Accepted
- **Date:** 2026-07-12
- **Deciders:** operator (OQ-0006)
- **Related:** OQ-0006, ADR-0003, ADR-0004, ADR-0005, T-0011, T-0014

## Context

External skill packs (mattpocock/skills, marketing-council, gstack) are high-value but large. Full-embedding violates pin/lean policy (ADR-0003) and light-process stance (ADR-0005). We already vendor **ponytail** without copying it into `~/.grok/skills`.

## Decision

Use **hybrid (OQ-0006 option 4)**:

1. **First-party core** - small number of skills we **own and edit** under `bootstrap/grok-cli/skills/` (and mirrored `.grok/skills/`). Installed into `~/.grok/skills/` by `install.sh`.
2. **paths snapshots** - bulk/curated upstream packs under `bootstrap/grok-cli/skills-external/<name>/`, registered via Grok **`[skills].paths`** (scanned, not copied into `~/.grok/skills/`). Same mechanism as ponytail.
3. **Docs-only** - role recipes / AGENTS patterns for material we will not install (e.g. most of gstack’s 23 skills) until a port earns first-party or snapshot status.

### What “ponytail method” means (apply to the rest)

| Technique | Ponytail practice | Apply to other packs |
|-----------|-------------------|----------------------|
| **Snapshot, don’t embed tree** | Only `skills/` vendored under `skills-external/ponytail/` | Curated subset only; no full monorepo |
| **`skills.paths` not copy** | Config points at repo path; `git pull` updates snapshot | Same for mattpocock subset, optional later packs |
| **Pin / refresh deliberately** | Pin commit in manifest; rsync refresh documented | Pin SHA + refresh recipe in package README |
| **Opt-out install** | `--no-ponytail` | `--no-<pack>` when adding more paths |
| **Do not rewrite for Grok unless core** | Ponytail stays upstream-shaped | First-party ports only when we need Grok-specific wording or process glue |

### How we decide **core** (first-party) skills

A skill is **core** only if **most** of the following hold:

1. **Process backbone** - used across projects (adr, docs, open-questions, one-shot, catalog-docs, project-process).
2. **We will edit it** - catalog- or Grok-specific; not a thin mirror of upstream.
3. **Small surface** - one skill (or a tight set), not a 20-skill tree.
4. **Default on every install** - every operator should get it without choosing a pack.
5. **No AGPL/license surprise** for embedding in first-party tree (prefer MIT/Apache-style; AGPL packs stay paths/docs).

Otherwise: **paths snapshot** (curated) or **docs-only**.

### Initial placement (Phase 1 ports)

| Source | Placement | Notes |
|--------|-----------|--------|
| marketing-council (core pattern) | **First-party** port of council/dissenter SKILL(s) | Small, process-shaped; rewrite for Grok |
| mattpocock plan/review/TDD subset | **paths snapshot** curated subset | Like ponytail; pin + skills.paths |
| gstack | **Docs + AGENTS recipes** first; optional **first-party method rewrite** only | Avoid full embed (T-0014). Eval: [gstack-skill-port-comparison.md](../ops/gstack-skill-port-comparison.md) - raw paths blocked; top candidate **investigate** method (T-0017) |
| ponytail | Already **paths snapshot** | Template for bulk packs |
| karpathy-guidelines | Already **first-party** (vendored single skill) | Fits core criteria |

## Rejected alternatives

| Option | Why rejected |
|--------|----------------|
| All first-party ports | Rewriting large trees; drift and maintenance cost |
| All paths snapshots | No owned process glue; hard to enforce catalog-docs/one-shot standards |
| Docs-only for everything | Leaves installable value on the table for council/plan skills |
| Full gstack embed | Violates ADR-0003; huge surface, Claude-specific |

## Consequences

- T-0011 unblocked under hybrid rules.
- install.sh may gain additional `skills.paths` entries over time; keep opt-out flags.
- Catalog TOOLS notes should say “first-party port” vs “paths snapshot” vs “docs pattern” vs “raw-port-blocked”.
- Supersedes open state of OQ-0006 (promoted here).
- **2026-07-12 deeper-port eval:** gstack skills are not raw-paths candidates; optional single deeper port is a **first-party rewrite of the investigate (RCA) method** (T-0017), not a gstack tree snapshot.
