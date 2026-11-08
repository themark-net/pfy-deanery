# MemPalace evq1107

Verdict: STAY I1. Top-1 recall was 8/8 on eight verbatim excerpts from this repo. A word-overlap walk of the same excerpts was 6/8. A second unscoped search agreed 8/8. Searches limited to the other wing leaked 0 of 8 expected files, and the correct wing still kept 8/8. Graded with/without harness cases: 0. The pinned work tree without git is 68560448 bytes. The MiniLM `model.onnx` file is 90387606 bytes. Both are over the 50 MB I2 copy limit, and the embedder is a required weight. Nothing was wired into a gate.

It beats a word walk on this eight-question set by two questions (`value-gate`, `skill-grade`). It does not close gap H1. skill-up already grades a with-skill arm against a no-skill arm (catch-up: both arms 5/5, delta 0). This probe emitted 0 graded cases.

## Catalog comparison

Same job: local verbatim memory with scoped search, and the lane gap H1 (a repeatable with/without score for memory and context). The 2026-11-07 ranking puts MemPalace on the post-MVP memory slot (row 10, with RoBrain) and puts skill-up on H1. `eval/evq1107/mempalace/probe.py` token-scans `uses`, `features`, and tags on the other cards for memory, verbatim, recall, rag, embedding, embeddings, chroma, handoff, vector, bm25, and code-memory. That scan returned 14 cards. Batch-1 under `eval/ev1107/` has no verbatim palace trial. `eval/catchup-1107/skill-up/VERDICT` is PROMOTE I3.

| Card | Stage | What it already covers | How MemPalace compares |
| --- | --- | --- | --- |
| skill-up | I3 | With-skill vs no-skill grade. Catch-up: 5 cases, both arms pass, delta 0. | This probe scored 0 cases. The recall number is a different score. |
| harness2 | I1 | The trial H1 is about. Local harness edit on the decision set. | MemPalace does not re-measure that trial. |
| codebase-memory-mcp | I2 | Primary code-graph MCP. | A graph. This probe mined eight short excerpts, not the code graph. |
| opencode-mem | I1 | Memory plugin for the OpenCode worker. | Same job class. This lane did not run it. |
| LEANN | I1 | Compressed RAG. CPU install about 1.63 GB. Stayed I1 on size. | Same shape of local embed and search. LEANN's install is larger. This probe's onnx file is still over 50 MB. |
| OpenContext | I1 | Personal context store. 8/8 copied notes, 0/8 facts already in the repo, keyword search skipped on a key. | MemPalace search ran with no key. Top-1 was 8/8 on excerpts it had mined. |
| Memvid | I1 | Video-backed memory. No current job. | Different store. Not run. |
| Chroma (or LanceDB) | I0 | Vector store. Code memory is already chosen. | MemPalace's default backend is Chroma. This lane did not add a second store to the product. |
| Graphify | I0 | Reference graph. Not the code memory we run. | A graph, not a drawer index. |
| RoBrain | I0 | Decision memory with vetoes. Needs Postgres. | Different question (what was rejected). Not run. |
| Agent Beacon | I0 | Copy a session, store a typed lesson. Scoring calls hosted Jev. | This probe made no hosted call. |
| imcodes | I0 | Final-answer memory. Reference only. | Not an install. |
| Hermes Agent (feedback loops) | I1 | Feedback pattern already ported as a skill. | The pattern is already in-tree. |
| Grok CLI bootstrap | I3 | Operator sessions. Tag code-memory. | The surface that already runs. |
| LangGraph (LangChain) | I1 | Graph orchestration. Tag rag. | Different job. |
| MUE-X | I1 | Unsafe runtime. Tag memory. | Not a store we would turn on. |
| cass-memory (108) | no card, entry I0 | Scored playbook. Keyword context on the Grok Bot box. | Not executed. The license rider counts benchmarking in an evaluation harness as use. The entry says Mark decides before a trial. |
| ai-memory (132) | no card, entry I0 | Git-backed wiki and claim-once handoffs. Smoke PASS on the Grok Bot box. | Not executed. Its cache is another lane's, and `setup` writes harness config. |
| word-overlap walk | in this probe | Scores the eight excerpts by shared content words. | 6/8. MemPalace top-1 was 8/8. The walk has no wing filter. |

## Pins

