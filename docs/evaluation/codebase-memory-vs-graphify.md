# Decision note: codebase-memory-mcp vs Graphify

**Date:** 2026-07-25 · **Status:** Accepted operator posture (not a full ADR - tooling choice under ADR-0002)  
**Rubric:** [evaluation-framework.md](../evaluation-framework.md) S1-S4 · Cluster context: [knowledge-graph-cluster-overlap.md](knowledge-graph-cluster-overlap.md)

## Question

Is Graphify (X Entry 017) equivalent to **codebase-memory-mcp**, and should we run both?

## Answer

**Not equivalent.** Same job class (structured code context so agents stop rereading the tree), different packaging and integration cost.

| | **codebase-memory-mcp** | **Graphify** (Entry 017) |
|--|-------------------------|--------------------------|
| Role | Persistent **code-graph MCP server** for Grok | Tree-sitter **code → explicit graph** + agent hooks / MCP-capable marketing |
| Operator path | Bootstrap `--with-codebase-memory`, Grok `config.toml` | Not wired |
| Lab proof | `make smoke-codebase-memory` (green) | None in this repo |
| Catalog scores | **S1 92 / S2 88 / S3 95 / S4 85 → 91 S** | Catalog row B-tier reference (see TOOLS.md); not previously scored in tools.json |
| Overlap | Primary “map codebase for agent” | Medium redundancy vs CM + repowise (x-posts Entry 017 notes) |

**repowise** remains a **complement** (token-efficient retrieval; `make smoke-repowise`), not a Graphify substitute.

## Decision

1. **Primary code memory for Grok + cage:** codebase-memory-mcp.  
2. **Graphify:** catalog + comparison only until a scored head-to-head + in-cage smoke says otherwise.  
3. **Do not** run two full code-graph runtimes by default (process cost, dual truth).  
4. **Patterns** worth stealing from Graphify later: confidence-labeled edges (EXTRACTED/INFERRED/AMBIGUOUS), commit-trigger rebuild - without requiring Graphify as runtime.

## Rejected for now

| Option | Why not |
|--------|---------|
| Adopt Graphify as primary | No smoke, no bootstrap, overlaps CM job; violates “one primary MCP code memory” |
| Dual-run CM + Graphify always | Redundant context sources; operator confusion; no eval proving additive value |
| Drop CM for Graphify | Would discard working cage smoke and bootstrap wiring without lab proof |

## Re-open if

- Graphify gets a pin + `make smoke-graphify` (or MCP path) green in cage  
- Head-to-head on same fixture shows clear S1/S3 win over CM  
- Operator needs non-code asset graph (docs/PDF/media nodes) that CM does not cover

## Related

- TOOLS.md rows: codebase-memory-mcp (S), repowise (A), Graphify (B reference)  
- `pipelines/smoke/context-tools-compare.md`  
- ADR-0002 Grok primary interface  
