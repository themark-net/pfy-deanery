# Chroma (or LanceDB) evq1107

Verdict: STAY I0 reference: code memory is already chosen, and this pair does not score gap H1.

## What it is

Chroma (chroma-core/chroma) is an Apache-2.0 search database. The README calls it open-source data infrastructure for AI. At tag 1.5.9 the Python package is `chromadb` (`requires-python >= 3.9`). `chromadb.Client()` is in-memory. `PersistentClient(path=...)` stores files on disk and defaults the path to `.chroma`. `chroma run --path` plus `HttpClient` is client-server. `CloudClient` talks to Chroma Cloud (`api.trychroma.com`) with an API key. The default embedding function is all-MiniLM-L6-v2 and the docs say it may download model files. `pyproject.toml` depends on onnxruntime, grpcio, and kubernetes. Product telemetry stopped at 1.5.4. The OSS page says engineering effort is on distributed Chroma and the cloud, and local single-node storage is a different subsystem. The Rust client README lists dense search, sparse search (BM25 or SPLADE), full-text, metadata filters, and a weighted hybrid `search` endpoint.

LanceDB (lancedb/lancedb) is the other name on this card. Apache-2.0. Python package `lancedb`, `requires-python >= 3.10`, Lance crates `=14.0.2`. The README describes a local columnar store with vector search, full-text search, SQL, and automatic table versions, plus a cloud product.

No `sources/entries` file exists for this slug, so there is no Status line to update. `TOOLS.md` already has the B-tier row (overall 78). This lane did not edit `TOOLS.md` or `data/tools.json`.

## Pin and command

| Item | Value |
| --- | --- |
| Chroma pin | `11f3c7435e71024aa0a2b53710a28d3289d922d1` |
| Chroma tag | `1.5.9` and `cli-1.4.4` are that commit. 2026-05-04 16:34:47 -0700. Subject: [RELEASE] CLI 1.4.4 Python 1.5.9 JS 3.4.5 (#7018). `main` `1a3ac2c7c623adbd03ed2508dc27b98cdf26016d` was not checked out. |
| LanceDB pin | `3936a8b3bcce8f8e073f3ec6a47e4ca4d3381b92`. Annotated tag `v0.41.0` is object `9a5af75d60fc542f4e4c87e0ed23374ff8d7eccb`. 2026-10-29 08:07:25 +0000. Subject: Bump version: 0.41.0-beta.17 -> 0.41.0. |
| Fetch | Cache `~/.cache/pfy/tools/chroma-or-lancedb/`. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` were under that cache. Chroma: `git clone --filter=blob:none --depth 1 --branch 1.5.9 --sparse`. Cone sparse-checkout of `README.md` failed. Docs were read with `git cat-file -p`. LanceDB: `git clone --filter=blob:none --depth 1 --branch v0.41.0`. Wall time 4s. |
| Bytes | Chroma worktree 338334. Directory 19563266 after a full `git ls-tree -r -l` was started and stopped. Full blob sum not recorded. LanceDB: 1224 blobs, 44268819 bytes. Directory 71438644 including `.git`. |
| Ran | no pip, no `chroma`, no curl installer, no upstream script, no model |

## Ideas, and the pfy file each would touch

| Idea | pfy file | What we already have |
| --- | --- | --- |
| Filter memory by type (semantic, procedural, episodic) before similarity. Their guide puts that in one collection. | `bootstrap/grok-cli/skills/hermes-feedback/SKILL.md` | Observations stay markdown. A collection is the non-goal. |
| The caller may pass vectors. A local default must not require a hosted key. | `docs/ops/local-cloud-split.md` | Workers use a local base URL. Chroma's default still downloads MiniLM. OpenContext's card records keyword mode exiting 1 with no key. |
| The index is disposable. `reset()` wipes the path. Source text lives outside the database. | `docs/evaluation/codebase-memory-vs-graphify.md` | One primary code memory. That note says not to run a second code-memory runtime. |
| LanceDB versions a table without extra infrastructure. | `docs/ops/cage-session-resumption-design.md` | Git already versions the worktree. A second versioned table stays out. |

## Catalog comparison

Gap H1 in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is a repeatable with/without score. The pick there is skill-up (I3). This card is not in entries 137 to 167. Same job: a vector or embedding store for memory. This lane builds no pipeline, CI, or gate.

| Tool | Stage | What it covers | How this card compares |
| --- | --- | --- | --- |
| codebase-memory-mcp | I2 | Primary code-graph MCP | The chosen code memory. A vector DB would be a second store. |
| LEANN | I1 | Compressed HNSW plus BM25 | Already the local RAG candidate. Its card records an HNSW graph smaller than the float32 matrix. |
| opencode-mem | I2 | Turso vector store for the OpenCode worker | Already a vector store. Its card records 8 of 8 stored salts. |
| MemPalace | I1 | Verbatim memory. Default backend is Chroma 1.5.9 | Uses this library. This lane does not put that store in the product. |
| OpenContext | I1 | LanceDB index that asks for an embedding key | Its card records keyword mode exiting 1 with no key. |
| OpenLore | I1 | Optional LanceDB embeddings | Its report says the probe stayed on the keyword index. |
| Kenfold, RoBrain | I1, I0 | Postgres and pgvector | Another vector stack. Not our code memory. |
| Graphify, Memvid, cass-memory, ai-memory | I0, I1, I0, I1 | Graph, video memory, playbook, git wiki | Memory overlap. None of them is this database. |

Beats what we have: no.

## Gates

Value (3 of 4 for I3): gap fill no (H1 is a score, and skill-up grades it). Operator leverage no (a second store, plus a model download or a cloud key). Evidence no (docs only; `chroma login` and CloudClient were not run). Blast radius no: the documented getting-started path is Chroma Cloud with an API key, and `chroma run` is a second server. License is Apache-2.0, and the default model is not a multi-GB weight. Score 0 of 4.

Modularity (all 4 for I2): local code was not required. The surface is a monorepo (Python, JS, a Rust workspace with wal3, S3, and Spanner members, plus a top-level k8s directory). Isolatable and reversible pass. 2 of 4. Potential is low, not ambiguous, so the LanceDB worktree (44268819 bytes) does not open I2. The Chroma tree was not copied. No `self_pipeline`. Uses and features name no CI, test, or review role. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Default embedder | First `add` downloads MiniLM into a cache | Do not install. MemPalace already recorded that cache. |
| Cloud login | `chroma login` opens a browser and writes a profile and `CHROMA_API_KEY` | Do not run the CLI. No key on this lane. |
| curl installer | The docs pipe `install.sh` to bash | This lane did not fetch that script. |
| `reset()` | A trial points PersistentClient at a real tree and wipes `.chroma` | Stay I0. A later trial uses a cache path. |
| Second store | Catalog truth splits across codebase-memory and Chroma | The decision note stays. Stay I0. |

## Next gate

Stay I0 reference. Re-open only if a later ticket names a retrieval job that codebase-memory-mcp, LEANN, and opencode-mem do not cover, and that ticket grills the copy first. Not a Feature GO.

## Pipeline questions

This lane does not put Chroma or LanceDB on a pipeline. The scheduler started the read. It writes this directory and the card. No model and no account.

1. Trigger, if adopted later: a person runs `pip install chromadb` or points a client at Chroma Cloud. Not this scheduler.
2. It would read documents and write a `.chroma` directory, or call `api.trychroma.com` with an API key. This lane only read git docs.
3. Next: nothing in `./pfy`. Search stays on codebase-memory-mcp.
4. A human re-enters before any install, any cloud login, or any I1 claim.
5. One worktree per slug keeps this card private. A second read must not edit the same card.
