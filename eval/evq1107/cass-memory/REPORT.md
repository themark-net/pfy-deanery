# cass-memory evq1107

Verdict: STAY I0. One synthetic session produced 0 rules. A hand-written playbook put the right rule first on 7 of 8 queries. Token overlap on the same eight texts put the right rule first on 8 of 8. Facts already in this repo were 8 of 8 for a file scan and 0 of 8 inside the playbook. Graded with/without harness cases: 0. Nothing was wired into a gate.

It does not beat a text file plus token overlap, and it does not beat skill-up on gap H1.

The entry was already I0. This probe does not earn I1, I2, or I3. The card stays I0. No TOOLS.md row. No `data/tools.json` row.

## Catalog comparison

Same job: a procedural playbook built from session history, offline, for gap H1 (a repeatable with/without score, plus memory and context). H1 is that harness2 showed no gain and there is no score to re-measure it, or to compare pfy with a plain Build run. The 2026-11-07 ranking gives that score to skill-up. cass-memory is entry 108, older than that ranking. The ranking's memory row is MemPalace and RoBrain, post-MVP, and MemPalace's card already names a bake-off against 108. This lane is the cass-memory side of that question. It is not a MemPalace install.

`eval/evq1107/cass-memory/probe.py` reads `uses`, `features`, and tags for the words memory, playbook, procedural, and session. 26 other cards matched. Batch-1 under `eval/ev1107/` has no cass-memory trial. `eval/catchup-1107/skill-up/VERDICT` is PROMOTE I3, both arms 5/5, delta 0. skillspector and strata in that directory are other jobs.

| Card | Stage | What it already covers | How cass-memory compares |
| --- | --- | --- | --- |
| skill-up | I3 | With-skill vs no-skill grade. Catch-up: 5 cases, both arms pass, delta 0. | This probe scored 0 cases. It does not close H1. |
| harness2 | I1 | The trial H1 is about. Its own gain was 0. | cm does not re-measure that trial. |
| Harness Score | I0 | Offline grade of harness files, including context files. | A scorer, not a playbook. |
| eval-harness (pfy) | I1 | First-party structural ladder. | Already the structural score. cm adds 0. |
| neatroots | I2 | Offline rules on saved traces. | Not a playbook. This probe fed it no trace. |
| codebase-memory-mcp | I2 | Primary code-graph MCP. | cm saw 0 of 8 repo facts until they were typed in as rules. |
| repowise | I2 | Context packing. Overlaps codebase-memory. | Packs the repo. cm does not read the repo. |
| opencode-mem | I1 | Memory plugin for the OpenCode worker. Local. | Same job class. Not run here. cm did not beat a text file. |
| OpenContext | I1 | Note store. Its probe was 8/8 copied notes, 0/8 repo facts, 0 graded cases. | Same shape. cm's hand playbook was 7/8 top-1 after a copy, and 0/8 on repo facts. |
| LEANN | I1 | Compressed RAG. Not our code memory. | A passage index. cm is a bullet list. |
| Memvid | I1 | Video-backed memory. No current job. | Different store. Not run. |
| MemPalace | I0 | Verbatim local memory. Post-MVP bake-off against 108. | This probe did not beat a file plus token overlap. |
| RoBrain | I0 | Decision memory. Needs Postgres. | Different store. Not run. |
| Hermes Agent (feedback loops) | I1 | Feedback pattern already ported as a skill. | The pattern is already in-tree. cm is not that skill. |
| Agent Beacon | I0 | Copy a session, store a typed lesson. Scoring calls hosted Jev. | cm reflect also stopped without a local model CLI. 0 rules. |
| imcodes | I0 | Final-answer memory. Reference only. | Not an install. |
| Graphify, Axon, OpenLore, Tree-sitter Analyzer | I0 or I1 | Review graphs. The word memory matched. | Not a playbook. |
| Chroma (or LanceDB) | I0 | Vector store. Code memory is already chosen. | cm stayed on keyword mode. No embedding download. |
| MUE-X | I1 | Unsafe runtime. The word memory matched. | Not a store we would turn on. |
| Auto-Company | I1 | Persona patterns. The word memory matched. | Not this CLI. |
| Grok CLI bootstrap | I3 | Operator sessions. The word memory matched. | The surface that already runs. cm does not replace it. |
| agentplay, Open Steps | I0 | The word session matched. | Not memory stores. |
| token overlap on the 8 rules | in this probe | Scores the same rule texts the playbook holds. | 8/8 top-1. cm was 7/8. |
| file scan of this worktree | in this repo | Finds the 8 known needles under docs, data/stages, scripts, sources/entries, and AGENTS.md. | 8/8. cm playbook hits on those needles: 0/8. |

## Pins

