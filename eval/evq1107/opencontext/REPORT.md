# opencontext evq1107

Verdict: STAY I1. The manifest returned 8 of 8 copied notes and 0 of 8 facts already in this repo. A second process agreed, 8 of 8, after the note bodies were written. `oc search --mode keyword` exited 1 with no API key and returned 0 hits. Graded with/without harness cases: 0. Nothing was wired into a gate.

It does not beat rg on this repo, and it does not beat skill-up on gap H1.

The stage card did not exist. Stage-0 had already passed (license, CLI install, folder/doc/manifest). This probe does not earn I2 or I3, so the card is I1. Catalog HOLD stays. No TOOLS.md row.

## Catalog comparison

Same job: a personal context store an agent can reuse, and gap H1 (a repeatable with/without score). H1 is that harness2 showed no gain and there is no score to re-measure it, or to compare pfy with a plain Build run. The 2026-11-07 ranking gives that score to skill-up, not to a note store.

`eval/evq1107/opencontext/probe.py` token-scans `uses`, `features`, and `tags` on the other cards. Batch-1 under `eval/ev1107/` (agentgg, bumblebee, chiasmus, dspy, egm, hiroute, neatroots, osc) has no personal context store. neatroots is the H1-evals neighbor: its verdict is PROMOTE I2 for an offline trace check, not a note library. `eval/catchup-1107/skill-up/VERDICT` is PROMOTE I3, both arms 5/5, delta 0. skillspector and strata in that directory are other jobs.

| Card | Stage | What it already covers | How OpenContext compares |
| --- | --- | --- | --- |
| skill-up | I3 | With-skill vs no-skill grade. Catch-up: 5 cases, both arms pass, delta 0. | This probe scored 0 cases. It does not close H1. |
| harness2 | I1 | The trial H1 is about. Its own gain was 0. | oc does not re-measure that trial. |
| Harness Score | I0 | Offline grade of harness files, including context files. | A scorer, not a note store. |
| eval-harness (pfy) | I1 | First-party structural ladder. | Already the structural score. oc adds 0. |
| neatroots | I2 | Offline rules on saved traces. | Not a store. This probe fed it no trace. |
| codebase-memory-mcp | I2 | Primary code-graph MCP. | oc saw 0 of 8 repo facts until they were pasted. |
| repowise | I2 | Context packing. Overlaps codebase-memory. | Packs the repo. oc does not read the repo. |
| opencode-mem | I1 | Memory plugin for the OpenCode worker. Local. | Same job class. oc keyword search did not run without a hosted key. |
| LEANN | I1 | Compressed RAG. Not our code memory. | oc search is also an embedding path, and it was skipped. |
| Memvid | I1 | Video-backed memory. No current job. | Different store. Not run. |
| Hermes Agent (feedback loops) | I1 | Feedback pattern already ported as a skill. Tag `#memory`. | The pattern is already in-tree. oc is not that skill. |
| Graphify | I0 | Reference graph. Not the code memory we run. | oc is not a graph. |
| Chroma (or LanceDB) | I0 | Vector store. Code memory is already chosen. | The oc index sits on LanceDB and still asks for an embedding key. Index build was not run. |
| MemPalace | I0 | Verbatim local memory. Post-MVP. | Same shape as a file library. This probe did not beat a file write plus rg. |
| RoBrain | I0 | Decision memory. Needs Postgres. | Different store. Not run. |
| imcodes | I0 | Final-answer memory. Reference only. | Not an install. |
| Agent Beacon | I0 | Copy a session, store a typed lesson. Scoring calls hosted Jev. | oc search also stops on a hosted key. |
| TeaQL Agent Kit | I0 | Agent context policy patterns. | Docs. Not a store we ran. |
| Ruben Hassid context/token hacks | I0 | Token-saving prompts. Not a tool we run. | Not a store. |
| MUE-X | I1 | Unsafe runtime. Tag `#memory`. | Not a store we would turn on. |
| Auto-Company | I1 | Persona patterns. Tag `#consensus-memory`. | Not this CLI. |
| LangGraph (LangChain) | I1 | Graph orchestration. Tag `#rag`. | Not a note store. |
| Grok CLI bootstrap | I3 | Operator sessions. Tag `#code-memory`. | The surface that already runs. oc does not replace it. |
| Kolibri-1, Laguna S 2.1 | I0, I1 | Local weights. Tag `#1m-context`. | A context window, not a store. |
| rg on this worktree | in this repo | Finds the 8 known facts with no store. | 8/8 in 167.4 ms. oc store hits on those facts: 0/8. |
| `./pfy context` | already in this repo | `scripts/pfy_opencontext_205.py` already runs this hello path. | The probe repeated it. It did not add a score. |

