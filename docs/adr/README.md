# Architecture Decision Records (ADR)

**Store layout:** multi-file under `docs/adr/` (preferred for this project).  
**Process:** Grok skill `/adr` — full template and lifecycle in skill references.

## Index

| ID | Title | Status | Date |
|----|-------|--------|------|
| [0001](0001-process-docs-and-adr-layout.md) | Process docs + multi-file ADR layout | Accepted | 2026-07-11 |
| [0002](0002-grok-cli-primary-interface.md) | Grok CLI as primary operator interface | Accepted | 2026-07-11 |
| [0003](0003-default-pinned-commit-tracking.md) | Default tool tracking = pinned commit | Accepted | 2026-07-11 |
| [0004](0004-first-party-grok-bootstrap-package.md) | First-party Grok bootstrap under `bootstrap/grok-cli/` | Accepted | 2026-07-11 |
| [0005](0005-light-process-framework-not-heavy-tools.md) | Keep light DESIGN/ADR/TODO/OQ framework; do not replace with heavy tools | Accepted | 2026-07-11 |
| [0006](0006-deployment-profiles.md) | Deployment profiles local-only → max-performance + env registry | Accepted | 2026-07-12 |
| [0007](0007-write-guard-mcp-layer.md) | Write-guard MCP as filesystem write mediation layer | Accepted (design) | 2026-07-12 |
| [0008](0008-one-shot-workflow.md) | One-shot workflow: min questions, cheap iteration, lab prerequisites | Accepted | 2026-07-12 |
| [0009](0009-skill-port-hybrid-strategy.md) | Hybrid skill ports: first-party core + skills.paths snapshots | Accepted | 2026-07-12 |
| [0010](0010-reject-agenc-as-primary-runtime.md) | Reject AgenC as primary; Grok CLI + agent-cage; revisit if UX matures | Superseded by 0013 | 2026-07-12 |
| [0011](0011-hybrid-operator-surfaces-grok-opencode-ollama.md) | Hybrid surfaces: Grok primary + OpenCode/Ollama local-cloud split | Accepted (surfaces); **inference spine superseded by 0014** | 2026-07-25 |
| [0012](0012-voice-half-duplex-local-first.md) | Voice half-duplex local-first; no cloud full-duplex primary | Accepted | 2026-07-26 |
| [0012](0012-simple-harness-agnostic-launch.md) | Simple harness-agnostic `./pfy` launch (G8) — **cite this file, do not reuse ID** | Accepted | 2026-07-31 |
| [0013](0013-optional-operator-tuis-empirical-preference.md) | Treat operator TUIs (incl. AgenC) as optional scored components; empirical preference dimension | Accepted | 2026-07-27 |
| [0014](0014-pluggable-local-inference-spine.md) | Pluggable local inference spine (FreeToken → llama-swap/llama-server → Ollama) | Accepted | 2026-08-24 |
| [0015](0015-catalog-json-slim-subset.md) | Catalog JSON is a slim machine subset of TOOLS.md (not a 1:1 dump) | Accepted | 2026-08-24 |
| [0016](0016-jev-decision-layer.md) | Jev-style decision layer: typed Choice/Score; CUA-S1-FORMS primary local | Accepted | 2026-09-18 |
| [0019](0019-local-phoenix-otlp.md) | Local Phoenix OTLP for pipeline spans (0017 and 0018 stay reserved) | Accepted | 2026-11-11 |

## How to add

1. Next free `NNNN` (never reuse).
2. Create `docs/adr/NNNN-slug.md` from the skill template.
3. **Required:** rejected alternatives with concrete reasons.
4. Add a row to this index.
5. If layering changes, update `docs/ARCHITECTURE.md` and relevant DESIGN sections in the same change set.
6. Link related OQs; promote answered architectural OQs to ADR.

## Lifecycle

`Proposed` → `Accepted` | `Rejected`  
`Accepted` → `Superseded by NNNN` (new entry required; never silent overwrite)
