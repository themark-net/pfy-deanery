# Toolset value ranking for pfy-mentat

## 2026-11-07 catch-up re-rank (entries 137 to 167)

**Why:** 22 entries were cataloged between 2026-10-24 and 2026-11-06 and none was tested or built in. Mark approved a catch-up pass on 2026-11-07. This section ranks entries 137 to 167 by how soon each one closes a named pfy-mentat MVP gap. The 2026-10-06 ranking below is kept as history.

**Read:** `sources/entries/137` to `167`, `docs/HANDOFF-mvp-1104.md`, `docs/HANDOFF-headless-1105.md`, `docs/PENDING-HANDOFF.md`, `docs/build-dropins/skill-discovery.md`, `data/tool_integration_stages.json`, and the Strata upstream repo (README, `docs/STRIX_HALO.md`, `docs/MODELS.md`, `docs/TERMINAL_LAUNCH.md`, release `v0.2.12` asset list).

### MVP gaps used for ranking

| Gap | What is open | Source |
|-----|--------------|--------|
| L | Local inference has one engine (Ollama). The strongest local models that fit nimo (qwen3-coder-next, Qwen3.8-Flash-Next) need llama-server `--no-mmap` or more memory than the Ollama lane allows. MVP item 1 is "Grok plus local inference". | HANDOFF-mvp-1104, 2026-10-06 ranking #1, Entry 153 |
| B | `./pfy build` is not proven bot-usable: the 2026-11-06 trial hit the 3 h timeout and the recheck fix is parked after two pregate FAILs. | progress files 2026-11-06 |
| H2 | Skill and tool discovery has no install gate. The discovery drop-in forbids loading fetched skills because nothing checks them. | skill-discovery drop-in, Entry 148 |
| H1 | harness2 showed no gain and there is no repeatable with/without score to re-measure it or to compare pfy against plain Build (devbot-pfy-trial). | Entry 136, Entry 146 |
| W | Tauri operator window not built on nimo. | HANDOFF-headless-1105 |

No entry in 137 to 167 closes gap B or W. Both are bugs or build work in pfy's own code, the same finding as the 2026-11-04 handoff for G1 to G5.

### Ranking

| # | Entry | Gap | Why it closes it soon | Effort | Stage now |
|---|-------|-----|-----------------------|--------|-----------|
| 1 | **162 Strata** | L | Serves an OpenAI-compatible API on localhost, so pfy's launch smoke and harnesses use it with a base URL change. Ships a packaged `linux-x86_64-hip-halo` engine for gfx1151 (nimo's GPU) and documents Qwen3.6-35B-A3B (our default model) plus compact Qwen3.8-Flash-Next packs (Q2_0 37.6 GB). Installer is home-scoped with `STRATA_DATA_DIR` and `STRATA_BIN_DIR` overrides, no root | S to M | I0 |
| 2 | **148 SkillSpector** | H2 | Offline, CPU-only static scan (`--no-llm`) with a machine-readable recommendation. One command in front of any skill import | S | I0 |
| 3 | **146 skill-up** | H1 | Already staged on nimo. The custom local-command engine can grade any harness that reads a JSON session input, with baselines and repeats | M | I0 |
| 4 | 165 Elephant-Goldfish Model | B (indirect) | Fresh-eyes spec review before a Build lane starts; may cut fail-twice parks. Does not fix the timeout | S | I0 |
| 5 | 140 Chiasmus | B (review) | Call-graph impact for per-file review. Overlaps codebase-memory-mcp, the primary impact source | M | I0 |
| 6 | 161 agentgg | risky-change review | Local SAST pass on trading, deploy and secret diffs. Wiring it changes a security gate, so Tester and Reviewer apply | M | I0 |
| 7 | 137 neatroots | H1 (evals) | Offline rule checks over traces. Needs a trace export from Build or opencode first | M | I0 |
| 8 | 147 HiRoute, 163 magpie | L (routing) | Route cheap turns to the local engine. Only useful after the engine choice in #1 | M | I0 |
| 9 | 138 Hermes Teammates | Hermes interface | Blocked until Hermes is wired as the bot interface | S | I0 |
| 10 | 149 MemPalace, 155 RoBrain | memory | Post-MVP memory slot | M to L | I0 |

