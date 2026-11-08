# robrain evq1107

Verdict: STAY I0. Offline VetoBench at the pinned commit matched its published recall (1.00 with files known, 0.70 without). On 10 re-proposals taken from this repo's ADRs, the same ranker put the veto row in the top 5 on 8 of 10 when no file was in scope, and on 10 of 10 when the ADR path was in scope. Token overlap on the decision, rationale, and rejected text put the veto row in the top 5 on 10 of 10, and first on 8 of 10. An empty context surfaces 0 of 10. Postgres + pgvector was SKIPPED. Nothing was wired into a gate.

It does not beat the ADR files already in this repo, and it does not beat skill-up on gap H1.

The card was already I0. This probe does not earn I1, I2, or I3. No TOOLS.md row. No `data/tools.json` row.

## Catalog comparison

The job is decision memory: store a rejected option and surface it before a later task repeats it. The lane gap is H1 (a repeatable with/without score, plus memory and context). H1 is that harness2 showed no gain and there is no score to re-measure it, or to compare pfy with a plain Build run. The 2026-11-07 ranking gives that score to skill-up. The same ranking puts MemPalace and RoBrain on a post-MVP memory row, not on H1.

`eval/evq1107/robrain/probe.py` reads `uses`, `features`, and tags for the words memory, veto, pgvector, postgres, embedding, and embeddings. 16 other cards matched. The list is `cards` in `results.json`. Batch-1 under `eval/ev1107/` has no RoBrain trial. `eval/catchup-1107/` has no RoBrain trial. skill-up, harness2, neatroots, and eval-harness do not match those words. ai-memory does not either (its uses line is a wiki and a mailbox). Their stages are in the table.

| Card | Stage | What it already covers | How RoBrain compares |
| --- | --- | --- | --- |
| skill-up | I3 | With-skill vs no-skill grade. Catch-up verdict: both arms 5/5, delta 0. | This probe scored 0 harness cases. It does not close H1. |
| harness2 | I1 | The trial H1 is about. Local edit trial on the 48-case set. | This probe does not re-measure that trial. |
| eval-harness (pfy) | I1 | First-party structural ladder. | Already the structural score. This probe adds a veto recall number, not a harness delta. |
| neatroots | I2 | Offline rules on saved traces. | Not a decision store. This probe fed it no trace. |
| cass-memory | I0 | Playbook search. Its probe was top-1 7/8 against token overlap 8/8. | Same shape of loss. Different text. Not a MemPalace bake-off. |
| MemPalace | I1 | Verbatim excerpts. Top-1 8/8 against a word walk 6/8. Stayed I1. Work tree 68560448 bytes, MiniLM onnx 90387606 bytes. | A different question. It beat a word walk on excerpts it had mined. This ranker lost to ADR text on rejected options. |
| ai-memory | I1 | Pasted search 8/8, repo facts 0/8, claim-once 8/8. The word scan misses this card. | A wiki and a mailbox. It does not rank a rejected option that is already in an ADR. |
| opencode-mem | I2 | Restart search recalled 8/8 salts that are not in the repo. rg found 0/8. A notes file found the same 8. | Session facts that were never committed. The vetoes in this probe are already in `docs/adr`. |
| Kenfold | I1 | Stdio memory for several CLIs. Recall 8/8 copied tokens, 0/8 facts already in this repo. The probe started rootless Postgres and pgvector. Graded with/without cases: 0. | A paste between agents. It missed facts already in the repo. This probe's vetoes are already in `docs/adr`, and Postgres stayed skipped. |
| OpenContext | I1 | Note store. Its probe was 8/8 copied notes and 0/8 repo facts. | A note file. This probe did not beat ADR text. |
| LEANN | I1 | Compressed RAG. Not our code memory. | A passage index. This probe did not build one. |
| Memvid | I1 | Video-backed memory. No current job. | Different store. Not run. |
| codebase-memory-mcp | I2 | Primary code-graph MCP. | Code structure, not rejected decisions. |
| repowise | I2 | Context packing. Overlaps codebase-memory. | Packs the repo. It does not rank vetoes. |
| Hermes Agent (feedback loops) | I1 | Feedback pattern already ported as a skill. | The pattern is already in-tree. The Hermes provider was not installed. |
| Chroma (or LanceDB) | I0 | Vector store. Code memory is already chosen. | RoBrain's live stack is Postgres + pgvector, and that stack was skipped. |
| Graphify | I0 | Reference graph. Not the code memory we run. | Not a veto store. |
| Agent Beacon | I0 | Copy a session, store a typed lesson. | Different store. Not run. |
| imcodes | I0 | Final-answer memory. Reference only. | Not an install. |
| Grok CLI bootstrap | I3 | Operator sessions. The word memory matched. | The surface that already runs. RoBrain does not replace it. |
| Auto-Company | I1 | Persona patterns. The word memory matched. | Not this bench. |
| MUE-X | I1 | Unsafe runtime. The word memory matched. | Not a store we would turn on. |
| token overlap on the 10 ADR rows | in this probe | Scores the same decision and rejected text. | 10/10 in the top 5, 8/10 at rank 1. RoBrain no-files was 8/10 and 5/10. |
| empty context | the `none` condition | No decision text in front of the task. | 0/10. Retrieval beats nothing. It does not beat the files. |