| Item | Value |
| --- | --- |
| Entry pin | `84582fb055a6429261f9c779da86c0561ec80adc` (2026-10-25T04:41:28Z). `git rev-parse HEAD` matches. |
| Version | `mempalace --version` prints `MemPalace 3.12.0`. `pyproject.toml` version is 3.12.0. |
| License | MIT. `LICENSE` starts with "MIT License". |
| Python | uv CPython 3.12.12. System Python 3.14 was not used. The pin's `.python-version` is 3.12. |
| Packages that ran | mempalace 3.12.0 from the pinned tree, chromadb 1.5.9, onnxruntime 1.31.1. |
| Embedder | `minilm`, Chroma's all-MiniLM-L6-v2 ONNX. `model.onnx` 90387606 bytes. `onnx.tar.gz` 83178821 bytes. Chroma cache dir 174510889 bytes. |
| Work tree | 68560448 bytes excluding `.git`. `.git` is 17951917 bytes. `results.json` `src_bytes` is 86512365, which is the tree plus `.git`. Large files include three benchmark jsonl dumps (about 13 MB, 13 MB, and 12 MB) and `website/public/hero_video.mp4` (8411136 bytes). |
| Install sizes | `du -sb` venv 372820504 bytes. `du -sb` uv cache 58620845 bytes. Palace after the warm run 713510 bytes. None of these are committed. |
| Checksum | The entry gives a commit, not a tarball digest. The commit was re-checked with `git rev-parse`. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `TMPDIR`, `UV_CACHE_DIR`, and `HF_HOME` pointed under `~/.cache/pfy/tools/mempalace/`. The real home paths `.mempalace`, `.config/mempalace`, and `.cache/chroma` were absent before and after both runs. No API key was set. `--no-llm` was passed. `serve`, MCP, `wake-up`, and convos mining were not run. The model lock was not taken. This path does not call Ollama.

## Commands

```bash
ROOT=$HOME/.cache/pfy/tools/mempalace
git init "$ROOT/src/mempalace"
git -C "$ROOT/src/mempalace" remote add origin https://github.com/MemPalace/mempalace.git
git -C "$ROOT/src/mempalace" fetch --depth 1 origin 84582fb055a6429261f9c779da86c0561ec80adc
git -C "$ROOT/src/mempalace" checkout --detach FETCH_HEAD
uv venv --python /home/mark/.local/share/uv/python/cpython-3.12.12-linux-x86_64-gnu/bin/python3.12 "$ROOT/venv"
uv pip install --python "$ROOT/venv/bin/python" "$ROOT/src/mempalace"
python3 eval/evq1107/mempalace/probe.py \
  --repo "$PWD" \
  --out eval/evq1107/mempalace/results.json \
  --bin "$ROOT/venv/bin/mempalace" \
  --work "$ROOT/probe-work" \
  --home "$ROOT/home" \
  --src "$ROOT/src/mempalace" \
  --timeout 180
```

The probe copies a short window around eight anchors into a cache corpus, two wings (`handoff`, `ranking`). It runs `init --yes --no-llm --embedding-model minilm` on that corpus, then `mine --wing` once per wing, then each question four times: unscoped, unscoped again, the other wing, and the owning wing. `init` writes `mempalace.yaml` into the scanned directory. The scanned directory is the cache corpus. The repo gained no `mempalace.yaml`.

`python3 -m unittest tests.test_mempalace_probe` drives the same script with a stub `mempalace` binary. No network and no real binary. A decoy at rank 1 stays a top-1 miss and the expected file at rank 2 counts as top-5. The first `mine` of each wing can fail once. The probe retries that wing once and then scores. The stub writes `mempalace.yaml` only into the directory it was given. The fixture repo stays free of that file.

## Numbers

Corpus: 8 excerpts, 8 drawers filed, 0 mine retries. Anchors are real lines in this repo. Questions do not contain the anchor string.

| Check | Cold run | Warm run (results.json) |
| --- | --- | --- |
| Wall | 57.60 s | 42.53 s |
| init | 1.003 s, exit 0 | 0.96 s, exit 0 |
| mine | 17.539 s (onnx download) | 2.863 s |
| search | 38.895 s | 38.59 s |
| drawers | 8 | 8 |
| top-1 | 8/8 | 8/8 |
| top-5 | 8/8 | 8/8 |
| repeat agreement | 8/8 | 8/8 |
| word-overlap walk | 6/8 | 6/8 |
| other-wing leaks | 0/8 | 0/8 |
| other-wing label mismatches | 0 | 0 |
| owning-wing kept | 8/8 | 8/8 |
| h1 graded cases | 0 | 0 |
| repo yaml added | 0 | 0 |
| real home watched paths | unchanged (absent) | unchanged (absent) |