## Pins

| Item | Value |
| --- | --- |
| Entry pin | `0649e7134346f6f5038a9b29cc5c824ae6a54f3f` (2026-06-16). Checkout HEAD matches. |
| Checkout package | `@aicontextlab/cli` 0.1.0. `package.json` license field Apache-2.0. Root LICENSE file starts with MIT. |
| npm | `@aicontextlab/cli@0.2.2`. Registry sha1 `518bf681bdd1565225723b81305b499776a7effb`. Tarball sha256 `56bc8d3b60fc62df2a2b22fc95a177471aa09f3fabc1efe4d619e98e2116f15a`. 14,133,474 bytes. |
| npm gitHead | `9c26c0ba35249b26b5325abcd9c79703a220536f` (2026-01-28). Not the entry pin. That commit's `package.json` is still 0.1.0, so gitHead is not the build id of the 0.2.2 tarball. |
| Bytes vs the pin | `bin/oc.js`, `src/core/search/index.js`, `src/core/search/native-adapter.js`, `src/core/store/index.js`, and `src/core/native.js` match the tarball. `package.json` does not. |
| Native | `@aicontextlab/core-native` 0.2.1, linux-x64-gnu, from the optional dependency. |
| Pin tree start | `node bin/oc.js folder ls` at the pin exits 1 in 22.0 ms: `Cannot find module 'commander'`. The probe ran the cache install. |
| Node | v22.23.0. |
| Sizes | Checkout including `.git`: 30,503,015 bytes. npm prefix: 615,361,477 bytes. Neither is committed. |
| License | GitHub LICENSE and the tarball LICENSE start with MIT. `package.json` says Apache-2.0. Both are permissive. The entry treats the GitHub LICENSE as the source of truth. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `TMPDIR`, `OPENCONTEXT_ROOT`, `OPENCONTEXT_CONTEXTS_ROOT`, and `OPENCONTEXT_DB_PATH` pointed under `~/.cache/pfy/tools/opencontext/`. The real `~/.opencontext` stat fingerprint was the same before the install and after the probe (8 entries). No API key was set. `oc init`, `oc ui`, and `oc index build` were not run.

## Commands

```bash
git clone --depth 1 --branch main https://github.com/0xranx/OpenContext.git \
  ~/.cache/pfy/tools/opencontext/src/OpenContext
# HEAD 0649e7134346f6f5038a9b29cc5c824ae6a54f3f
npm pack @aicontextlab/cli@0.2.2 --pack-destination ~/.cache/pfy/tools/opencontext/npm
npm install --prefix ~/.cache/pfy/tools/opencontext/prefix --include=optional \
  ~/.cache/pfy/tools/opencontext/npm/aicontextlab-cli-0.2.2.tgz
python3 eval/evq1107/opencontext/probe.py
```

The probe writes `eval/evq1107/opencontext/results.json`. The store for the run was `~/.cache/pfy/tools/opencontext/run/h1`. Eight notes were created in folder `evq1107-h1`. Each description was one novel token. The context file was empty until the probe wrote that token into the body. Repo needles were not copied into the store.

## Numbers

| Check | Result |
| --- | --- |
| rg, 8 facts already in this repo | 8/8, part of a 167.4 ms scan of 16 needles |
| rg, 8 novel tokens | 0/8 |
| folder create + 8 doc creates | 9 exits 0. 1328.9 ms |
| file walk before the body write | 0/8 novel, 0/8 repo |
| manifest after create | exit 0, 128.3 ms, 8 docs, 8/8 novel, 0/8 repo |
| bodies written | 8 |
| file walk after the body write | 8/8 novel, 0/8 repo |
| second process file walk | exit 0, 24.4 ms, 8/8 novel, 0/8 repo |
| walk agreement on the 8 novel tokens | 8/8 |
| manifest again | exit 0, 133.7 ms, 8 docs, 8/8 novel, 0/8 repo |
| `oc search --mode keyword` | exit 1, 125.7 ms, SKIPPED, API key not configured, 0 hits |
| graded with/without cases | 0 |
| score delta | none |
| real `~/.opencontext` changed | no |

