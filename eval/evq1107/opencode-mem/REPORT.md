# opencode-mem evq1107

Verdict: PROMOTE I2. A second process searched 8 of 8 salts that are not in this repo, and listed 8 of 8. rg on the repo found 0 of 8. A notes file found the same 8 in 11.6 ms. A damaged shard did not rebuild (0 of 8). Nothing was wired into a gate.

It does not beat a notes file plus rg for exact recall, and it does not beat skill-up on the harness with/without grade. It does beat an empty store for session facts that were never written into the tree. The OpenCode injection path was not run.

Entry 049 lives in `sources/x-posts.md`. There is no `sources/entries` file for it. That shared log was not edited.

## Catalog comparison

The job is worker memory and context for gap H1: a repeatable with/without number. `probe.py` reads `uses`, `features`, and tags on the other cards and keeps a card when one of these whole words appears: memory, vector, rag, recall, context. That scan hit 20 other cards (`results.json`, overlap length 21 including this card). skill-up and harness2 are the H1 neighbors in `docs/eval/TOOLSET-RANKING.md` and do not carry those words, so they are listed here too. cass-memory landed at I0 while this lane was open. Its uses and features do not contain those whole words, so it is absent from the scan. The table below includes it. ai-memory and kenfold still have no stage card. Batch-1 under `eval/ev1107/` does not add another OpenCode memory plugin. `eval/catchup-1107/skill-up/VERDICT` is the with/without grade (both arms 5/5, delta 0).

| Card | Stage | What it already covers | How opencode-mem compares |
| --- | --- | --- | --- |
| skill-up | I3 | With-skill vs no-skill grade. Catch-up: 5/5 both arms, delta 0. | This probe is not that grade. It scored stored salts, 8/8 vs 0/8 in the tree. |
| cass-memory | I0 | Procedural playbook. One session produced 0 rules. A hand playbook was top-1 on 7/8, token overlap on 8/8, repo facts 0/8. | Same job class, different store. This probe recalled 8/8 salts that are not in the tree. The playbook did not beat a text file. |
| harness2 | I1 | The trial H1 is about. Its own gain was 0. | This run does not re-score that trial. |
| Harness Score | I0 | Offline grade of harness files, including context files. | A scorer, not a store. |
| codebase-memory-mcp | I2 | Primary code-graph MCP. | Decoy search for `smoke-codebase-memory` was not a hit. Different job. |
| repowise | I2 | Context packing. Overlaps codebase-memory. | Packs the repo. This store does not. |
| OpenContext | I1 | Copied notes 8/8, repo facts 0/8. Keyword search needed a key. | Same shape of probe. This search ran on local ONNX and hit 8/8. |
| LEANN | I1 | Compressed RAG. Not our code memory. | Not run here. |
| Memvid | I1 | Video-backed memory. No current job. | Different store. Not run. |
| Hermes Agent (feedback loops) | I1 | Feedback pattern already ported as a skill. Tag `#memory`. | Grok-side pattern. Not an OpenCode plugin. |
| Graphify | I0 | Reference graph. Not the code memory we run. | Not a session store. |
| Chroma (or LanceDB) | I0 | Vector store. Code memory is already chosen. | This plugin embeds Turso itself. It does not replace that choice. |
| MemPalace | I0 | Verbatim local memory. Post-MVP. | Same class of store. Not run. |
| RoBrain | I0 | Decision memory. Needs Postgres. | Different store. Not run. |
| imcodes | I0 | Final-answer memory. Reference only. | Not an install. |
| Agent Beacon | I0 | Copy a session, store a typed lesson. | Different surface. Not run. |
| MUE-X | I1 | Unsafe runtime. Tag `#memory`. | Not a store we would turn on. |
| Auto-Company | I1 | Persona patterns. Tag `#consensus-memory`. | Not this plugin. |
| LangGraph (LangChain) | I1 | Graph orchestration. Tag `#rag`. | Not a memory plugin. |
| Grok CLI bootstrap | I3 | Operator sessions. Tag `#code-memory`. | The monitor surface. This plugin is for the OpenCode worker. |
| Kolibri-1, Laguna S 2.1 | I0, I1 | Local weights. Tag `#1m-context`. | A context window, not a store. |
| TeaQL Agent Kit | I0 | Agent context policy patterns. | Docs. Not a store we ran. |
| rg on this worktree | in this repo | Finds 8 known facts. Finds 0 of the 8 salts. | 0/8 salts in 158.6 ms. |
| notes file plus rg | written under the cache tmp | The same 8 sentences. | 8/8 in 11.6 ms. Faster than the vector recall, same count. |

