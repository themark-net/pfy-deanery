# kenfold evq1107

Verdict: STAY I1. Stdio recall returned 8 of 8 copied tokens to a second agent, and the second pass agreed, 8 of 8. The same store returned 0 of 8 facts already in this repo. A secret fixture was rejected and the error did not echo it. Graded with/without harness cases: 0. Nothing was wired into a gate.

It does not beat rg on this repo, it does not beat skill-up on gap H1, and it does not beat opencode-mem, which is already I2 for 8 of 8 stored salts with no Postgres. It also does not beat ai-memory, which stayed I1 for 8 of 8 pasted notes, 0 of 8 repo facts, and 8 of 8 claim-once handoffs.

The stage card did not exist. The entry had left Kenfold at I0 until Docker was confirmed. This probe used rootless podman, not a new Docker install. The result does not earn I2 or I3. No TOOLS.md row.

## Catalog comparison

Same job: one memory store several agent CLIs can read, and gap H1 (a repeatable with/without score, plus memory and context). H1 is that harness2 showed no gain and there is no score to re-measure it, or to compare pfy with a plain Build run. The 2026-11-07 ranking gives that score to skill-up. Shared memory for its own sake is the post-MVP slot (MemPalace, RoBrain), not the H1 score.

`eval/evq1107/kenfold/probe.py` token-scans the card name, `uses`, `features`, `tags`, and `catalog_tags`. It listed 28 cards. Batch-1 under `eval/ev1107/` (agentgg, bumblebee, chiasmus, dspy, egm, hiroute, neatroots, osc) has no shared memory server. neatroots is the H1-evals neighbor: `eval/ev1107/neatroots/VERDICT` is PROMOTE I2 for an offline trace check, not a memory store. `eval/catchup-1107/skill-up/VERDICT` is PROMOTE I3, both arms 5/5, delta 0. skillspector and strata in that directory are other jobs. `eval/evq1107/opencode-mem/VERDICT` is PROMOTE I2: a second process recalled 8 of 8 stored salts, rg found 0 of 8, and a notes file found the same 8 in 11.6 ms. `eval/evq1107/ai-memory/VERDICT` is STAY I1: pasted search 8/8, repo facts 0/8, claim-once 8/8. `eval/evq1107/cass-memory/VERDICT` is STAY I0. `eval/evq1107/mempalace/VERDICT` is STAY I1.