The walk missed `value-gate` and `skill-grade` (no unique winning excerpt). MemPalace ranked both first. The other six matched the walk.

Upstream's 96.6% LongMemEval R@5 was not reproduced. This set is eight short windows, not that benchmark.

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: no. H1 needs a with/without score. skill-up already emits one (5/5 both arms, delta 0). This run emitted 0 graded cases. On the memory question it did beat the word walk, 8/8 against 6/8, with a wing filter the walk does not have. cass-memory and ai-memory were not on the same questions, so that bake-off is still open.
2. Operator leverage: no. Two runs of eight excerpts, 57.60 s cold and 42.53 s warm, did not become a session primer or a harness comparison. `wake-up` was not run.
3. Evidence: yes. The pin matches. Version 3.12.0 matches. Both runs scored. `results.json` records the warm run.
4. Blast radius: yes, while it stays in the cache. MIT. No account. No multi-GB weight. The venv is 372820504 bytes (`du -sb`) and is not in the repo. It did not become the product runtime.

Value score: 2 of 4.

Modularity (all 4, required before an in-repo copy):

1. Local code needed: yes. The 8/8 top-1 and the 0 wing leaks showed up when the CLI ran. The README number was not the measurement.
2. Bounded surface: yes for the commands that ran (`init`, `mine`, `search`, with `--wing` and `--no-llm`). MCP, `serve`, rust, and docker were not the unit of eval.
3. Isolatable: yes. The checkout, the venv, the palace, and the embedder stayed under `~/.cache/pfy/tools/mempalace/`.
4. Reversible: yes. Deleting that cache leaves the pin and this entry. The repo was not initialized.

Modularity passes. The lightweight size gate does not. The work tree without git is 68560448 bytes and the onnx file is 90387606 bytes. The stage scheme stays at I1 when the tree or the weights are over 50 MB. I3 would also need a pipeline script and `self_pipeline` evidence. The card's uses and features do not match the pipeline role tokens. This lane wires nothing.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Wrong recall | Search ranks a decoy first and the agent uses the wrong excerpt | The probe counts top-1 and top-5 separately. The stub test keeps a rank-1 decoy as a miss and counts the expected file at rank 2 as top-5. On this set top-1 was already 8/8, so that recovery was not needed. |
| Writes outside scratch | `init` writes `mempalace.yaml` into the scanned directory | The probe refuses a work dir inside the repo and scans only the cache corpus. Both runs added 0 yaml files in the repo. The stub test checks the same. |
| Mine or palace failure | The first `mine` exits non-zero, or Chroma cannot read the index | The probe retries that wing once. If the retry fails it records a skip and does not invent a score. This run needed 0 retries. A broken palace is rebuilt by mining the excerpts again. |
| Weights and network | The first mine downloads about 90 MB of ONNX, and a later pin can grow past the size gate | The warm run used the cache. If the file is missing, the score stays unclaimed until a download into the cache home succeeds. Do not copy the onnx file into the repo. |
| License on the comparison tools | Running cass-memory inside this harness hits the rider the entry already flags | This lane did not execute it. Mark decides before any cass-memory trial. |

## Next gate

Stay I1. Re-open I2 only if a later pin keeps top-1 above 6 of 8 on these eight questions, keeps wing leaks at 0, and both the work tree and the embedder are under 50 MB. The same questions against cass-memory (108) and ai-memory (132) are still open. No gate wiring. No Feature GO.

## Five questions (if this tool ran in the pipeline)

1. What triggers it? A later memory lane, or an operator asking for a scoped recall of handoff excerpts before a session. This eval lane does not leave that trigger in place.
2. What does it do, and which services does it read and write? It reads a copy of the excerpts and writes a Chroma palace plus `mempalace.yaml` in that copy. The embedder is local ONNX. No hosted model, no account, no Ollama lock.
3. What does it trigger next? Nothing in this lane. A same-question run of cass-memory and ai-memory would be a separate ticket. Gate wiring would be another ticket with a grill step.
4. Where does a human re-enter? The size exception (work tree and onnx both over 50 MB), the cass-memory license decision, or any request to put search in front of a session. `tmp/evq/mempalace.parked` and `tmp/STOP` also stop this lane.
5. What stops two runs doing the same work? One worktree and one palace directory per run. This probe deletes `probe-work` before a clean run. Two mines of one palace at once can corrupt Chroma. Recovery is to delete that palace and mine the excerpts again. Lanes do not share this stage card.
