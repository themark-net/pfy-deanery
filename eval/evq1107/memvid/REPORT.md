# Memvid evq1107

Verdict: STAY I1 reference: single-file .mv2 store, no named job, and it does not score gap H1.

## What it is

Memvid (memvid/memvid) is a Rust library, crate `memvid-core` 2.0.140. One `.mv2` file holds documents, optional embeddings, search indexes, and metadata. License is Apache-2.0: `LICENSE` copyright 2026 Memvid, `Cargo.toml` `license`, GitHub `license.spdx_id` Apache-2.0. The README calls Smart Frames an append-only sequence inspired by video encoding. Changelog 2.0.0 (2026-01-05) says that rewrite removed QR-code video encoding. Entry 044 in `sources/x-posts.md` still says MP4. This lane did not edit that shared file. There is no `sources/entries` file. Status is the card.

Default features are `lex`, `pdf_extract`, and `simd` (Tantivy BM25, no model). `vec` is HNSW at 384 dimensions. The README says to curl a BGE-small ONNX file of about 120 MB into `~/.cache/memvid`. Larger listed models go to about 1.3 GB. `whisper-small-en` is 244 MB. `api_embed` calls OpenAI and wants `OPENAI_API_KEY`. Cargo.toml marks `replay` as time-travel replay with no extra deps. `MV2_SPEC.md` version 2.1 describes a 4 KB header, an embedded WAL, a time index, and no sidecar files. `rust-toolchain.toml` says 1.90.0. `rust-version` is 1.85.0.

## Pin and command

| Item | Value |
| --- | --- |
| Pin | `e6bd9f7b9c38cd8d5370fa0fc936ac1dcd751813` (`main` on 2026-11-07). Subject `Update README.md`. Author date 2026-07-14T20:09:06+05:30. GitHub `pushed_at` 2026-07-14T14:39:07Z. Stars 17382. |
| Release | Latest by publish date is `v2.0.140` (2026-05-27), tag `e18fe55494379e2ab7397ce03655e8abbc5e0c31`. Crate version on the pin is still 2.0.140. Tag `v2.0.157` was published earlier (2026-02-15). |
| Fetch | `~/.cache/pfy/tools/memvid/src`. `git init`, remote `https://github.com/memvid/memvid.git`, `git fetch --depth 1 --filter=blob:none origin e6bd9f7b9c38cd8d5370fa0fc936ac1dcd751813`, `git checkout --detach FETCH_HEAD`. Wall time 1 s. `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, and `TMPDIR` were under that cache. `GIT_CONFIG_GLOBAL` and `GIT_CONFIG_SYSTEM` were `/dev/null`. |
| Bytes | Worktree 217 files, 9555399 bytes. `.git` 3461726 bytes. Total 13017125. No `.onnx`, `.gguf`, or `.mp4` in the tree. |
| Ran | no cargo, no npm, no pip, no model curl, no upstream script |

## Ideas, and the pfy file each would touch

| Idea | pfy file | What we already have |
| --- | --- | --- |
| One file, WAL inside, no sidecar. | `docs/ops/memory-assist-patterns.md` | That note already names Memvid as a pattern and says do not embed it. |
| A time index can name an older frame. | `docs/ops/cage-session-resumption-design.md` | Git versions the worktree. Hermes observations stay markdown in `bootstrap/grok-cli/skills/hermes-feedback/SKILL.md`. |
| Bind an index to one embedding model and reject a mismatch. | `docs/ops/local-cloud-split.md` | Workers use a local base URL. OpenContext's card records keyword search exiting 1 with no key. |
| Leave QR-in-MP4 behind. The 2.0 changelog already did. | `docs/evaluation/codebase-memory-vs-graphify.md` | One primary code memory. A second store stays out. |

## Catalog comparison

Gap H1 in `docs/eval/TOOLSET-RANKING.md` (2026-11-07) is a repeatable with/without score. The pick is skill-up (I3). Memvid is not in entries 137 to 167. The 2026-10-06 section lists Memvid under skip or hold. Same job: a local memory or RAG store. A word scan of uses, features, and tags (memory, rag, context, versioning, wiki, embedding, recall) matched 24 cards. The table is the comparison set. cass-memory is in it even though that scan missed the card. This lane builds no pipeline, CI, or gate.

| Tool | Stage | What it covers | How Memvid compares |
| --- | --- | --- | --- |
| skill-up | I3 | With-skill vs no-skill grade. | A store does not close H1. |
| codebase-memory-mcp | I2 | Primary code-graph MCP. repowise (I2) packs context beside it. | Chosen code memory. This would be a second store. |
| LEANN | I1 | Compressed HNSW plus BM25. | Already the local RAG candidate. |
| opencode-mem | I2 | Turso store for the OpenCode worker. | Already a worker memory. |
| MemPalace | I1 | Verbatim memory. Work tree 68560448 bytes. | Same job class. Already probed. |
| OpenContext, ai-memory, Kenfold | I1 | Notes, a wiki, shared MCP memory. | Same recall job. Already probed. |
| cass-memory, RoBrain, Graphify | I0 | Playbook, decisions, code graph. | Overlap. None is this file format. |
| Chroma (or LanceDB) | I0 | Vector database, reference only. | Another store. Not adopted. |
| Hermes feedback loops | I1 | Pattern already a skill. | Process memory is markdown. |

Beats what we have: no.

## Gates

Value (3 of 4 for I3): gap fill no. Operator leverage no. The pattern note already exists, and no operator job is named. Evidence no. This lane read docs only. Blast radius no on the README vector path: `vec` and `whisper` download models, and `api_embed` wants an OpenAI key. Default features do not download weights, and the license is Apache-2.0, so a lex-only reading is 1 of 4. The documented memory path scores 0 of 4.

Modularity (all 4 for I2): local code was not required. One crate is a bounded surface. Isolatable and reversible pass. 3 of 4. Potential is low. The worktree is 9555399 bytes, under 50 MB, and that does not open I2. No `self_pipeline`. Tags are memory, versioning, local-first, and rag. No CI, test, or review role. No gate wiring.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Stale MP4 claim | A later lane looks for a video encoder the 2.0 changelog removed | Stay I1. The pin is the `.mv2` tree. |
| Model download | `vec` writes ONNX under `~/.cache/memvid`, or whisper pulls 244 MB | Do not build those features. |
| OpenAI key | `api_embed` reads `OPENAI_API_KEY` | Do not enable it. No key on this lane. |
| Second store | Catalog truth splits away from codebase-memory-mcp | The decision note stays. Stay I1. |
| Home write | The README mkdir targets `~/.cache/memvid` | This lane set HOME under `~/.cache/pfy/tools/memvid` and did not curl models. |

## Next gate

Stay I1 reference. Re-open only if a later ticket names a retrieval job that codebase-memory-mcp, LEANN, opencode-mem, and git do not cover, and that ticket grills a copy first. Not a Feature GO.

## Pipeline questions

This lane does not put Memvid on a pipeline. The scheduler started the read. It writes this directory and `data/stages/memvid.json`. No model and no account.

1. Trigger, if adopted later: a person runs `cargo add memvid-core` or `npm install -g memvid-cli`. Not this scheduler.
2. It would read documents and write a `.mv2` file. `vec` would read an ONNX file or call OpenAI. This lane only read git docs.
3. Next: nothing in `./pfy`. Search stays on codebase-memory-mcp.
4. A human re-enters before any install, any model download, any API key, or any I2 claim.
5. One worktree per slug keeps this card private. A second read must not edit the same card.
