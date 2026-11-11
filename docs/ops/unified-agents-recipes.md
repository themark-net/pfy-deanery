# Claude Code Unified Agents → pfy-deanery (eval + integration)

**X:** https://x.com/i/status/2082997925014053075  
**Upstream:** https://github.com/stretchcloud/claude-code-unified-agents  
**Pin:** see `bootstrap/grok-cli/skills-external/claude-unified-agents/manifest.json`  
**Eval receipt:** `pipelines/eval/unified-agents-eval.latest.md`  
**Stage:** **I1** paths pack (ADR-0009) — not Claude Code primary (ADR-0002)

## Eval loop result (2026-07-31)

| Metric | Value |
|--------|------:|
| Agents scored | 53 |
| Structural pass gate | **98%** |
| Mean overall | **4.06** |
| Pack decision | **PASS → curated integrate** |

Re-run:

```bash
python3 scripts/eval_unified_agents_pack.py --root /path/to/agents
make eval-unified-agents   # if registered
```

## What we integrated

| Layer | Location |
|-------|----------|
| Curated paths skills (16) | `bootstrap/grok-cli/skills-external/claude-unified-agents/*/` |
| Install | `install.sh` registers path (opt-out `--no-claude-ua`) |
| Catalog | TOOLS.md + tools.json + sources entry |
| Role map | this file |

## Prefer first-party when both exist

| Unified agent | Prefer in pfy-deanery |
|---------------|----------------------|
| orchestrator | `/agent-loops` + `/worker-monitor` |
| error-detective | `/investigate` |
| code-reviewer | mattpocock `code-review` |
| context-manager | `/hermes-feedback` |
| documentation-writer / technical-writer | `/docs` `/catalog-docs` |
| requirements-analyst | mattpocock `to-spec` |
| test-engineer | `make smoke-*` / `eval-structural` |

## High-value paths skills (use when specialty needed)

- **security-auditor** — OWASP-oriented review posture  
- **e2e-test-specialist** — Playwright/Cypress strategies  
- **accessibility-auditor** — WCAG  
- **api-designer** — OpenAPI/REST  
- **devops-engineer** / **incident-responder** / **performance-engineer**  
- **backend-architect** / **database-specialist**  
- **prompt-engineer** / **ai-engineer**  
- **ux-designer**

## What we did *not* do

- Install all 54 agents as default first-party  
- Subtree-embed the upstream monorepo  
- Adopt Claude Code `/agents` as primary UI  
- Port multi-thousand-line domain code dumps (game/healthcare) into core

## Operator invoke examples

```text
Use security-auditor posture on this diff — OWASP focus, no drive-by refactors.
Use e2e-test-specialist: propose Playwright smoke for the voice remote path.
Use backend-architect: sketch service boundaries for product-ship remote.
```