`oc doc create -d` stores the token in sqlite. The manifest prints it. The context file stays empty, so the file walk the existing prove uses is 0/8 until something else writes the body. `./pfy context` does that write itself. Native keyword search builds an embedding client before it looks at mode, so keyword mode still exits on a missing key. That matches the Stage-0 note. `oc index build` was not run, because it would call the embedding API.

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: no. H1 needs a with/without score. skill-up already emits one (5/5 both arms, delta 0). This run emitted 0 graded cases. Facts already in the repo: rg 8/8, oc 0/8.
2. Operator leverage: no. `./pfy context` already runs this hello path. Capture of 8 empty docs took 1328.9 ms and did not make a harness comparison. Search did not run.
3. Evidence: yes. The pin checkout matches. The tarball sha1 matches the registry. Folder, doc, and manifest ran offline. `results.json` records the exits.
4. Blast radius: yes, while it stays in the cache. MIT LICENSE file, Apache-2.0 in `package.json`, both permissive. No model weights. No account. The 615,361,477 byte prefix is not in the repo. It did not become the product runtime. The embedding key stayed unset.

Value score: 2 of 4.

Modularity (all 4, required before an in-repo copy):

1. Local code needed: yes. The empty file after `doc create`, and keyword mode exiting inside the embedding client, showed up when the CLI ran.
2. Bounded surface: no. `oc` is one bin, and the published package pulls the UI, the editor, and a native module. The pin tree does not start without that install (exit 1, missing `commander`).
3. Isolatable: yes. The cache held the checkout, the tarball, the prefix, and the store.
4. Reversible: yes. Deleting the cache leaves the pin and this entry. `oc init` was not run, so `AGENTS.md` was not rewritten.

Modularity fails the bounded surface. The result is no longer ambiguous, and it does not help H1, so the card stays I1. I3 would also need a repeatable pipeline script and `self_pipeline` evidence. The card's uses and features do not match the pipeline role tokens. This lane wires nothing.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Empty doc body | `doc create -d` leaves a 0-byte file. A context-dir file walk scores 0/8 while the manifest says 8/8. | The existing prove writes the body after the manifest. Do not treat `-d` as captured text. |
| Keyword search key | `oc search --mode keyword` exits 1 and tells the operator to set `OPENAI_API_KEY`. 0 hits. | Do not set a key. Record SKIP. Do not run `oc index build`. |
| Pin vs npm | Registry gitHead is not the entry pin, and `package.json` bytes differ (0.1.0 vs 0.2.2). Five CLI source files matched. | Trust the tarball sha256 and the commit. Do not treat gitHead as the build id. |
| Pin tree does not start | `node bin/oc.js` exits 1, missing `commander`. | Use the cache prefix. Do not commit `node_modules`. |
| Real home writes | A run without a redirected `HOME` writes `~/.opencontext`. | Subprocesses used the cache home and `OPENCONTEXT_*`. The real directory stayed unchanged. |
| `oc init` | It rewrites `AGENTS.md`. | Not run. Do not run it in this repo. |
| Second store | Notes in oc and facts in the repo can disagree. rg still sees the repo. oc does not, until a copy. | Leave the card at I1. rg stays the way to read this repo. |
| Heavy install | The prefix is 615,361,477 bytes because the CLI package depends on the UI. | Keep it in the cache. Do not vendor it. |

## Next gate

Stay I1. Do not wire OpenContext into pregate, CI, or a new `./pfy` path. `./pfy context` already proves the hello path. Reopen only if a later pin searches keywords with no API key and beats rg on facts already in this repo, or emits a repeatable with/without harness score. That ticket grills wiring first. Catalog HOLD stays until a separate un-HOLD.

## Five questions (if this tool ran in our pipeline)

1. What triggers it? An operator runs `./pfy context`, or `oc` when the binary is on `PATH`. Nothing in `./pfy` pregate, CI, or the lane scheduler starts oc. This lane adds no trigger.
2. What does it do, and which services does it read and write? It reads and writes a local contexts directory and a sqlite file (`OPENCONTEXT_CONTEXTS_ROOT`, `OPENCONTEXT_DB_PATH`). It does not read this repo unless a person copies a file in. `oc search` calls an embedding API. This lane did not call it. `oc mcp` was not started. No hosted account was used.
3. What does it trigger next? Nothing. The manifest prints JSON. It does not start `catalog_check`, pregate, or a harness grade. Search stops before an index build.
4. Where does a human re-enter? A person chooses which notes to copy, and whether to set an embedding key. Our re-entry stays the `tmp/evq` markers, `tmp/STOP`, and Mark. No key was set.
5. What stops two runs doing the same work? One store directory per `OPENCONTEXT_ROOT`. Two writers can clobber the same folder name. oc does not see the scheduler's `.pid`, `.dispatched`, `.done`, or `.parked` markers. One worktree per slug stays the lock. This probe used its own store under the cache.