## Pins

| Item | Value |
| --- | --- |
| Entry commit | `ac53011016e5f7dd42bae9c00c1a9b7d207a68b8` (2026-10-29). Checkout HEAD matches. |
| Version | Root package `2.5.0`. `@robrain/vetobench` `0.1.0`. `@robrain/shared` `2.5.0`. |
| License | Apache-2.0, first line of `LICENSE`. |
| Package manager | `pnpm@10.33.3`, from the root `packageManager` field. |
| Node | v22.23.0. The `eve` package warns it wants Node >= 24. This lane did not build `eve`. |
| Install | `~/.cache/pfy/tools/robrain/src/robrain`. Not committed. |
| Checkout bytes | 304388021, from `results.json`. |
| `node_modules` bytes | 295415802. `@robrain/vetobench` depends on `mem0ai`, so the frozen install pulls it. The offline bench does not import it. |
| Source without `.git` or `node_modules` | 6767744 bytes. |
| Upstream default suite | exit 0, 46.1 ms, 10 rows, recall 1.00 with files known and 0.70 without, offline, PASS. |
| Upstream lifecycle suite | exit 0, 34.6 ms, 4 rows, recall 1.00 and 1.00, offline, PASS. |
| ADR rank call | 33.7 ms. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, `TMPDIR`, and `COREPACK_HOME` for the install pointed under `~/.cache/pfy/tools/robrain/`. The probe child env was a fresh map with those homes under `probe-home`, plus `PATH` limited to the node directory and `/usr/bin:/bin`. The parent env was not inherited. No API key was set. `~/.robrain` and `~/.mem0` were absent before the probe and after it (`home_unchanged` true). `~/.npm` was not touched (mtime 2026-08-23).

## Commands

```bash
git clone --filter=blob:none https://github.com/adelinamart/robrain.git \
  ~/.cache/pfy/tools/robrain/src/robrain
git -C ~/.cache/pfy/tools/robrain/src/robrain fetch --depth 1 origin ac53011016e5f7dd42bae9c00c1a9b7d207a68b8
git -C ~/.cache/pfy/tools/robrain/src/robrain checkout --detach ac53011016e5f7dd42bae9c00c1a9b7d207a68b8
corepack prepare pnpm@10.33.3 --activate
corepack pnpm install --frozen-lockfile --filter "@robrain/vetobench..." --ignore-scripts
corepack pnpm --filter @robrain/shared exec tsc -p tsconfig.publish.json
corepack pnpm --filter @robrain/vetobench exec tsc -p tsconfig.json
python3 eval/evq1107/robrain/probe.py
```

The probe writes `eval/evq1107/robrain/results.json`. The corpus is 16 shortened ADR rows in `corpus.json`. The 10 tasks are in `scenarios.json`. `historical_relevance` is 0.5 on every row and `reviewed_at` is set, so those two signals do not separate ranks. Rank comes from `vetoRank` in the built `dist/adapters.js` (hash embedder, 5-signal composite, top 5). Token overlap uses the same token rule as that embedder (lowercase, letters and digits, length greater than 2) and scores `|query tokens ∩ doc tokens| / |query tokens|`.

`python3 -m unittest tests.test_robrain_probe` drives the same script with a stub `node` in a temp directory. No network and no real VetoBench build. A rank of 9 is 0 hits, and a rank of 1 is 10 hits. Non-JSON rank output is not a score. A recall line of 0.40 does not pass the pin check. A missing `dist/run.js` skips the node calls. The stub's `podman` is not executed.

Not run: `robrain up`, `robrain install`, `robrain init-project`, `--live`, the Mem0 adapter, the e2e extractor, and `docker compose`. Podman 5.7.0 is installed and rootless. It was not started. The compose file uses `pgvector/pgvector:pg16` and a required `POSTGRES_PASSWORD`. Perception reads `.env` and embeds at 1536 dimensions. That needs `OPENAI_API_KEY` or a local OpenAI-compatible server. This lane takes no key and no model lock, so that half is SKIPPED.

## Numbers

| Check | Result |
| --- | --- |
| Pin HEAD | match |
| Default suite recall@5 | 1.00 with files, 0.70 without |
| Lifecycle suite recall@5 | 1.00 / 1.00 |
| Corpus rows | 16 |
| Scenarios | 10 (6 direct, 4 implicit) |
| Empty context, veto in the prompt | 0/10 |
| Flat dump of every row | 10/10, by construction |
| RoBrain, files known, top 5 | 10/10, rank 1 on 10/10 |
| RoBrain, no files, top 5 | 8/10, rank 1 on 5/10 |
| Token overlap, decision + rationale, no files, top 5 | 10/10, rank 1 on 6/10 |
| Token overlap, ADR text including rejected lines, no files, top 5 | 10/10, rank 1 on 8/10 |
| RoBrain no-files minus ADR overlap | -2 |
| `beats_adr_text` | false |
| Graded with/without harness cases | 0 |
| Postgres + pgvector | SKIPPED |
| Probe wall | 1190.1 ms (includes the checkout byte walk) |
| Real home directories changed | no |