| Card | Stage | What it already covers | How Kenfold compares |
| --- | --- | --- | --- |
| skill-up | I3 | With-skill vs no-skill grade. Catch-up: 5 cases, both arms pass, delta 0. | This probe graded 0 cases. It does not close H1. |
| harness2 | I1 | The trial H1 is about. Its own gain was 0. | Kenfold does not re-measure that trial. |
| Harness Score | I0 | Offline grade of harness files, including context files. | A scorer, not a shared store. |
| eval-harness (pfy) | I1 | First-party structural ladder. | Already the structural score. Kenfold adds 0. |
| neatroots | I2 | Offline rules on saved traces. | Not a store. This probe fed it no trace. |
| codebase-memory-mcp | I2 | Primary code-graph MCP. | Kenfold saw 0 of 8 repo facts until they are pasted. Different job. |
| repowise | I2 | Context packing. Overlaps codebase-memory. | Packs the repo. Kenfold does not read the repo. |
| opencode-mem | I2 | Worker memory. Second process 8/8 stored salts. rg 0/8. Notes file 8/8 in 11.6 ms. | Same pasted-fact count. Kenfold still needs Postgres. It does not beat this. |
| ai-memory | I1 | Git wiki plus a claim-once mailbox. Pasted search 8/8, repo facts 0/8, claim-once 8/8. | Same pasted count. Same miss on repo facts. This probe did not measure claim-once. It does not beat this card. |
| OpenContext | I1 | Personal note store. Its probe was 8/8 copied notes, 0/8 repo facts, 0 graded cases. | Same shape of result. OpenContext stayed I1. |
| cass-memory | I0 | Procedural playbook. 0 rules from one session. Hand playbook top-1 7/8. | Different store. This probe did not run that playbook. |
| LEANN | I1 | Compressed RAG. Not our code memory. | Kenfold's vector path was off. Full-text only. |
| Memvid | I1 | Video-backed memory. No current job. | Different store. Not run. |
| Hermes Agent (feedback loops) | I1 | Feedback pattern already ported as a skill. Tag memory. | The pattern is already in-tree. |
| Graphify | I0 | Reference graph. Not the code memory we run. | Not this store. |
| Chroma (or LanceDB) | I0 | Vector store. Code memory is already chosen. | Kenfold brings another Postgres plus pgvector. Not used for vectors here. |
| MemPalace | I1 | Verbatim local memory. Top-1 on 8/8 of its questions. Checkout over 50 MB, so it stayed I1. | This probe did not run that question set. |
| RoBrain | I0 | Decision memory. Needs Postgres. | Same dependency shape. Not run. |
| imcodes | I0 | Final-answer memory. Reference only. | Not an install. |
| Agent Beacon | I0 | Copy a session, store a typed lesson. Scoring calls hosted Jev. | Kenfold's hosted bench was skipped. No key. |
| TeaQL Agent Kit | I0 | Agent context policy patterns. | Docs. Not a store we ran. |
| Ruben Hassid context/token hacks | I0 | Token-saving prompts. Not a tool we run. | Not a store. |
| MUE-X | I1 | Unsafe runtime. Tag memory. | Not a store we would turn on. |
| Auto-Company | I1 | Persona patterns. Tag consensus-memory. | Not this server. |
| LangGraph (LangChain) | I1 | Graph orchestration. Tag rag. | Not this server. |
| Grok CLI bootstrap | I3 | Operator sessions. Tag code-memory. | The surface that already runs. Kenfold was not attached to it. |
| Kolibri-1, Laguna S 2.1 | I0, I1 | Local weights. Tag context. | A context window, not a store. |
| rg on this worktree | in this repo | Finds the 8 known facts with no store. | 8/8 in 141.0 ms. Kenfold hits on those facts: 0/8. |

## Pins

| Item | Value |
| --- | --- |
| Entry pin | `dfc18f9f1a7be98c5af8c0e7e1cbf566c37d51af`. Tag `v0.1.1` (annotated). `git describe --tags --exact-match` prints `v0.1.1`. |
| Go | `go1.27.2` linux-amd64. Tarball sha256 `ecbadb99091a3f46e31f5f934b068b1864eafa7995211b39eaddf76996045fe5`. 70,590,635 bytes. Upstream's v0.1.1 notes say 1.27.2 or newer. |
| Binary | `kenfold v0.1.1 (commit dfc18f9, built 2026-11-08T04:50:13Z)`. sha256 `a54fff6fff63d8a845957ba33b4548a3b1ffc84d2122e4938e00a3967acbdd23`. 29,515,936 bytes. |
| Image | `docker.io/pgvector/pgvector:0.8.6-pg18-trixie`. Id `b4a0a7b473ee375a4d5507e712a0646447dd2d3293a5e6987fbade5ee73e54dc`. Podman reports 469 MB. |
| Sizes | Checkout including `.git`: 31,827,804 bytes. Go toolchain dir: 244,137,476 bytes. Podman store: 462,285,900 bytes. None of that is committed. |
| License | GitHub LICENSE starts with MIT. Copyright 2026 Jeongwan Jeon. |
| Newer tag | A `kenfold version` during the build, before `KENFOLD_UPDATE_CHECK=false`, printed an update notice for v0.1.3. This lane did not fetch it. The probe set the flag, and its version line has no update notice. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` for the tool pointed under `~/.cache/pfy/tools/kenfold/`. Podman used `--root` and `--runroot` in that cache. The database password stayed in a mode 0600 file there and was not printed. The URL has no password. No API key was created. `KENFOLD_EMBED_URL` and `KENFOLD_CHAT_URL` were unset. The real `~/.local/state/kenfold` and `~/.cache/kenfold` were absent before and after (`real_home_unchanged` true).

## Commands

```bash
git clone --branch v0.1.1 https://github.com/jeonjw85/kenfold.git \
  ~/.cache/pfy/tools/kenfold/src/kenfold
