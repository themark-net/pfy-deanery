# LEANN evq1107 (2026-11-07)

## Catalog tools on the same job

The job is compressed local RAG for a catalog question, with no vector-database server. The lane gap is B (`./pfy build`, lanes, review). This probe measures storage and retrieval. It does not wire a build lane.

`docs/eval/TOOLSET-RANKING.md` section 2026-11-07 (entries 137 to 167) does not list LEANN. The 2026-10-06 ranking, row 10, lists LEANN as compressed local RAG for catalog-ask. `eval/ev1107/` and `eval/catchup-1107/` have no LEANN trial. `TOOLS.md` has a LEANN row. `data/tools.json` does not. This lane stays at I1, so it does not add that row.

The probe scanned `uses`, `features`, `tags`, and `catalog_tags` for rag, compression, embedding, embeddings, vector, memory, code-memory, and code memory. 16 other cards matched.

| Tool | Stage | What it already covers | How LEANN compares |
|------|-------|------------------------|--------------------|
| codebase-memory-mcp | I2 | Primary code graph. | The comparison target. Shadow search on these 10 questions returned the expected file in 0/10. LEANN's slice already contained every expected file. LEANN does not replace the graph. |
| Chroma or LanceDB | I0 | Vector store. Code memory is already chosen. | Same family of job. LEANN is a file index. The CPU install still pulls torch. |
| Graphify | I0 | Reference tree-sitter graph. | A graph, not a passage index. |
| Memvid | I1 | Video-backed memory. | Different store. The memory-assist note keeps both as later spikes. |
| opencode-mem | I1 | Vector memory for the OpenCode worker. | Different surface. |
| MemPalace | I0 | Verbatim local memory with scoped search. | A memory store. This probe is one HNSW file plus a BM25 sqlite. |
| repowise | I2 | Context packing. Overlaps codebase-memory. | Packs a repo. It does not claim a smaller-than-raw embedding index. |
| LangGraph / LangChain | I1 | Graph orchestration. | The rag tag matched. Different job. |
| Cloudflare security audit skill | I0 | Schema check for findings. | The rag tag matched. Different job. |
| Agent Beacon | I0 | Session copy and a lesson store. | The word memory matched. |
| Auto-Company | I1 | Company-daemon patterns. | The word memory matched. |
| Grok CLI bootstrap | I3 | Operator env and skills. | The words memory and code-memory matched. |
| Hermes Agent (feedback loops) | I1 | Feedback-loop skill. | The word memory matched. |
| imcodes | I0 | Supervised review and final-answer memory. | Reference. Not an install. |
| MUE-X | I1 | Self-rewriting agent. | The word memory matched. Unsafe as a runtime. |
| RoBrain | I0 | Decision memory with vetoes. | Different memory. |

## Pins

Entry 052 in `sources/x-posts.md` has no commit and no checksum. There is no `sources/entries/052-leann.md`, so this lane does not edit the shared post log. The pin lives on `data/stages/leann.json`.

- GitHub tag `v0.3.9` is commit `07796bd7e40f2d5f3a4be9e45adf1f62a68481fd` (2026-10-28). PyPI release 0.3.9.
- Wheel `leann-0.3.9-py3-none-any.whl`, 2049 bytes, sha256 `3784706ec4a0a2b5da299437a01627c77ca3911c116828e2b2d1287957fe4615`.
- Sdist `leann-0.3.9.tar.gz`, 2285 bytes, sha256 `f0482785ef6edd75a93ab56297499a0a52a0867e665bf6146e40788cca4be769`.
- License MIT. Requires Python >= 3.10. Classifiers stop at 3.13.
- Installed into `~/.cache/pfy/tools/leann/venv` with the existing uv CPython 3.12.12. No new interpreter was downloaded. System Python 3.14 was not used.
- Versions that ran the probe: leann 0.3.9, leann-core 0.3.9, leann-backend-hnsw 0.3.9, leann-backend-diskann 0.3.9 (meta dependency, unused), torch 2.2.2+cpu, sentence-transformers 3.4.1, numpy 1.26.4, scipy 1.17.1.
- Cache sizes after the scored run: venv 1632621178 bytes, uv cache 1882519621 bytes, sentence-transformers home 91579054 bytes (MiniLM weights), probe index dir 978704 bytes.
- `site-packages` has no nvidia directory.

The published `[cpu]` extra depends on `torch==2.2.2`. On PyPI that resolves to the CUDA wheel. The CPU wheel is `torch==2.2.2+cpu`, and the local version does not satisfy `torch==2.2.2`. The extra was not installed. A constraint file pinned `torch==2.2.2+cpu`.

## Commands

