### Entry 120: Kenfold — self-hosted shared memory server for agent CLIs over MCP (Postgres + pgvector, provenance per agent)

- **URL**: https://github.com/jeonjw85/kenfold (MIT, Go, 70 stars at this read; release v0.1.1, 2026-10-13)
- **Date**: 2026-10-15 (daily X intake)
- **Source / Poster**: @DanKornas, https://x.com/DanKornas/status/2110834096788189244
- **Summary / Key Claims** (upstream README and `compose.yaml` at v0.1.1): one memory store shared by Claude Code, Codex, OpenCode and ChatGPT over MCP (HTTP at `/mcp`, or stdio straight to the database). Every memory records which agent wrote it (from its own API key), when, and how far to trust it. Recall fuses full-text and vector search, follows links between memories, can rerank with a local cross-encoder, and prefers recent session summaries and memories whose code references still exist. Writes containing credentials are rejected (`kenfold scan --redact` cleans old ones). Session hooks can extract facts with a local model. Export/import as JSONL, a review dashboard, and OAuth for remote clients. `make up` runs Postgres 18 + pgvector and Kenfold on `127.0.0.1:7077`; `make up-embed` adds Ollama with `bge-m3` and a llama.cpp reranker. Status per upstream: features implemented, public benchmark validation incomplete (partial LoCoMo only).
- **Why it matters here**: the org's agents (Grok Bot teammates, Grok Build, Cursor, OpenCode on nimo) each keep their own memory, and handoffs live in repo docs. Kenfold is a local option for one shared, attributed memory that several CLIs can read, with secret rejection built in, which matches the standing no-secrets rule. Compare with opencode-mem (toolsets drop-in), the notes in `docs/ops/memory-assist-patterns.md`, and codebase-memory-mcp (code graph, a different job).
- **Fit on nimo**: Only with Docker and Compose, which are unconfirmed on nimo; installing Docker is a system change that needs the operator. Embeddings can point at nimo's existing Ollama (`KENFOLD_EMBED_URL`, any 1024-dim model such as `bge-m3`) instead of the bundled container. The compose file hardcodes `127.0.0.1:7077`.
- **Verified on the Grok Bot box**: nothing ran; there is no Docker on the box. Read the README and `compose.yaml` at v0.1.1 only. The smoke's not-staged and no-docker paths exit 2 as intended.
- **Finding**: the Kenfold image is built from source (`kenfold:dev`), so the pin is the git tag; Postgres is pinned by tag (`pgvector/pgvector:0.8.6-pg18-trixie`), not digest. A release build checks GitHub for updates unless `KENFOLD_UPDATE_CHECK=false` (the smoke sets it). `make key` prints an API key once to stdout, so keys must go straight into a secret store, never a log.
- **Extracted Repos / Tools**: https://github.com/jeonjw85/kenfold · https://github.com/jeonjw85/kenfold/blob/v0.1.1/compose.yaml · https://github.com/jeonjw85/kenfold/blob/main/docs/deploy.md
- **TOOLS.md Link**: None. No TOOLS.md row and no `data/tools.json` row.
- **Smoke**: `python3 examples/x-intake-local/smoke_119_121.py --entry kenfold`. Needs `$KENFOLD_DIR` or `tmp/kenfold` at tag v0.1.1 (`$KENFOLD_REF` overrides) and docker with compose; brings up only postgres + kenfold, probes `/healthz`, `/readyz`, a keyless `/mcp` (must be 401) and `kenfold healthcheck`, then `compose down -v`. Mints no key and writes no memory. Receipt: `pipelines/smoke/kenfold/latest.json`. **Compose happy path has still not run.** The 2026-11-07 lane used stdio and rootless podman; see Status.
- **Status**: evq1107 2026-11-07 STAY I1. Stdio recall 8/8 copied tokens across two agents (agreement 8/8), 0/8 facts already in this repo, 0 graded with/without cases. A secret fixture was rejected and not echoed. No API key. Report: ops:eval/evq1107/kenfold/REPORT.md.
- **Non-goals**: No agent wired to Kenfold, no API key created, no remote/OAuth exposure.
- **How this fails / how we recover**:

| Risk | How it fails | Recovery |
|------|----------------|----------|
| No Docker on nimo | Smoke exits 2 forever | Leave catalog-only; ask the operator before installing Docker |
| A printed API key leaks into a log | Key visible in chat or CI | Create keys only straight into a secret store; rotate on any exposure |
| Memory exposed beyond loopback | OAuth or a tunnel opened by mistake | Keep the default 127.0.0.1 bind; follow upstream's deploy checklist before any exposure |
| Smoke happy path untested | First nimo run fails on a smoke bug | Treat the first nimo run as the real test; fix the smoke in a follow-up |