| Item | Value |
| --- | --- |
| Entry commit prefix | `229a312b696a` |
| Tag v0.5.0 | Annotated tag peeled to `229a312b696aa347d1e2c491d3d466c925716dc0` (published 2026-10-08). Matches the prefix. |
| Asset | `cass-memory-linux-x64` from the v0.5.0 release. 124601824 bytes. |
| sha256 | `06e1563881f8bb1225cf7036068252ef210f242704a27f8ce32518b822181bd7`. Matches the upstream `.sha256` asset and `CM_V050_SHA256` in `examples/x-intake-local/smoke_106_108.py`. |
| Version that ran | `0.5.0` |
| License | MIT plus an OpenAI/Anthropic rider. GitHub SPDX is NOASSERTION. Mark is not a restricted party. This lane did not call an OpenAI or Anthropic model. |
| Install | `~/.cache/pfy/tools/cass-memory/bin/cass-memory-linux-x64`. Not committed. |

`HOME`, `XDG_CONFIG_HOME`, `XDG_CACHE_HOME`, `XDG_DATA_HOME`, and `TMPDIR` for every `cm` child pointed under `~/.cache/pfy/tools/cass-memory/probe-home`. `PATH` started with a stub directory for `claude`, `codex`, `cursor`, `ollama`, `cass`, `grok`, `aider`, and `opencode`. The child env did not inherit the parent env. The real `~/.cass-memory`, `~/.cache/cass-memory`, and `~/.cass` were absent before the probe and after it.

## Commands

```bash
curl -fsSL -o ~/.cache/pfy/tools/cass-memory/bin/cass-memory-linux-x64 \
  https://github.com/Dicklesworthstone/cass_memory_system/releases/download/v0.5.0/cass-memory-linux-x64
curl -fsSL -o ~/.cache/pfy/tools/cass-memory/bin/cass-memory-linux-x64.sha256 \
  https://github.com/Dicklesworthstone/cass_memory_system/releases/download/v0.5.0/cass-memory-linux-x64.sha256
sha256sum -c ~/.cache/pfy/tools/cass-memory/bin/cass-memory-linux-x64.sha256
python3 eval/evq1107/cass-memory/probe.py
```

The probe writes `eval/evq1107/cass-memory/results.json`. Rules and the two-line session text live in `eval/evq1107/cass-memory/rules.json`. The session is not a real agent log. `cm reflect --session` ran inside `unshare -rn`. `cm doctor --fix`, `cm hook`, `cm update`, `cm diary`, `cm validate`, `cm audit`, and `cm serve` were not run. No model lock was taken.

`python3 -m unittest tests.test_cass_memory_probe` drives the same script with a stub `cm` in a temp directory. No network and no real binary. A context reply that is not JSON is a miss, and the other seven queries still score. A third harmful mark that still leaves the bullet in `context` is not counted as a drop. A sha256 mismatch does not execute the file.

## Numbers

| Check | Result |
| --- | --- |
| `cm --version` | 0.5.0 |
| sha256 | match |
| `cm init --json` | exit 0, cassAvailable false |
| `cm doctor --json` | exit 0, 147.2 ms, overall unhealthy, cass missing |
| `cm reflect --dry-run` | exit 0, added 0 bullets |
| `cm reflect --session` on the two-line fixture | exit 0, 124.8 ms, 0 bullets, sha256 text not stored |
| claude stub during that reflect | 3 invocations, all exit 2, no real claude |
| hand-added rules | 8 plus 1 distractor |
| token overlap top-1 | 8/8 |
| `cm context` top-1 | 7/8 |
| `cm context` recall (right rule anywhere in the list) | 8/8 |
| top-1 delta (cm minus overlap) | -1 |
| second pass agreement | 8/8, including the same miss |
| distractor leaked into the 8 queries | 0 |
| three harmful marks on the distractor | candidate, candidate, deprecated |
| distractor still in the next context | no |
| `cm usage` total | 0 |
| repo needles in the tree | 8/8 |
| repo needles in returned bullets | 0/8 |
| semantic mode | keyword |
| graded with/without cases | 0 |
| wall clock | 6440.8 ms |
| real home directories changed | no |

The miss was the auth.json rule. The query was "which secret file named auth.json must stay uncommitted". `cm context` returned three bullets. The trading rule was first (relevance 1.142), the auth.json rule was second (1.097), and the Gom Jabbar spelling rule was third (0.714). Token overlap, which does not stem "stays" into "stay", still ranked the auth.json rule first. Those scores are the `auth` row in `results.json`.

History snippets were empty. `cass` is not installed. The reflect stderr said provider anthropic is not configured and fell back to a local CLI. The stub named `claude` caught that call. No API key was set.

## Gates

Value (3 of 4 needed for I3):