**Hold or comparison only:** 139 (overlaps skill-up), 141, 142, 143 (after the window exists), 144 (post-MVP scratch trial), 145, 150 to 152 (Stage-0 FAIL), 153 (does not fit nimo), 154, 156 (AGPL), 157, 158, 159, 160, 164, 166, 167.

### Picked for trials (2026-11-07)

1. Strata (162), next to Ollama on the local-model path: same model, same prompts, both engines, then pfy's launch smoke against Strata.
2. SkillSpector (148): scan every skill already in the repo, then build in an advisory scan command.
3. skill-up (146): grade one small pfy case set with a baseline.

Each trial records its verdict in `data/tool_integration_stages.json`. Results go in `eval/catchup-1107/`.

### Strata, long term

Strata is an MIT local inference engine (C++, HIP, CUDA, Metal, SYCL) by Niko1221, about 41k stars and very active (release `v0.2.12` on 2026-11-07, 0.2.10 to 0.2.12 in five days). It plugs into pfy-mentat as a second engine on the local-model path: pfy already talks to engines through an OpenAI-compatible base URL, so Strata sits beside Ollama without a harness rewrite. Its value for nimo is the packaged gfx1151 engine and its own packs of the models we care about (Qwen3.6-35B-A3B, Qwen3.8-Flash-Next). Risks, all from upstream's own docs: Strix Halo support is marked experimental, DeepSeek V4.1-Flash on Strix Halo runs on Windows only (Linux not yet), the release cadence means pins go stale within days, and the desktop AppImage and updater are out of scope for us (the terminal `strata launch --no-tui` path is the one to use). Speed and quality on nimo are unmeasured until the trial below.


## 2026-10-06 ranking (history)

**Scope:** what to integrate next, assuming **local models only on nimo** (Strix Halo, Ollama about 22 GB edge; `llama-server --no-mmap` edge ≥ 51 GB) and no paid keys besides Grok and Cursor. Active products: Leasegrid, pfy-mentat, Gom Jabbar (jobbar-master), Lotline, Practice Minder.
**Read:** `TOOLS.md`, `data/tool_integration_stages.json`, `data/toolsets.json`, `sources/x-posts.md`, `sources/entries/066–092`, `docs/dogfood/LOCAL-BENCH-*`, `~/DEVELOP/_vendor/*` READMEs. Nothing was installed or run for this ranking.

## Already integrated (not re-recommended)

