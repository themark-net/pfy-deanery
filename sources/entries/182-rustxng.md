### Entry 182: RustXNG: self-hosted metasearch and page-text grounding for agents (JSON API and MCP)

- **URL**: https://github.com/sahenjp/RustXNG (AGPL-3.0, Rust). Checked at commit `97d330a76597dbabdd3426679c061cd560cd2e1b` (release 0.31.2, 2026-11-11).
- **Date**: 2026-11-11 (daily X intake)
- **Source / Poster**: watch-list post by @DanKornas, https://x.com/DanKornas/status/2120372448046588052 (repo link in the reply https://x.com/DanKornas/status/2120372729408856513)
- **Summary / Key Claims** (upstream README; their claims, not verified here): a Rust rewrite of SearXNG that merges results from external providers and returns title, URL and snippet as JSON, CSV or RSS. `rustxng mcp` exposes two read-only tools, `search` and `read_page`, with character and token budgets. Page fetches check robots.txt and refuse non-public addresses. A `standard` profile uses 34 keyless documented endpoints; a `clean` profile searches only local indexes (own crawl via `rustxng-index`, Wikipedia dumps); `full` adds HTML scrapers and billed Exa (off without a key).
- **Why it matters here**: the catalog has no local web-search layer. Lanes that need a fact from the web either skip it or depend on a hosted model's search. A loopback search plus `read_page` with a token budget would let local-model lanes (qwen3.6 35B on nimo) ground claims during catalog fit checks without a paid key.
- **Fit on nimo**: no GPU. A release binary (with SHA-256 sidecar) or `cargo install --locked` under `~/DEVELOP` with a throwaway HOME. Bind to 127.0.0.1 only. `standard` still sends queries to outside providers; `clean` is fully offline but needs an index.
- **Verified on the Grok Bot box** (2026-11-11): commit pin matched via GitHub API; smoke exits 2 (not installed). 7 stub tests pass.
- **Findings**:
  - 956 stars, about a month old, frequent releases (release-please).
  - AGPL-3.0: fine for local use; do not vendor its code into this repo.
  - Upstream's own numbers: Standard Hit@5 67-69/100 on their docs question set after provider permission changes (down from 84/100).
- **Extracted Repos / Tools**: https://github.com/sahenjp/RustXNG
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_182.py`. Commit-metadata only. Pins `$RUSTXNG_COMMIT`. Fetches via `$RUSTXNG_FETCH_BIN` or stdlib GitHub commits API. Does not install. Receipt: `pipelines/smoke/rustxng/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_182` (7 stub tests).
- **Non-goals**: no `full` profile (terms and billed Exa), no public bind, no vendored AGPL code, no install outside `~/DEVELOP`. Catalog HOLD 70-75 untouched. No Feature GO.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Smoke treated as a pass | Commit match becomes exit 0 | Keep exit 2 while it is not installed |
| Service exposed | Bound to 0.0.0.0 | Loopback bind only |
| Provider terms or billing | `full` profile enabled | Stay on `standard` or `clean`; no Exa key |
| Web text injected into prompts | `read_page` output trusted | Treat returned text as untrusted data |
| Pin drift | `main` moves | Smoke checks this SHA |

- **Status**: Cataloged I0. Next step, if any: eval-auto trial of `rustxng mcp --profile standard` as a grounding tool for one catalog fit-check lane, measuring hit rate on known tool facts, latency and token cost against no search.
