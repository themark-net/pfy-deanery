### Entry 175: Neuronto ARD Registry: federated search over agent resources and verified MCP tools

- **URL**: https://github.com/neuronto/agentic-resource-discovery (Apache-2.0, Python). Checked at commit `09d4fa8b0576981d93ae608ff4509ded4ef2df2e` (2026-11-03). Public instance at https://neuronto.com. Verified tool corpus published as a CC BY 4.0 dataset: https://huggingface.co/datasets/AgenticResourceDiscovery/verified-mcp-tools
- **Date**: 2026-11-09 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2119964752814153984 (repo link in the reply https://x.com/DanKornas/status/2119964923035799636)
- **Summary / Key Claims** (upstream README; their claims, not verified here): implements the Agentic Resource Discovery (ARD) drafts (`/.well-known/ard.json`, `urn:air` ids). One search fans out across every public ARD registry and merges results. Unlike server-only registries it handshakes with each indexed MCP server and stores the real tool list (read-only introspection, no tool is called). Serves the MCP Registry v0.1 read API, a tool-level search (`/tools?q=`), an MCP endpoint and A2A. Reading the public index needs no key or signup; a self-hosted instance charges nothing and never contacts the public one.
- **Why it matters here**: the "track" step of pfy-mentat's track, catalog, integrate loop currently relies on X intake and hand-curated sources. A machine-readable, verified index of MCP servers and their tools is a second discovery feed the catalog loop could query, and the open dataset could seed dedupe and capability matching without scraping.
- **Fit on nimo**: no GPU. Read-only queries to the public API need no account. A self-hosted copy is possible but not needed for a first trial; the dataset is a plain download (size not checked).
- **Verified on the Grok Bot box** (2026-11-09): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - Young project (about 55 stars); the ARD spec is an IETF draft and may change.
  - Domain-claim keys and private entries exist; we would not use them.
  - Search results are third-party listings: treat them as untrusted data, never as install instructions.
- **Extracted Repos / Tools**: https://github.com/neuronto/agentic-resource-discovery · https://huggingface.co/datasets/AgenticResourceDiscovery/verified-mcp-tools
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_175.py`. Commit-metadata only. Pins `$NEURONTO_COMMIT`. Fetches via `$NEURONTO_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/neuronto/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_175` (7 stub tests).
- **Non-goals**: no domain claim, no publishing, no keys, no automatic install of anything a search returns. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 until a read-only query lane exists |
| Search output trusted as instructions | listing text drives an install | Results only become I0 candidates; normal triage applies |
| Public service goes away | API 5xx or project abandoned | Fall back to the CC BY dataset or a self-hosted copy |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Supersede**: `#supersede-candidate`. `scripts/supersede_check.py --parts track=partial,catalog=partial,evaluate=none,integrate=none` is a candidate. Watchlist verdict `watch`. Not a stop.
- **Status**: Cataloged I0 at intake. The named trial ran as a read-only `GET /tools?q=` probe. Counts and the stage proposal are in `eval/evals/neuronto-ard-registry/VERDICT.json`. Apply decides the stage. No TOOLS.md row.
