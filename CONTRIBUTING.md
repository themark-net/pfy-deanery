# Contributing to pfy-mentat

Thank you for helping improve the catalog of local LLM development tools, agents, frameworks, and infrastructure.

This repo's core purpose is to **Track • Categorize • Rank • Integrate** high-value, self-hosted or local-first components that improve Grok CLI workflows, MCP-style code memory, agentic pipelines, and iterative tool evaluation.

We prioritize practical, reproducible improvements in efficiency (tokens, latency, cost), integration ease, and pipeline robustness over hype or raw benchmark chasing.

## How to Contribute

### 1. Adding a New Tool or Framework (from X post, GitHub, paper, or personal discovery)

1. **Seed the source** — Add a structured entry to `sources/x-posts.md` (or `sources/aggregates.md` for list repos) following the exact format of existing entries (see Entry 00X examples). Include post URL, poster, summary of claims, extracted repo(s), and initial notes on relevance.
2. **Evaluate using the rubric** — Apply the staged scoring in `CATEGORIZATION.md` (Stage 0 gate + S1–S4 weighted). Be honest about overlaps with existing entries (e.g., repowise vs codebase-memory-mcp). Document reasoning in the entry and in `TOOLS.md` Notes.
3. **Update the master catalog**:
   - Add a row to the table in `TOOLS.md` (under the appropriate primary category).
   - Add a corresponding object to the `tools` array in `data/tools.json` (include pinned commit where applicable, tags, notes on Grok CLI / MCP / pipeline fit).
4. **Track tracking method** — Most tools use pinned commit + shallow clone. Only propose `git subtree` for small, high-value, heavily customized components that meet the strict criteria in `SUBTREES.md`.
5. **Open a PR** with clear description linking the X post / source and the evaluation notes.

### 2. Improving Existing Entries

- Update scores only after hands-on integration attempts (e.g., wiring into Grok CLI, running in a gom-jobbar-style agent, or benchmarking token/latency impact).
- Append empirical results to the Notes column in `TOOLS.md` and the JSON object.
- Re-score when major releases or new integration data appears.

### 3. Process & Documentation Changes

- Architecture or major process shifts → create or update an ADR in `docs/adr/` (follow the template and include rejected alternatives).
- Unsettled questions or experiments → open an Issue. Maintainers track open questions privately and record answers as ADRs in `docs/adr/`.
- Small improvements to docs, categorization, or bootstrap scripts are welcome via direct PR.

## Evaluation Standards

We use the rubric in `CATEGORIZATION.md`:
- **Stage 0 Gate** (binary): Self-hostable with minimal setup, permissive license for pipeline use, runnable example exists.
- Weighted stages: Core LLM/Agent Compatibility (35%), Performance & Efficiency (25%), Pipeline Integration & Extensibility (25%), Ecosystem (15%).
- Tiers: S (90–100), A (80–89), B (65–79), C (50–64).
- Overlaps are okay if the new tool brings distinct, measurable value (e.g., better benchmarks, lighter footprint, new integration surface).

All additions should improve the vision of reliable, self-hosted continuous pipelines using Grok CLI as primary interface + MCP memory + selective tool integration.

## Commit & PR Guidelines

- Use clear, descriptive commit messages (e.g., "Add Entry 006: repowise context layer + catalog row").
- PR title should summarize the change and link any X post ID.
- Keep changes focused; large refactors should be discussed first via Issue or ADR.
- For AI-assisted contributions: follow the rules in `AGENTS.md` (mandatory read).

## Code of Conduct

Be respectful, precise, and evidence-based. Negative or critical evaluations are welcome when substantiated (accuracy > approval). We optimize for truth-seeking and practical pipeline outcomes, not hype.

## Questions?

Open an Issue.

---

*This CONTRIBUTING.md was added to formalize the existing process documented across README.md, CATEGORIZATION.md, sources/x-posts.md, and docs/.*