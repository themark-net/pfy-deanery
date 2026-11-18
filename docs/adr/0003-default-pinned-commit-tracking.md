# ADR-0003: Default tool tracking is pinned commit (not subtree)

- **Date:** 2026-07-11
- **Status:** Accepted

## Context

Embedding every interesting tool would bloat the tracking repo and fight “lean catalog” goals. Operators still need reproducibility for pipelines.

## Decision

**Default:** record tools with `pinned_commit` (or tag) in `data/tools.json` / TOOLS.md; pipelines use shallow clone at that pin.

**Rare exception:** `git subtree` (or submodule) only when all criteria in `SUBTREES.md` are met (small, high-tier, actively customized, offline/repro benefit).

Aggregates use handling tiers A/B/C in `sources/aggregates.md` rather than always embedding list repos.

## Rationale

- Matches SUBTREES.md core principle and keeps history small.
- Pins remain scriptable for CI without vendoring multi-GB runtimes.

Rejected alternatives:

1. **Subtree everything useful** - Unbounded growth; poor default for Ollama/llama.cpp-class projects.
2. **Floating `main` only (no pins)** - Non-reproducible pipelines; silent breakage.
3. **Submodules for all tools** - Better than full history copy, but still noisy for dozens of entries operators never edit in-tree.

## Consequences

- New tool PRs must include pin fields when integration is claimed.
- Subtree requests need explicit criteria checklist in the PR.

## References

- `SUBTREES.md`, `sources/aggregates.md`, `data/tools.json` schema
