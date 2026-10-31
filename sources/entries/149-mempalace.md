### Entry 149: MemPalace: local-first verbatim agent memory with scoped search and an MCP server

- **URL**: https://github.com/MemPalace/mempalace (MIT, Python 3.10+). Checked at `HEAD` `84582fb055a6429261f9c779da86c0561ec80adc` (2026-10-25T04:41:28Z), `mempalace --version` = `MemPalace 3.12.0`.
- **Date**: 2026-10-29 PT (daily X intake, window 2026-10-28 17:42 to 2026-10-29 17:35 PT, i.e. 2026-10-29T00:42Z to 2026-10-30T00:35Z)
- **Source / Poster**: Mark's bookmark of @thisguyknowsai, https://x.com/thisguyknowsai/status/2115754546018566471 (repo found by name; the post had no link)
- **Summary / Key Claims** (upstream README; their claims except where marked verified): stores project files and agent transcripts verbatim (no summarizing) in a ChromaDB-backed index organized as wings (people/projects), rooms (topics) and drawers (original chunks), so search can be scoped to a wing or room by metadata filter. Hybrid ranking (cosine plus BM25). Claims 96.6% R@5 raw on LongMemEval with zero API calls. CLI (`init`, `mine`, `search`, `wake-up` for a ~600-900 token session primer, `audit`, `kg`, `tunnels`), a 47-tool MCP server (`mempalace-mcp`), Claude Code session mining (`mine --mode convos`), optional local-LLM classification through Ollama, pluggable backends (Chroma, Milvus). The post's "49K stars" figure is unverified.
- **Why it matters here**: pfy-mentat already catalogs several memory layers (108 cass-memory, 132 ai-memory, opencode-mem). MemPalace is the first with a published LongMemEval number, verbatim storage (nothing lost to summarization) and scope filters that map onto pfy-mentat's per-repo, per-run structure. It is a direct candidate for the memory slot in the Grok Build replacement, and its `wake-up` primer is the same idea as our handoff docs, done automatically.
- **Fit on nimo**: Yes, expected: pure Python plus ChromaDB, CPU embeddings (all-MiniLM-L6-v2 ONNX by default, ~80 MB, downloaded once on first use), no GPU or NVIDIA dependency. Not yet staged on nimo; the smoke exits 2 there until it is.
- **Verified on the Grok Bot box** (Python 3.13 venv under `/tmp`, install from the pinned commit, temp HOME): `init --yes` + `mine` on a two-note fixture project filed 2 drawers in about 3 s; `search "why did we switch auth provider"` ranked the auth note first (observed scores on that run: cosine 0.54, BM25 1.60; not a benchmark) and `search "which test runner does CI use"` ranked the CI note first. With the model cache warm, the whole flow also runs under bubblewrap with no network. Smoke PASS.
- **Findings**:
  - `init` writes `mempalace.yaml` into the project directory it scans, so point it at a copy or a scratch dir, never Mark's main checkout.
  - First use downloads the ONNX embedder into `$HOME/.cache/chroma`; with a warm cache it runs fully offline. Seen on the author's (Grok Bot) box only, not yet reproduced on nimo: without `/proc` and a writable `/dev/shm` inside bwrap, ChromaDB failed with `disk I/O error`. The smoke mounts both.
  - The `--llm` path supports Ollama and OpenAI-compatible endpoints (so a local model on nimo fits); the Anthropic option and the opt-in remote `serve` mode are out of scope.
  - LongMemEval number and star count not reproduced here.
- **Extracted Repos / Tools**: https://github.com/MemPalace/mempalace · `website/guide/mcp-integration.md` (MCP tool list and the "search before answering" memory protocol) · `benchmarks/` upstream
- **TOOLS.md Link**: None yet. I0 awareness. No TOOLS.md row, no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_149.py`. Reads `$MEMPALACE_BIN`, else `~/DEVELOP/pfy-mentat/tmp/mempalace/.venv/bin/mempalace`, else PATH; version pinned to an exact match (`$MEMPALACE_VERSION`, default 3.12.0); needs the embedder cached under `$MEMPALACE_HOME` (default `~/DEVELOP/pfy-mentat/tmp/mempalace/home`), else exit 2; needs a working bwrap (no network, read-only root), else exit 2, never an unsandboxed run (same rule as Entry 148); never downloads. Receipt: `pipelines/smoke/mempalace/latest.json`. Tests: `python3 -m unittest tests.test_x_intake_smoke_149` (18 stub tests; the ones that need a real sandbox skip when bwrap is not usable).
- **Non-goals**: No MCP registration, no hooks into Grok Build or Hermes, no mining of real repos or transcripts, no LLM mode, no `serve`, no daemon.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| Wrong recall | Search ranks the wrong drawer and the agent acts on stale context | Smoke checks ranking on fixtures; an eval-auto trial measures recall on our own handoff docs before any wiring |
| Writes outside scratch | `init` drops `mempalace.yaml` into the scanned dir; first run fills `~/.cache/chroma` | Scan only copies; give it a HOME under `~/DEVELOP/pfy-mentat/tmp/mempalace/home` |
| Palace corruption | ChromaDB version bump or sandbox I/O error breaks the index | Palace is rebuildable from source files (`mempalace repair`); pin the version |
| Network | First-run model download, opt-in remote serve | Warm the cache once, then run offline under bwrap |

- **Status**: Cataloged I0. Smoke PASS on the Grok Bot box; not yet staged on nimo. **Eval-auto trial candidate** after the MVP: mine pfy-mentat's `docs/` handoffs and Build transcripts into a palace and compare recall against cass-memory (108) and ai-memory (132) on the same questions.