Homes for the install and the probe were directories under `~/.cache/pfy/tools/leann/`: `HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `TMPDIR`, `HF_HOME`, `HUGGINGFACE_HUB_CACHE`, `SENTENCE_TRANSFORMERS_HOME`, `TORCH_HOME`, `UV_CACHE_DIR`. `CUDA_VISIBLE_DEVICES` was empty. `LEANN_EMBEDDING_DEVICE=cpu`. `HF_HUB_DISABLE_TELEMETRY=1`. The probe did not take `~/.cache/pfy/locks/local-model.lock`.

```bash
printf '%s\n' 'torch==2.2.2+cpu' > "$ROOT/constraints.txt"
uv pip install --python "$ROOT/venv/bin/python" \
  --constraint "$ROOT/constraints.txt" \
  --index https://download.pytorch.org/whl/cpu \
  --index https://pypi.org/simple \
  --index-strategy unsafe-best-match \
  'torch==2.2.2+cpu' 'leann==0.3.9' 'leann-backend-hnsw==0.3.9'
uv pip install --python "$ROOT/venv/bin/python" 'sentence-transformers>=3.0,<4'
uv pip install --python "$ROOT/venv/bin/python" 'numpy>=1.26.4,<2'
```

`first-index` failed: the CPU index only offers `requests` 2.28.1, and leann-core needs `requests>=2.31.0`. An earlier `leann[cpu]` resolve started CUDA wheels and was killed. Those wheels were not kept.

The scored command, after the model was already in the sentence-transformers home:

```bash
python3 eval/evq1107/leann/probe.py \
  --root "$PWD" \
  --out eval/evq1107/leann/results.json \
  --index-dir "$ROOT/probe-index"
