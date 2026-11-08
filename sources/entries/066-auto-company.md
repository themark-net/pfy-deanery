### Entry 066: Auto-Company — Fully Autonomous AI Company (14 Expert Personas + consensus.md)

- **URL**: https://x.com/i/status/2079230095345209479
- **Date**: 2026-07-20
- **Poster**: Rimsha Bhardwaj (@heyrimsha) highlighting Max Miksa / Max Kong (@MaxMiksa, Carnegie Mellon)
- **Summary / Key Claims**: Open-sourced autonomous AI company that runs 24/7 on a personal PC. Fourteen AI agents with real mental models (CEO=Jeff Bezos, CTO=Werner Vogels, engineer=DHH, marketer=Seth Godin, critic/inversion=Charlie Munger, plus product/UI/ops/sales/QA/research/etc.). Workflow converges: Cycle 1 brainstorm → Cycle 2 Munger pre-mortem + market/unit-econ GO/NO-GO → Cycle 3+ build/deploy/ship. Pure discussion loops forbidden. Shared memory is a single markdown file `memories/consensus.md` (human edits "Next Action" to steer). 30+ reusable skills (research, scrape, financial modeling, SEO, security audit…). Runs on Claude Code or Codex CLI; native daemon on macOS, Windows (WSL), Linux; local dashboard for cycle status, spend, active agents. Early: real API cost per cycle, stability not guaranteed, cannot replace a real company — but the blueprint is a git clone.
- **Extracted Repos / Tools**: https://github.com/MaxMiksa/Auto-Company (~1.3k stars at capture; MIT/open; docs/ per role; scripts for daemon). CLAUDE.md defines mission ("Make money legally"), safety guardrails table, team architecture.
- **TOOLS.md Link**: Primary row under **Autonomous AI Companies** (new category). Company rubric weighted **4.7 → S-tier**. Cross-refs Multica, gstack, paperclipai/companies, Claude Company 037.
- **Company scores (C1–C6)**: Org 5 · Cycle 5 · Memory 5 · Safety 4 · Econ 4 · Local 5 · Weighted 4.7 · **S**
- **Notes**: User requested a **completely separate category** and **separate evaluation rubric** for these "company" setups. Delivered:
  1. Primary category **Autonomous AI Companies** in CATEGORIZATION.md
  2. Dedicated rubric [docs/evaluation/autonomous-ai-companies-rubric.md](../docs/evaluation/autonomous-ai-companies-rubric.md)
  3. Cluster 5 in scoring-summary.md
  4. TOOLS.md company section + data/tools.json v0.4.3
  Integration posture: **extract patterns** (named personas, consensus.md baton, Munger pre-mortem, forbidden-action table, squad formation, cycle gates) into Grok skills / AGENTS.md — do **not** adopt as primary operator runtime without ADR (aligns ADR-0010).
- **Status**: STAY I1 reference (read 2026-11-07). Pin `211baad12b08d25c75b10ade86ed301098be69b2` is package 3.0.0, MIT. Both GitHub URLs resolve to that commit. Patterns already in `docs/ops/auto-company-patterns.md` (T-0055). No install, no daemon, no code copy. Gap B is unchanged. Receipt: `eval/evq1107/auto-company/REPORT.md`. No Feature GO.