1. Gap fill: no. H1 needs a with/without score. skill-up already emits one (5/5 both arms, delta 0). This run emitted 0 graded cases. On the playbook texts, overlap was 8/8 and cm was 7/8. Facts already in the repo: file scan 8/8, cm 0/8.
2. Operator leverage: no. Reflect extracted 0 rules in 124.8 ms and tried to exec `claude`. Typing the eight rules in by hand did not beat token overlap. AGENTS.md and the stage cards already hold the repo facts.
3. Evidence: yes. The tag commit matches the entry prefix. The sha256 matches the release asset. `results.json` records the exits. The commands above reproduce the run.
4. Blast radius: no, for an unattended lane. The binary is 124601824 bytes, over the 50 MB I2 copy limit, and it is not in the repo. The license rider bars OpenAI and Anthropic use. Default `provider` is anthropic. With no key, `cm reflect` execs `claude` from `PATH`. That is a paid-CLI footgun. Spend stayed 0 only because the stub blocked it. It did not become the product runtime.

Value score: 1 of 4.

Modularity (all 4, required before an in-repo copy):

1. Local code needed: yes. The auth.json rank miss, and the claude fallback, showed up when the binary ran.
2. Bounded surface: no. One binary shells out to `cass` and `claude`, and `cm doctor --fix` wants a separate embedding download. `serve`, `hook`, and `update` are in the same CLI.
3. Isolatable: yes. The cache held the binary and the playbook. The real home directories stayed absent.
4. Reversible: yes. Deleting the cache leaves the pin and this entry. No repo file was rewritten by `cm`.

Modularity fails the bounded surface. The binary is also over 50 MB, so the lightweight I2 copy gate fails. The result is not ambiguous, and it does not help H1, so the card stays I0. I3 would also need a repeatable pipeline script and `self_pipeline` evidence. The card's uses and features do not match the pipeline role tokens. This lane wires nothing.

## Risks

| Risk | How it fails | Recovery |
| --- | --- | --- |
| Claude fallback | `cm reflect` with no API key execs `claude` on `PATH`. A real binary could spend or send the session text. | Child `PATH` stubs `claude` and the other local CLIs. `unshare -rn` drops the network. Record 0 rules. Do not set a key. |
| Missing cass | Session discovery and history snippets stay empty. | Expected. Do not install cass in this lane. History score stays 0. |
| sha256 mismatch | A different binary would still be executed. | The probe checks the pin and does not exec on a mismatch. The stub test covers that. |
| Context stdout is not JSON | A parser that scans raw text could count a marker from stderr. | That query is a miss. Later queries still score. The stub puts `CMK_PIN` on stderr only. |
| newState says deprecated while context still returns the bullet | A score that trusts `newState` alone would hide a live rule. | The drop is decided from the next `context` list. The stub test keeps the bullet and expects `removed_from_context` false. |
| Keyword top-1 | Shared stems ("stays", "named") rank a distractor above the literal rule. | Keep the hand file. Do not replace it with the playbook. Overlap was 8/8 on this set. |
| doctor --fix | Downloads the xenova embedding model. | Not run. Semantic mode stayed keyword. |
| Real home writes | A run without a redirected HOME writes `~/.cass-memory`. | Subprocesses used the cache home and XDG dirs. The real directories stayed absent. |
| License rider | Use on an OpenAI or Anthropic lane can end the license. | This lane is Grok, offline, no key. Do not point reflect at those providers. |
| Large binary | 124601824 bytes in cache. | Do not commit it. Do not call it an I2 tree copy. |

## Next gate

Stay I0. Do not wire cass-memory into pregate, CI, or `./pfy`. Re-open only if a later pin extracts at least one rule from the two-line session in `rules.json` with no network, no `claude` binary, and no API key, and top-1 on these 8 queries beats token overlap. An in-repo I2 copy also needs a binary under 50 MB. That ticket grills wiring first.

## Five questions (if this tool ran in our pipeline)

1. What triggers it? Nothing in `./pfy` pregate, CI, or the lane scheduler starts `cm`. An operator would run `cm context` by hand. This lane adds no trigger. The rolling scheduler started only this eval.
2. What does it do, and which services does it read and write? It reads and writes a playbook, `config.json`, and `usage.jsonl` under the redirected `XDG_DATA_HOME/cass-memory`. `cm reflect --session` reads one local jsonl file. With the default provider and no key it execs a local `claude`. It does not read this repo unless a person types a rule in. No hosted account was used. `cm usage` total was 0.
3. What does it trigger next? Nothing. Context prints JSON. It does not start `catalog_check`, pregate, or a harness grade. Suggested `cass search` lines were not executed.
4. Where does a human re-enter? A person chooses which rules to add, whether to install cass, and whether to set a provider. Our re-entry stays the `tmp/evq` markers, `tmp/STOP`, and Mark. No key was set.
5. What stops two runs doing the same work? One playbook file per `XDG_DATA_HOME`. Two writers can clobber that file. cm does not see the scheduler's `.pid`, `.dispatched`, `.done`, or `.parked` markers. One worktree per slug stays the lock. This probe used its own home under the cache.