```

`/usr/bin/time` reported wall 110.85 s. Build 7.5737 s. Search 97.4549 s. Codebase-memory calls are inside that wall clock. The shadow db is `CBM_CACHE_DIR=/home/mark/.cache/pfy/cbm-shadow/db`, project `pfy-mentat-cbm-shadow`. The probe calls `codebase-memory-mcp cli --json`. It does not rebuild that index.

Chat (`LeannChat`) is SKIPPED. It needs a generator, and this lane takes no Ollama, llama-server, hosted model, or API key. DiskANN is SKIPPED. The package is installed and was not selected. Upstream setup for that backend wants system libraries, and this lane does not use sudo.

## Numbers

Corpus: 216 passages, 121 files, 190529 raw text bytes. Sources are `docs/ops/memory-assist-patterns.md` (1 chunk), `docs/ops/integration-stages.md` (15), `docs/eval/TOOLSET-RANKING.md` (10), `scripts/test_select.py` (26), `scripts/catalog_check.py` (14), `scripts/cbm_shadow.py` (31), 114 stage cards under 20 KB, and the Entry 052 slice of `sources/x-posts.md` (2). Chunks are at most 1800 characters with a 200 character overlap.

Index files under the probe dir, excluding the harness `passages.jsonl`:

| File | Bytes |
|------|------:|
| catalog.index | 16582 |
| catalog.ids.txt | 1296 |
| catalog.leann.meta.json | 673 |
| catalog.leann.passages.idx | 2693 |
| catalog.leann.passages.jsonl | 226568 |
| catalog.leann.bm25.sqlite | 372736 |
| Total | 620548 |

Backend hnsw, `is_recompute` true, `is_compact` true, model `sentence-transformers/all-MiniLM-L6-v2`, dim 384. A naive float32 matrix would be 216 * 384 * 4 = 331776 bytes. No produced file is that matrix. `embedding_matrix_stored` is false. The sqlite file is 372736 bytes, which is larger than 80% of the naive matrix, and the probe ignores sqlite, jsonl, idx, txt, and json when it makes that call.

Savings versus the naive matrix, using the whole bundle: (331776 - 620548) / 331776 = -0.8704. The graph file alone is 16582 / 331776, which is 95.00% smaller than the matrix. Dropping the sqlite still leaves 247812 bytes of graph plus passage store, above the 190529 raw bytes. The entry's 97% figure (201 GB to 6 GB, 60 million chunks) was not measured here.

`compression_beats_raw` is false: 620548 > 190529.

File hit means the expected path is in the top 5. Passage hit means one of those rows is that path and contains the expected substring. The same question string goes to vector (`vector_weight` 1.0), BM25 (`vector_weight` 0.0), `search_graph`, and `search_code`.

| id | vector file | vector passage | bm25 file | bm25 passage | vector rank 1 | bm25 rank 1 | cm graph | cm grep |
|----|:-----------:|:--------------:|:---------:|:------------:|:-------------:|:-----------:|:--------:|:-------:|
| p1 | yes | yes | yes | no | yes | yes | no | no |
| p2 | yes | yes | yes | yes | yes | no | no | no |
| p3 | yes | yes | yes | yes | yes | yes | no | no |
| p4 | yes | yes | yes | yes | yes | yes | no | no |
| p5 | yes | yes | yes | yes | yes | yes | no | no |
| p6 | yes | yes | yes | yes | no | yes | no | no |
| c1 | yes | yes | yes | no | no | yes | no | no |
| c2 | yes | yes | yes | yes | no | no | no | no |
| c3 | yes | yes | yes | yes | yes | yes | no | no |
| c4 | yes | yes | yes | yes | no | no | no | no |

Totals: vector file 10/10, BM25 file 10/10, vector passage 10/10, BM25 passage 8/10, vector rank 1 is 6/10, BM25 rank 1 is 7/10, `recovered_by_bm25` is 0. Codebase-memory graph 0/10 and grep 0/10.

Rank 1 is where the methods differ. Vector's first hit on p2 is `docs/ops/memory-assist-patterns.md`. BM25's first hit on that paraphrase is `data/stages/graphify.json`, and the expected file is still inside the top 5. BM25's first hit on the lexical p6 query and on c1 is the expected file. Vector's first hit on those two is `sources/x-posts.md` and `scripts/cbm_shadow.py`. Both miss c2 and c4 at rank 1 and both find them by rank 5. BM25's p1 and c1 file hits do not contain the expected substring. Vector's hits do.

`search_code` with the full question string returned no files on all 10 questions. `search_graph` returned symbols from the whole shadow repo (tests and `pfylib` for most questions, and an empty list for p6). Example: c1's graph top is `tests/test_pfy_build_cloud.py`, not `scripts/test_select.py`. c2's graph top is `tests/test_catalog_self_pipeline.py`, not `scripts/catalog_check.py`.

The two indexes did not see the same corpus. LEANN searched 216 passages that already include every expected file. The shadow graph searches the repo. A 10/10 against a 0/10 on that setup is a real count, and it is an easy count for the tool whose corpus is the answer list.

## Gates

Lightweight size gate for I2: working copy under 50 MB, and no model weights. The venv is 1632621178 bytes and the sentence-transformers home holds MiniLM weights (91579054 bytes). The rule says stay I1 when the copy is over 50 MB or weight-bearing.

Value gate for I3 needs 3 of 4.

1. Gap fill. The open claim is storage. On this corpus the bundle is larger than the raw passages. Retrieval is strong inside the slice and was not shown against an index of the same files in codebase-memory. Fails this check.
2. Operator leverage. Search took 97.4549 s for 20 queries after a 7.5737 s build, on a 1.63 GB install. Fails this check.
3. Evidence. This probe is a runnable path. Passes this check.
4. Blast radius. The install carries torch and embedding weights. Fails this check.

Score 1 of 4. Modularity for a local copy needs all 4. Local code was required to check the storage claim. The cache copy is isolatable and reversible. The surface is not bounded: the meta package pulls leann-core, hnsw, diskann, and a torch stack. I3 is out of scope for this lane, and `self_pipeline` is not set. No gate was wired.

## Risks

- A BM25 sqlite larger than 80% of a float32 matrix is labeled a stored embedding matrix. The compression story then says the matrix is on disk. Recovery: `probe.py` ignores `.sqlite`, `.jsonl`, `.idx`, `.txt`, and `.json` when it sets `embedding_matrix_stored`. `tests/test_leann_probe.py` feeds a stub that sets the flag true and includes an oversized sqlite. The probe result is false. The same test uses an index larger than the raw text and checks that BM25 still records the hit.
- A small index with a wrong file is treated as success because the byte count looks good. Recovery: file hit and `compression_beats_raw` are separate. The miss-mode test expects compression true, vector hit false, and BM25 hit true.
- A dead adapter is counted as zero hits. Recovery: status `skipped`, hits null, probe exit 0. The crash-mode test expects `hnsw` in the skip reason and null hits.
- The HNSW embedding server stays up as a daemon and keeps the parent's stderr pipe, so `subprocess.run` waits for the daemon TTL (default 900 s). Recovery: the adapter starts the searcher with `use_daemon=False` and calls `cleanup()` before it exits. The scored run returned in 110.85 s. If a later run wedges, stop the `hnsw_embedding_server` process this lane started and leave other lanes alone.
- `sentence-transformers` 5.x on this torch raises `AttributeError: module 'numpy' has no attribute 'long'`. NumPy 2.x with torch 2.2.2+cpu then fails inside `emb.numpy()`. Recovery: pin sentence-transformers 3.4.1 and numpy 1.26.4. The scored run encoded with that pair. Tests do not download those wheels.
- DiskANN or chat is required for the claim. Recovery: both are SKIPPED in this report. The HNSW search still ran.

## Pipeline questions

1. Trigger: a catalog question over local files when a keyword miss is the problem. Nothing in this lane registers that trigger.
2. Work: read the passage files, write an HNSW index and a BM25 sqlite under `~/.cache/pfy/tools/leann/probe-index/`. The comparison reads the existing codebase-memory shadow db. No other service. The scored search did not call a model server.
3. Next: nothing. No CI job and no gate.
4. Human re-entry: a later pin that meets the size gate, or a decision to wire a caller. This lane does not do that.
5. Two runs: one worktree and one branch, and one index directory. No new global lock. The probe does not take the local-model lock.

## Verdict

STAY I1. The index bundle is 620548 bytes against 190529 bytes of raw passages, and the CPU install is about 1.63 GB with torch and MiniLM weights. The 50 MB I2 gate fails. Vector passage recall on the slice is 10/10 against BM25 8/10, and rank-1 file hits are 6/10 against BM25 7/10. Storage stays over the gate.
