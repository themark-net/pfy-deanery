# Evaluation Framework for Local LLM Dev Tools Catalog

**Status:** v1.4 — 2026-07-25  
**Purpose:** Consistent triage → score → optional implementation into the **Grok + agent-cage** operator stack.  
**Extension:** Design/coding assist lanes (structural / implement) — [evaluation/design-coding-assist-rubric.md](evaluation/design-coding-assist-rubric.md) · `data/eval-lanes.json`

**Operator defaults:** Grok Build CLI ([ADR-0002](adr/0002-grok-cli-primary-interface.md)), agent-cage lab, LiteLLM/Ollama as needed.  
**Not default:** AgenC primary runtime ([ADR-0010](adr/0010-reject-agenc-as-primary-runtime.md)).

## Full evaluation pipeline

### Phase 0: Triage & relevance gate
- Local/self-hosted value, open source/reproducible, pipeline fit.
- If the item is a full multi-agent **AI company** (org chart + personas + shared consensus + cycle autonomy), route to the **company rubric** instead of (or in addition to) the generic 1–5 table.
- **Suite overlap:** mark which parts of our suite the tool covers (track, catalog, evaluate, integrate) at none, partial, or full. Two or more parts at partial or full makes it a supersede candidate: tag `#supersede-candidate` and add it to `data/supersede-watchlist.json` (`python3 scripts/supersede_check.py --parts track=partial,catalog=partial`). A part name with no level is not coverage. All four in full is a stop-and-decide for Mark ([supersede-watch.md](ops/supersede-watch.md)).
- Accept → Phase 1, Defer, or Reject.

### Phase 1: Initial cataloging
- Add structured entry to `sources/x-posts.md` (append; never replace the whole log).
- Triple-write when scoring: `TOOLS.md` + `data/tools.json` + sources notes.
- Capture attributes (relevance, tags, github).

### Phase 2: Attribute scoring
- **Standard tools:** Apply rubric table below.
- **Autonomous AI Companies:** Apply [autonomous-ai-companies-rubric.md](evaluation/autonomous-ai-companies-rubric.md) (6 dimensions + Stage 0 gate).
- Update cluster notes in `docs/scoring-summary.md` when useful.

### Phase 3: Integration feasibility
- Map to: Grok skill, cage smoke, eval task, LiteLLM recipe, docs-only, or OQ.
- For companies: default is **pattern extraction** (personas, consensus baton, pre-mortem, cycle gates) — not full daemon adoption.
- Effort + priority (S/A/B/C).

### Phase 4: Implementation (only when justified)
Concrete change to **this** environment, e.g.:
- first-party skill under `bootstrap/grok-cli/skills/`
- in-cage `make smoke-*` or eval task
- module/ops docs
- **not** installing demoted runtimes without ADR

Guidance checker (non-authoritative): `python3 bootstrap/setup-local-agent-env.py`

## Rubric (1–5 dimensions) — standard tools

| Dimension | 5 | 3 | 1–2 |
|-----------|---|---|-----|
| Relevance to local agent workflows | Core loop/memory/safety/inference | Niche | Tangential |
| Integration ease with **Grok + cage** | Make smoke / skill path clear | Moderate glue | Poor fit / heavy embed |
| Reproducibility | Docs + install + maintained | Partial docs | Closed / fragile |
| Unique value | Clear gap vs catalog | Overlaps existing | Redundant |

**Overall priority:** S (act) · A (plan) · B (reference) · C (awareness)

## Autonomous AI Companies — separate rubric

Full multi-agent simulated companies (org + personas + consensus + cycles) use:

**[evaluation/autonomous-ai-companies-rubric.md](evaluation/autonomous-ai-companies-rubric.md)**

| Dimension | Weight |
|-----------|--------|
| Org Design & Role Fidelity | 20% |
| Autonomy & Cycle Design | 20% |
| Shared Memory & Consensus | 15% |
| Safety & Blast Radius | 15% |
| Economic Realism & Convergence | 15% |
| Local / Operator Fit | 15% |

Do not collapse these into Stage 1–4 tool scores alone.

## Alignment notes

- Prefer pins + smokes over subtrees ([ADR-0003](adr/0003-default-pinned-commit-tracking.md)).
- Integration depth: [ops/integration-stages.md](ops/integration-stages.md) (I0–I4) · registry `data/tool_integration_stages.json`.
- Golden-task model eval: [ops/local-model-storage-and-eval.md](ops/local-model-storage-and-eval.md) · `make eval-golden`.
- Skill ports: hybrid first-party + paths ([ADR-0009](adr/0009-skill-port-hybrid-strategy.md)).
- Empirical lab receipts beat X hype: `pipelines/smoke/*`, `pipelines/eval/*`.

## Related

- [scoring-summary.md](scoring-summary.md)  
- [CATEGORIZATION.md](../CATEGORIZATION.md)  
- [evaluation/autonomous-ai-companies-rubric.md](evaluation/autonomous-ai-companies-rubric.md)  
- [evaluation/design-coding-assist-rubric.md](evaluation/design-coding-assist-rubric.md) — process skills + structural lane  
- [ops/human-decision-inventory.md](ops/human-decision-inventory.md) — batch OQs; pending decision count  
- [TODO.md](TODO.md) · T-0042 catalog re-score  
- Automated: `make eval-structural` (no LLM) · `make eval-v02` (needs Ollama)