## Pins

| Item | Value |
| --- | --- |
| git HEAD | `6c5828f3e49f962385aeb3ad033ecac5adc22878` (2026-11-06, release v2.41.1). `git ls-remote` HEAD matches. Checkout HEAD matches. |
| npm | `opencode-mem@2.41.1`. gitHead is the same commit. dist.shasum `5e285c025f956c0c2036aac16de3986d38dc309a`. |
| tarball sha256 | `142d404aea2add4ffbe1742862e912ddfd109e8b0e7533b73de8adf132ecf883` |
| integrity | `sha512-P4L+m89tlVntFwJfQqWBwXW4f5zloUSmp/qNjLfFkcyGH4dPcT+xpu46i02WqppmXXM8Pzq7SFQoDqNhTAO51w==` |
| tarball bytes | 611949 |
| license | MIT (`LICENSE` and `package.json`). |
| Node | v22.23.0. |
| embedder | `Xenova/nomic-embed-text-v1`, the package default, 768 dims, fp32 ONNX. File is 547552426 bytes. |
| sizes | Source checkout 6310354 bytes. npm prefix about 1.2 GB. Neither is committed. |
| project tag | `opencode_project_94f30b5f90fb12f4` |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `npm_config_cache`, and `TMPDIR` for the driver pointed under `~/.cache/pfy/tools/opencode-mem/`. The scored config set `webServerEnabled` false and `autoUpdate` false. No API key was set. Real `~/.config/opencode`, `~/.opencode`, `~/.opencode-mem`, `~/.local/share/opencode`, and `~/.cache/opencode` directory mtimes did not change (`real_home_changed` is empty). `~/.opencode-mem` was absent before and after.

## Commands

```bash
git clone --depth 1 https://github.com/tickernelz/opencode-mem.git \
  ~/.cache/pfy/tools/opencode-mem/src/opencode-mem
# HEAD 6c5828f3e49f962385aeb3ad033ecac5adc22878
npm pack opencode-mem@2.41.1 --pack-destination ~/.cache/pfy/tools/opencode-mem/npm
npm install --prefix ~/.cache/pfy/tools/opencode-mem/prefix --omit=dev --include=optional \
  ~/.cache/pfy/tools/opencode-mem/npm/opencode-mem-2.41.1.tgz
python3 eval/evq1107/opencode-mem/probe.py
```

The probe writes `eval/evq1107/opencode-mem/results.json`. The driver is `eval/evq1107/opencode-mem/driver.mjs`. It calls `memoryClient.addMemory`, then a new process calls `listMemories` and `searchMemories`, then a third process overwrites the shard db with `not a database` and tries to open it. The scored storage path was `~/.cache/pfy/tools/opencode-mem/run/data`, with the ONNX cache linked in so the model was not downloaded again. Before store, the probe removes every file in that directory except `.cache`. This scored run started from the damaged shard the previous run left behind.

`python3 -m unittest tests.test_opencode_mem_probe` drives the same script with a stub driver and a stub rg. No network and no real package. A corrupt arm that prints the salt and claims a hit while `ok` is false stays at 0 hits.

## Numbers

Scored run (`results.json`):

| Check | Result |
| --- | --- |
| rg, 8 facts already in this repo | 8/8, part of a 158.6 ms scan |
| rg, 8 salts, probe files excluded | 0/8 |
| notes file plus rg | 8/8 in 11.6 ms |
| store, model already cached | 8/8, one attempt each, wall 1149.2 ms, warmup() 688 ms |
| list after a new process | 8/8 |
| search after a new process | 8/8, wall 1034.2 ms, warmup() 721 ms, top similarity 0.7 |
| decoy `smoke-codebase-memory` | search ran, content hit 0 |
| damaged shard | open failed, search hits 0, list hits 0, 93.0 ms |
| real home dirs changed | no |

`warmup_ms` is only the `warmup()` call. Wall time is that call plus the adds, or plus the list and the searches.

First attempt, default template, cold ONNX load (`cold-start.txt`): salt 01 timed out at 30000 ms, 7 salts stored, the new process searched 7 of those 7. The missing salt's top neighbor had similarity 0.6315 and did not contain the salt. Deleting the shard files while `metadata.db` still named them blocked the next write.

