# Container integration-test framework

**Status:** Active (v0.1)  
**Primary harness:** [agent-cage (PNNL)](../../harness/agent-cage/) — Docker sandbox + MCP  
**Design:** pin tools (ADR-0003); do not embed large upstream trees  

## Goal

Use **versioned container images** so every catalog integration is:

- reproducible (image digest / pin SHA)
- isolated (host safe)
- MCP-capable
- comparable across tools and OSes (Linux / macOS / WSL via Make)

**Rule of thumb:** if you are integrating a catalog tool (LiteLLM, repowise, skills, colibri, …), the **smoke that proves it works** should run **inside agent-cage** (or a documented image derived from it), not only on the developer host. Host checks validate pins/JSON/CLI install only.

## Lifecycle (per tool)

```text
catalog pin (tools.json)
    → make -C harness/agent-cage up[-mcp]
    → install/run tool in cage workspace
    → smoke script + notes
    → update TOOLS.md scores/notes
    → make down
```

## Standard smoke contract

Each future `pipelines/smoke/<tool>/` (or `examples/integration-patterns/<tool>/`) should define:

| File | Content |
|------|---------|
| `README.md` | what is tested, host prerequisites |
| `run.sh` or Makefile target | idempotent smoke |
| `pins.env` | image tags, tool SHA, date |
| `results.latest.md` | last run outcome (optional CI artifact) |

Exit codes: `0` pass, `1` fail, `2` skipped (missing hardware/secrets).

## Why Make

Branching for Docker Desktop vs Engine, macOS vs Linux paths, and optional MCP is cleaner in Make than sprawling bash. Aligns with multi-developer harnesses used on other projects.

## Roadmap

1. ~~Select harness (agent-cage)~~  
2. Host smoke (`make smoke-host`)  
3. Full cage smoke (`make smoke-integration`)  
4. ~~First tool smokes: LiteLLM, codebase-memory, repowise, write-guard~~ — `make smoke-*`  
5. ~~Optional Grok-in-cage overlay~~ (see overlays/grok)  

One-shot DoD templates: [one-shot-example-dods.md](one-shot-example-dods.md).

## Related

- a private ops note  
- [TODO.md](../TODO.md)  
- [one-shot-example-dods.md](one-shot-example-dods.md)  