# HEAD dfc18f9f1a7be98c5af8c0e7e1cbf566c37d51af, describe v0.1.1
# go1.27.2 extracted under ~/.cache/pfy/tools/kenfold/go
# sha256 ecbadb99091a3f46e31f5f934b068b1864eafa7995211b39eaddf76996045fe5
cd ~/.cache/pfy/tools/kenfold/src/kenfold
PATH="$HOME/.cache/pfy/tools/kenfold/go/bin:$PATH" CGO_ENABLED=0 GOTOOLCHAIN=local make build
cp bin/kenfold ~/.cache/pfy/tools/kenfold/bin/kenfold
podman --root ~/.cache/pfy/tools/kenfold/podman/root \
  --runroot ~/.cache/pfy/tools/kenfold/podman/run \
  pull docker.io/pgvector/pgvector:0.8.6-pg18-trixie
python3 eval/evq1107/kenfold/probe.py
```

The probe writes `eval/evq1107/kenfold/results.json`. It starts Postgres on `127.0.0.1:54329` as container `pfy-evq-kenfold-pg` in that podman root, runs `kenfold migrate up`, then speaks newline JSON-RPC to `kenfold mcp`. The writer agent is `grok-build`. The reader agent is `opencode`. Both use `KENFOLD_AGENT`. Neither uses an API key. The probe then removes the container and the volume.

`python3 -m unittest tests.test_kenfold_probe` drives the same script with stub `kenfold` and `rg` binaries. No network, no podman, and no real binary. A migrate exit of 1 stays a skip and still records the rg score. A rejected secret is not a hit, and the 8 clean tokens still come back.

## Numbers

| Check | Result |
| --- | --- |
| rg, 8 facts already in this repo | 8/8, part of a 141.0 ms scan of 16 needles |
| rg, 8 novel tokens | 0/8 |
| postgres start | attempt 1, then removed |
| migrate up | exit 0, 47.8 ms |
| secret fixture remember | rejected, not echoed |
| 8 remembers | 8 active, writer session 33.0 ms including the rejected call |
| reader recall, 8 novel tokens | 8/8, source agent `grok-build` on 8/8 |
| reader recall, 8 repo facts | 0/8 |
| first reader session | 30.3 ms (8 novel queries plus 8 repo queries) |
| second reader session | 8/8 novel, 27.2 ms |
| agreement on the 8 novel tokens | 8/8 |
| graded with/without cases | 0 |
| score delta | none |
| embeddings, reranker, chat, OAuth, API key | off or not created |
| hosted bench (`make bench`, LoCoMo) | SKIPPED. It wants a bench API key and a chat model. This lane does not. |
| real home kenfold dirs changed | no |

Recall was full-text. The query was the token itself, which is also in the stored sentence. This is not the upstream hybrid or rerank number (their holdout recall@5 of 0.96 needs embeddings and a reranker, and this lane did not run that set).

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: no. H1 needs a with/without score. skill-up already emits one (5 cases, both arms pass, delta 0). This run graded 0 cases. Facts already in the repo: rg 8/8 in 141.0 ms, Kenfold 0/8. Pasted tokens: opencode-mem already recalls 8/8 with no Postgres. ai-memory already recalls 8/8 pasted notes and claimed 8/8 handoffs, also with no Postgres.
2. Operator leverage: no. Nothing in the operator path reads this store. Copying 8 sentences into Postgres did not make a harness comparison, and it did not beat the I2 opencode-mem recall.
3. Evidence: yes. The pin matches. The image id matches the pull. Stdio remember, recall, provenance, and the secret rejection ran with no key. `results.json` records the exits.
4. Blast radius: yes, while it stays in the cache. MIT. No model weights. The 469 MB image and the Go toolchain are not in the repo. The container and volume were removed. It did not become the product runtime. No account and no API key.

Value score: 2 of 4.

Modularity (all 4, required before an in-repo copy):

1. Local code needed: yes. Provenance on the second agent, and rejection of the secret fixture, showed up when `kenfold mcp` ran.
2. Bounded surface: yes. One Go binary. Postgres is a pinned image, not a second product tree. The checkout is 31,827,804 bytes, under the 50 MB copy limit. This lane left the copy in the cache.
3. Isolatable: yes. The cache held the checkout, the toolchain, the binary, and the podman store.
4. Reversible: yes. Deleting the cache leaves the pin and this entry. No agent config was edited.

Modularity passes. The result is no longer ambiguous, and it does not help H1, so the card stays I1. I2 is for a probe that measurably helps while the value is still unclear. I3 would also need a repeatable pipeline script and `self_pipeline` evidence. The card's uses and features do not match the pipeline role tokens. This lane wires nothing.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Postgres will not start | The probe records SKIPPED after 3 attempts and still writes the rg score. Recall stays 0/8. | Leave the card at I1. Do not install Docker. Do not point the probe at a foreign container. |
| Secret in a write | `remember` returns an error and does not echo the value. The other 8 writes still count. | Do not store the fixture. Do not create an API key to bypass the filter. |
| Migrate fails | The live arm is skipped. The report still has the rg numbers. | Fix the database and re-run. The stub covers this path. |
| Exact token looks like search quality | Full-text finds a sentence that contains the query. Paraphrase recall was not measured. | Do not quote upstream 0.96 as this run. Leave embeddings off until a later lane. |
| `kenfold key create` prints a key | The key lands in a log. | Do not run it. Stdio uses `KENFOLD_AGENT`. Rotate if a key is ever printed. |
| Port 54329 is taken | `podman run` fails. The probe skips instead of killing another process. | Record SKIPPED. The scheduler's one worktree per slug stays the lock. |
| Pin is behind v0.1.3 | A later build is not what this card measured. | Stay on `dfc18f9f` until a lane re-pins on purpose. |
| Real home writes | A run without a redirected HOME can create `~/.local/state/kenfold`. | Children used the cache home. Those two real paths stayed absent. |
| Container left up | A killed probe can leave `pfy-evq-kenfold-pg` in the cache podman root. | `podman rm -f` and `volume rm -f` that name in the cache root. It is not the default podman store. |
| Second store | Sentences in Kenfold and facts in the repo can disagree. rg still sees the repo. | Leave the card at I1. rg stays the way to read this repo. |

## Next gate

Stay I1. Do not wire Kenfold into pregate, CI, or a client config. Reopen only if a later pin, still with no API key and no hosted model, beats rg on facts already in this repo or emits a repeatable with/without harness score. A bake-off against opencode-mem is a different ticket. ai-memory already stayed I1 on the same pasted-note shape and also claimed 8 of 8 handoffs.

## Five questions (if this tool ran in our pipeline)

1. What triggers it? An operator would start Postgres and point a CLI at `kenfold mcp`. Nothing in `./pfy` pregate, CI, or the lane scheduler starts it. This lane adds no trigger.
2. What does it do, and which services does it read and write? It reads and writes one loopback Postgres (`127.0.0.1:54329`, database name `kenfold`) through stdio. It does not read this repo unless an agent copies a sentence in. It does not call a hosted model. This lane set no API key and removed the container and volume at the end.
3. What does it trigger next? Nothing. Recall returns JSON to the client. It does not start `catalog_check`, pregate, or a harness grade.
4. Where does a human re-enter? A person would approve preferences and would have to choose any public URL. Our re-entry stays the `tmp/evq` markers, `tmp/STOP`, and Mark. No key was created. No tunnel was opened.
5. What stops two runs doing the same work? One database. Two writers share it on purpose. Nothing inside Kenfold sees the scheduler's `.pid`, `.dispatched`, `.done`, or `.parked` markers. One worktree per slug stays the lock. This probe used its own podman root and container name, then removed them.