No Ollama call. The embedder is local ONNX. `scripts/model_lock.sh` was not needed.

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: no. The 8 salts are absent from the repo (rg 0/8) and present after restart (8/8). A notes file plus rg also returns 8/8 in 11.6 ms. skill-up already emits the harness with/without grade. codebase-memory stays the code graph. OpenCode injection was not shown.
2. Operator leverage: no. Store and recall took about a second each once the 522 MB ONNX file was cached, against 11.6 ms for rg. No worker session ran. Auto-capture stayed off.
3. Evidence: yes. The checkout, tarball sha1, and tarball sha256 match the pin. `results.json` records the exits.
4. Blast radius: yes, while it stays in the cache. MIT. No account. No model weights in the repo. The 1.2 GB prefix and the 547552426 byte ONNX file are not committed. The scored config did not bind port 4747 and did not auto-update. It did not become the product runtime.

Value score: 2 of 4.

Modularity (all 4):

1. Local code needed: yes. The 30 s embed timeout, jsonc winning over a sibling json file, and a deleted shard that blocks writes showed up only when the package ran.
2. Bounded surface: yes. One npm package, plugin id `opencode-mem`, and `memoryClient` add/search/list. The tarball also ships a web UI. This probe did not start it.
3. Isolatable: yes. Checkout, prefix, store, and ONNX cache sat under `~/.cache/pfy/tools/opencode-mem/`.
4. Reversible: yes. Deleting the cache leaves the pin and this card. The repo gained no plugin install.

Modularity passes. The recall number is a real gain against an empty store, so the card moves to I2. I3 would need the value gate and a repeatable pipeline script with `self_pipeline` evidence. The card's uses and features do not match the pipeline role tokens. This lane wires nothing.

Source checkout is 6310354 bytes, under the 50 MB I2 copy limit. The install stays in the cache.

`tier_ceiling` stays I1. That is the formula cap for catalog tier A in `scripts/catalog_stage_eval.py`. `integration_stage` is I2 because this probe measured a gain. A later `--apply` keeps a ceiling that is already above the formula, so this card matches repowise: stage I2, ceiling I1.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Cold embed | The first `addMemory` times out at 30000 ms while the ONNX file loads. That salt is missing. A later search can still return a neighbor above the 0.6 threshold. | Retry the add after warmup. Count a hit only when the salt is in the memory text. The cold run stored 7 of 8 and the new process searched those 7. The scored run, model already cached, stored 8 of 8 on the first attempt. |
| Deleted shard | Removing the db while `metadata.db` still names it returns "incompatible or corrupt" and does not create a new file. | The probe deletes metadata and shard files before store and keeps the `.cache` link. A manual recovery is a new `storagePath` or a restored file. |
| Damaged db | Overwriting the shard with `not a database` fails the open. Hits stay 0. | Restore the file or re-add into a new directory. The probe records the error and does not turn it into a pass. |
| jsonc template | A missing `opencode-mem.jsonc` is created on import, and that file wins over `opencode-mem.json`. The first attempt ignored the json settings. | Write `opencode-mem.jsonc` before the process starts. The scored run did that. |
| Default plugin load | The template enables the web server on 127.0.0.1:4747 and auto-update. | The scored config turned both off. Do not load the plugin into the real OpenCode home from this lane. |

## Next gate

Stay I2. The next proof is one OpenCode worker run under the model lock, with this plugin and without it, on these 8 salts. Promote toward I3 only if the with-plugin arm recalls salts the without-plugin arm misses, and a later ticket wires nothing until that smoke is the record. No Feature GO.

## Five questions (this tool in the pipeline)

1. What triggers it? An OpenCode worker session that loads the pinned plugin, or a manual `addMemory`. This lane adds no CI trigger.
2. What does it do, and which services does it read and write? It reads the project path and the Turso store under `storagePath`. It writes memories and the local ONNX cache. This config uses `Xenova/nomic-embed-text-v1` on CPU. It does not call a hosted model. Auto-capture was off, so this run did not call Ollama.
3. What does it trigger next? On a real OpenCode load it would inject search hits into the next model request. This lane triggers nothing else.
4. Where does a human re-enter? When a shard is corrupt, writes stay blocked until the file is restored or the storage directory is replaced. Gate wiring waits for a separate ticket and Mark's GO.
5. What stops two runs doing the same work? `metadata.db` names one active shard per project hash. A second writer that deletes or damages that file fails closed instead of inserting a second copy. This lane is one worktree and one storage directory.
