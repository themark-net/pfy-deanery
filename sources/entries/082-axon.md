### Entry 082: Axon — codebase knowledge graph + MCP tools

- **URL**: https://github.com/harshkedia177/axon
- **Date**: 2026-09-13 (HOLD research; implement #215 — do not merge catalog PR #75)
- **Poster / source**: Catalog HOLD PR [#75](https://github.com/themark-net/pfy-mentat/pull/75) (scores-only; **not merged**) · upstream [harshkedia177/axon](https://github.com/harshkedia177/axon)
- **Summary / Key Claims**: Graph-powered code intelligence. Indexes a repo into a structural knowledge graph (KuzuDB + local embeddings), CLI (`axon analyze` / `axon query` / `axon context` / `axon impact`) plus MCP (`axon serve --watch`) so agents get callers, impact, dead code, and flows without stuffing the context window. Fully local; no API keys required.
- **Extracted Repos / Tools**: https://github.com/harshkedia177/axon (MIT). PyPI `axoniq` 1.0.1. Pin note: `main` @ `2b386fb38a468201ab2ec825ddea5ebf4c33f513` (2026-08-03). Python ≥3.11. Install: `pip install axoniq`. Hello-world: `axon analyze . --no-embeddings` then `axon serve --watch` (MCP). Optional UI `axon ui` stays **out of pfy chrome**.
- **TOOLS.md Link**: **Catalog HOLD this round** — Stage-0 receipt + score note only. No TOOLS.md / `data/tools.json` triple-write. Do not merge or cherry-pick PR #75. Do not touch catalog PRs 70–75.
- **Notes (Stage-0 gate):**
  - **License:** PASS — MIT (commercial/research OK; no copyleft embed issue).
  - **Self-host / quickstart:** PASS — `pip install axoniq` (<5 min when Python ≥3.11 is present). Local KuzuDB + optional `--no-embeddings` (LIVE_HARD_OFF: skip cloud/paid embeddings).
  - **Hello-world:** PASS — documented CLI: `axon analyze .` (index) → `axon query` / `axon context` (search) → `axon serve --watch` (MCP reuse). `axon ui` is optional developer chrome, not a pfy Attach control.
  - **Fail closed:** Stage-0 PASSES on those three. Nimo install/run is DoD (`./pfy code-graph`). Missing axon is honest FAIL + `pip install axoniq` **or** fallback to already-present `codebase-memory-mcp` painted as **not Axon**. Never claim Axon when only the MCP stub is live.
  - **Non-goals (#215):** do not merge catalog PR #75; do not auto-install Axon into the repo; do not put Axon UI into pfy chrome; Ix (#198) stays parked; do not reopen #76; do not start #214.
- **Score note (initial, not cataloged):** Context & Memory / Codebase Knowledge Graph & MCP. S1 ~88 (MCP tools `axon_query` / `axon_context` / `axon_impact` / `axon_dead_code` into existing agents). S2 N/A (no inference). S3 ~85 (`pip` CLI + stdio MCP + `.axon/` local store). S4 ~80 (MIT, PyPI `axoniq`, last push 2026-08-03). Overall ~A pending catalog un-HOLD. I3-shaped operator path via `./pfy code-graph` + Attach mode `code-graph`; catalog row deferred.
- **Status**: STAY I1 after the 2026-11-07 nimo probe. Pin git 2b386fb38a468201ab2ec825ddea5ebf4c33f513 (2026-08-03), PyPI axoniq 1.0.1 wheel sha256 4632b2f6d11a7c365ade3a307d3d49b7f4e0010ef338ee2531a12caf57260a60. Bare impact and file-qualified callers both agree with test_select on 4/10. codebase-memory and tree-sitter-analyzer agree on 5/10. Chiasmus agrees on 3/10. Venv 218 MB. Not a gate. No Feature GO. Report `ops:eval/evq1107/axon/REPORT.md`.