No-files ranks (`vetoRank`, then decision-text overlap, then ADR-text overlap):

| id | trap | veto | RoBrain | decision overlap | ADR overlap |
| --- | --- | --- | ---: | ---: | ---: |
| s01 | direct | d010 AgenC as primary | 4 | 1 | 1 |
| s02 | implicit | d010 dual primary | 1 | 2 | 2 |
| s03 | direct | d003 subtree everything | 1 | 1 | 1 |
| s04 | implicit | d003 floating main | 10 | 1 | 1 |
| s05 | direct | d002 Continue.dev | 1 | 1 | 1 |
| s06 | direct | d005 Confluence | 7 | 2 | 1 |
| s07 | implicit | d007 host-only write-guard | 2 | 2 | 2 |
| s08 | direct | d009 gstack embed | 1 | 2 | 1 |
| s09 | implicit | d011 third runtime | 2 | 1 | 1 |
| s10 | direct | d014 vLLM default | 1 | 1 | 1 |

The two misses are s04 (rank 10) and s06 (rank 7). Both are July rows. Recency half-life is 30 days and `as_of` is 2026-11-07, so an old row loses to newer rows when the hash buckets collide. The rejected name for s06 (Confluence) is only on the rejected line, which `vetoRank` does not embed. It embeds `decision` plus `rationale`. Putting the ADR path in `files_in_scope` moves both misses to rank 1. That is the file-overlap rescue the upstream README describes. A task that has not opened the ADR does not get that rescue.

The files-known token-overlap arm adds 1.0 when the scenario names that row's ADR path. Its 10/10 is by construction. The no-files column is the comparison.

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: no. The rejected options already live in `docs/adr`. Token overlap on that text is 10/10. skill-up already owns the H1 score. codebase-memory-mcp is the code memory.
2. Operator leverage: no. The ranker is slower to install than reading the ADR, and the Postgres stack cannot run on this lane.
3. Evidence: yes. The pinned offline bench ran, and this probe reruns it.
4. Blast radius: no. `robrain up` writes `~/.robrain`, `init-project` writes `AGENTS.md`, and the default providers are hosted. The runnable install is 304388021 bytes. License Apache-2.0 is fine. Turning the stack on is not.

Value score: 1 of 4.

Modularity (all 4 for an I2 copy):

1. Local code needed: yes. The docs do not give this repo's 8/10.
2. Bounded surface: weak. The unit scored is `packages/vetobench`. The frozen install still fetches `mem0ai` and 375 packages.
3. Isolatable: yes. The checkout sits under `~/.cache/pfy/tools/robrain/`.
4. Reversible: yes. Deleting the cache leaves the pin and the entry.

I2 also needs a measured win and a light copy. There is no win. The running tree is over 50 MB because of `node_modules`. Stay I0.

## Risks

| Risk | How it fails | How we recover |
| --- | --- | --- |
| Stale veto | A superseded rejection still ranks and blocks a later valid approach | The upstream lifecycle suite scored 1.00 / 1.00. This corpus has no superseded row. A later trial has to add one before anyone trusts a block. |
| Hash miss on an old row | s04 landed at rank 10 and s06 at rank 7, so the warning never enters the top 5 | Read the ADR. Token overlap found both. Do not replace the files with this ranker. |
| Writes outside the scratch home | `up`, `install`, and `init-project` write `~/.robrain` and editor rules | This lane ran none of them. The probe's child HOME is under the cache. The real home signature did not change. |
| Key or cloud call | Default extraction is Anthropic and default embeddings are OpenAI. Cloud mode is Rory Plans. | The child env is clean. `--live` is refused in the probe. Postgres stays skipped until a lane allows a local embedding server and the model lock. |
| Fat install treated as a small library | `mem0ai` pulls the tree to 295415802 bytes of `node_modules` | Do not copy it into the repo. A missing `dist/run.js` records SKIPPED instead of a fake 1.00. |

## Next gate

Stay I0. Do not wire a gate. Do not add a TOOLS.md row. Re-open only if a later pin beats ADR token overlap on these 10 tasks with no files in scope, with no API key and no local model, and the runnable tree is under 50 MB.

## How this tool would run in the pipeline

1. What triggers it? Nothing today. A later trial would be a manual probe on a named corpus, not a commit hook.
2. What does it do, and which services does it read and write? The offline bench reads a JSON corpus and writes a recall number. The self-hosted stack would read and write a local Postgres volume and call an embedding endpoint. This lane did not start that stack.
3. What does it trigger next? Nothing. No gate, no smoke target, no skill.
4. Where does a human re-enter? Before any real-home install, before any key, and before `init-project`, which writes project rules.
5. What stops two runs doing the same work? The offline numbers are deterministic for a pin and a corpus. A Postgres trial would need its own scratch volume so two lanes do not share `~/.robrain`.