codebase-memory-mcp (I2, `code-graph` toolset) · LiteLLM (I2 smoke) · Ollama (host runtime) · agent-cage (I3) · write-guard-mcp · Grok CLI + project-process bootstrap (I3) · ponytail, karpathy-guidelines, mattpocock skills (on `skills.paths`) · `/agent-loops` 8-exits port (`orchestration` toolset) · `/hermes-feedback` · Jev / CUA-S1-FORMS decision lane (#230) · OpenContext (`opencontext` toolset) · repowise and kolibri smokes · Laya (trial-ran, not promoted) · local-bench harness (Entries 089–092).

## Ranking

| # | Candidate | Value for pfy-mentat (local-only) | Effort | API key? | Status |
|---|---|---|---|---|---|
| 1 | **llama-server `--no-mmap` lane** (llama.cpp server mode) | Only way to run `qwen3-coder-next` (83.3 % on #230, vs 79.2 % for qwen3.6). Make it a named lane in `pfylib/hedge.py` / `eval-lanes.json` with start/stop + health, not a bench-only script. It also gives atg-framework an OpenAI-compatible target | S–M | No | Built in a bench only (`pipelines/dogfood/local-bench-4/run_nommap_server.sh`). Not a lane |
| 2 | **atg-framework (ATG)** | Typed DAG compile + localized repair for multi-step local loops. First use is a compile bench, then an opt-in `atg` loop kind. See [ATG-FRAMEWORK-EVAL.md](ATG-FRAMEWORK-EVAL.md) | M | No (Ollama / local) | Built and unit-green (35 tests). Live compile unproven. Catalog card stale |
| 3 | **DSPy optimizers on the #230 decision bench** | Tune the prompt / few-shot set for `qwen3.6:35b` on the 48 cases with a held-out split. It may close the gap to coder-next without the 51 GB load. Gom Jabbar already uses DSPy | M | No (`ollama_chat/…` via LiteLLM) | Idea (TOOLS.md A-tier row, not integrated) |
| 4 | **destructive_command_guard** | Guardrail for unattended local workers (`worker-monitor`, OpenCode + Ollama), next to write-guard. That matters more as bots hand bulk work to local models | S | No | Catalog row only (Entry 041) |
| 5 | **opencode-mem** | Persistent memory for the **worker** surface (OpenCode + Ollama), which the Grok-side tools don't cover | S–M | No (local vector DB) | Catalog row only (Entry 049) |
| 6 | **claude-mem** (adapt, not adopt) | Its SQLite FTS5 observation store + session summaries is the best memory design on disk. Port the store pattern into `/hermes-feedback`. Its runtime hooks are Claude-Code specific | M–L | Yes by default (Claude / Gemini / OpenRouter providers). Local only if the OpenRouter base-URL override points at llama-server, which is unverified | Vendored only (`_vendor/claude-mem`, 2026-07-06) |
| 7 | **llama.cpp ngram-mod** speculative decoding | Free decode speedup on repetitive code edits for the local worker. Pairs with #1 | S | No | Catalog row only (Entry 051) |
| 8 | **Bumblebee** | Read-only supply-chain + MCP-config scanner. Cheap cage probe that protects every vendored tool on this list | S | No | Catalog row only (Entry 069) |
| 9 | **OpenLobster** | Go single binary, Ollama / OpenAI-compatible, MCP client, graph memory (file or Neo4j), Telegram and Slack channels. Candidate to replace `openclaw-gateway`, whose 128k-ctx GLM loads keep stalling benches. Ops value, not core | M | No (Ollama provider) | Vendored only (`_vendor/OpenLobster`, 2026-03-27) |
| 10 | **LEANN** | Compressed local RAG over catalog + sources for `catalog-ask`, without a server vector DB | M | No | Catalog row only (Entry 052) |
| 11 | **kanbots** | Kanban fan-out of CLIs into worktrees. Could drive the Build drop-ins in `docs/build-dropins/`. Overlaps `/agent-loops` | M | No | Stage 0 passed (npx). I1 |

### Skip or hold

Graphify, Ix, Axon (CM is primary) · Memvid · MUE-X and Exo (unsafe as runtimes) · asm · claude-codex-settings · MCO (multi-provider review that assumes paid CLIs) · Antigravity-Manager · AgenC · career-ops (Gom Jabbar's optional vendor, not pfy) · `_vendor/openclaw` (actually an iRODS/sssd tree, not the agent) · Kronos, bip39, monero, sssd (unrelated).

## Per-product notes

- **Gom Jabbar:** #3 (DSPy) moves routine identify/fit work to local models (ROADMAP item 7). #6 memory pattern for sticky answers.
- **Leasegrid / Practice Minder / Lotline:** no tool on this list is on their critical path. They are founder-gated (RELEASE / Mark inputs). #4 and #8 protect the Build sessions that work on them.
- **pfy-mentat:** do #1, then #2 (bench), then #3. That order raises local-model quality before adding loop machinery.
