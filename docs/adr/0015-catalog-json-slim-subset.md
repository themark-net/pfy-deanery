# ADR-0015: Catalog JSON is a slim machine subset

**Status:** Accepted  
**Date:** 2026-08-24  
**Deciders:** PM / DevBot (owner completeness audit)  
**Issue:** [#83](https://github.com/themark-net/pfy-deanery/issues/83)

## Context

DESIGN G1 used to read as if every scored tool lived in both `TOOLS.md` and `data/tools.json`. On main, `TOOLS.md` / `sources/entries` still look like ~79 rows while `data/tools.json` v0.4.13 has **3** tools (Grok CLI bootstrap, kanbots, multi-agent-generator) and empty `aggregates` / `x_posts` arrays.

The product surface is `./pfy` onboard / stage / ship. The catalog is how we choose pieces. Restoring JSON to match all ~79 markdown rows is a catalog rewrite and is out of scope here.

## Decision

- **`TOOLS.md` (+ `sources/`)** is the scored catalog.
- **`data/tools.json`** is a **slim machine subset** for eval/dashboard consumers that already speak JSON. It is **not** required to list every TOOLS.md row.
- G1 does **not** mean triple-write of all ~79 rows into JSON.
- `scripts/catalog_check.py` (and `./pfy eval` catalog checks) must enforce subset honesty: every JSON tool name appears in `TOOLS.md`. They must **not** fail because JSON has fewer rows than markdown.

## Rejected alternatives

| Option | Why not |
|--------|--------|
| Restore JSON to match all ~79 TOOLS.md rows | Catalog rewrite; blocks G8; owner said no TOOLS.md rewrite-from-scratch. |
| Delete tools.json | Breaks existing eval/dashboard readers. |
| Silent dual-SoT | Agents keep treating count mismatch as a bug. |
