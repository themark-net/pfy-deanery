# Memory assist patterns (LEANN / Memvid / CM)

**Sources:** Entries 044 Memvid · 052 LEANN · active **codebase-memory-mcp**  
**Posture:** Patterns for coding agents; **CM remains primary** runtime ([codebase-memory-vs-graphify.md](../evaluation/codebase-memory-vs-graphify.md)).

## Layer map

| Layer | Tool / pattern | When |
|-------|----------------|------|
| Code graph MCP | **codebase-memory-mcp** | Default Grok index/search |
| Token-efficient retrieval | repowise | Complement CM, not replace |
| Extreme index compression | LEANN (pattern) | If local RAG size becomes the bottleneck - spike later |
| Versioned blob memory | Memvid (pattern) | If need git-like memory snapshots outside git |
| Process memory | TODO / OQ / hermes-feedback | Decisions and gotchas |

## Defaults (no human)

- Do **not** embed LEANN/Memvid subtrees.  
- Do **not** dual-run Graphify + CM.  
- New memory tool: structural eval green → docs/B-tier → optional smoke → only then promote.

## Agent checklist before adding memory tooling

1. Does CM smoke still green?  
2. Is the gap **compression**, **versioning**, or **query UX**?  
3. Prefer skill/docs over new binary until smoke exists.  
