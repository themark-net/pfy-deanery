# Evaluation: stretchcloud/claude-code-unified-agents

**Status:** PASS (curated I1) · **Date:** 2026-07-31  
**Source X:** https://x.com/i/status/2082997925014053075  
**GitHub:** https://github.com/stretchcloud/claude-code-unified-agents  

## Phase 0 - triage

- Open source (MIT), reproducible clone, agent skill markdowns  
- Fit: **skill pack / role library**, not a new primary runtime  
- Accept for Phase 1-4 as **paths + docs**, not full embed  

## Phase 2 - scores (pack level)

| Dimension | Score | Notes |
|-----------|------:|-------|
| Relevance | 4 | Strong role coverage for coding agents |
| Integration ease (Grok+cage) | 3 | Claude frontmatter/tools; portable via paths + PORT notes |
| Reproducibility | 5 | Public repo + install scripts |
| Unique value | 4 | Breadth; overlaps gstack/mattpocock/our first-party |

**Priority:** **A** (plan/use curated) - not S (not primary stack)

## Phase 3 - extensive agent eval loop

Script: `scripts/eval_unified_agents_pack.py`  
Receipt: `pipelines/eval/unified-agents-eval.latest.{md,json}`

- Per-agent: structural, content density, portability, uniqueness, relevance  
- Gate: structural≥3, overall≥3.2, body≥8 lines  
- Pack pass: pass_rate≥55% and mean overall≥3.3 → **achieved 98% / 4.06**

## Phase 4 - implementation

- Curated **16** skills under `skills-external/claude-unified-agents/`  
- Install path wiring + `--no-claude-ua`  
- Ops recipes + catalog triple-write  

## Non-goals

Claude Code as default operator UI; 54 first-party skills; domain mega-file first-party ports.
