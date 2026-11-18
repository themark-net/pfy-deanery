# Evaluation: Exo (exoharness)

**Status:** I1 pattern extract · **Date:** 2026-07-31  
**GitHub:** https://github.com/exoharness/exo  
**Pin:** `372602d1b553af06e9843e19f31fa8a7f749ab6e`

## Phase 0-2 scores

| Dimension | Score | Notes |
|-----------|------:|-------|
| Relevance | 5 | Core harness / loop / long-running agent |
| Integration ease (Grok+cage) | 2-3 | Heavy stack (Rust+TS+Docker); OpenAI/OpenRouter first; not drop-in |
| Reproducibility | 4-5 | MIT, CI, docs, setup.sh |
| Unique value | 5 | True RSI: event log, rebuild guardian, sandbox rewind, skill artifacts |

**Overall ~81 · Tier A** - high unique value; **do not** make primary runtime.

## Self-mod evaluation (upstream)

**No formal numeric rubric.** Verification loop is operational (SELF-CONTROL §8):

snapshot → build/test → `rebuild_and_restart_exo(reason)` → observe event log → git/sandbox rollback on failure.

Gap: canary clone comparison not built.

## Our extraction

- Patterns: [exo-self-mod-patterns.md](../ops/exo-self-mod-patterns.md)  
- Ingest gates: [integration-self-mod-eval.md](../ops/integration-self-mod-eval.md)  
- Automation: `scripts/eval_integration_change.py`

## Decision

| Do | Don’t |
|----|-------|
| Pin + A-tier catalog | Primary runtime |
| Steal event-log + verify loop for **ingest** | Unattended monorepo RSI |
| Skills progressive-disclosure ideas | Embed full Exo tree |
