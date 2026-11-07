# Master Tools Catalog

This file contains the detailed, living table of evaluated local LLM development tools. Each entry includes scores per stage, overall tier, key attributes/tags, GitHub link, and integration notes especially relevant to Grok CLI, MCP code memory, DSPy/LiteLLM patterns, and continuous pipelines.

**How to read scores**: See CATEGORIZATION.md + [docs/evaluation-framework.md](docs/evaluation-framework.md). Mix of public docs and **lab receipts** (`pipelines/smoke/*`, `make eval-v02`). Cluster scores: [docs/scoring-summary.md](docs/scoring-summary.md). Operator default: **Grok CLI + agent-cage** (not AgenC — ADR-0010).

**Company systems** use a separate rubric: [docs/evaluation/autonomous-ai-companies-rubric.md](docs/evaluation/autonomous-ai-companies-rubric.md) (C1–C6 dimensions).

**Legend (standard tools)**:
- **S1**: Stage 1 Core LLM/Agent Compatibility (weight 35%)
- **S2**: Stage 2 Perf/Efficiency (25%)
- **S3**: Stage 3 Pipeline/Extensibility (25%)
- **S4**: Stage 4 Ecosystem (15%)
- **Overall**: Weighted 0-100

## Active Catalog

| Tool | Primary Cat | GitHub | S1 | S2 | S3 | S4 | Overall | Tier | Key Tags | Integration Notes / Grok CLI / MCP |
|------|-------------|--------|----|----|----|----|---------|------|----------|-------------------------------------|
| **Grok CLI bootstrap** | Pipeline & CI/CD Components | this repo (`bootstrap/grok-cli/`) | 95 | 90 | 98 | 90 | 94 | S | #grok-cli #mcp-compatible #code-memory #pipeline #local-first | **Primary operator env (ADR-0002).** `install.sh` + skills + optional codebase-memory MCP. **Cage path:** `make cage-grok` / `cage-grok-run` / `cage-grok-resume`. Env check: `python3 bootstrap/setup-local-agent-env.py`. |
| **project-process bootstrap** | Pipeline & CI/CD Components | this repo (`bootstrap/project-process/`) | 92 | 95 | 96 | 80 | 92 | S | #grok-cli #pipeline #local-first #agentic | **First-party process kit.** Scaffolds DESIGN + multi-file ADR (rejected alternatives) + TODO + open questions + AGENTS into any repo via `init.sh` / `/project-process`. Evaluation (2026-07): light markdown framework **sufficient**; optional later `adr-tools`; do not replace with heavy SaaS by default. See bootstrap/project-process/README.md + evaluation.md. |
| **AgenC** | Coding & Dev Agents | https://github.com/tetsuo-ai/agenc-core | 78 | 70 | 88 | 82 | 78 | B | #coding-agent #terminal #daemon #mcp-compatible #watch | **Reference only — not primary ([ADR-0010](docs/adr/0010-reject-agenc-as-primary-runtime.md)).** Daemon host agent; install `get.agenc.ag` / `@tetsuo-ai/agenc`. Trial 2026-07-12: TUI approval UX unfit vs Grok Build/Claude/OpenCode; default remote login ≠ Grok Build sub. **Watch:** web console, marketplace-style jobs — re-create gaps only if scored. Optional re-eval scripts under `bootstrap/agenc/` (demoted). Prefer **Grok CLI** + **agent-cage**. |
| **agent-cage (PNNL)** | Pipeline & CI/CD Components | https://github.com/pnnl/agent-cage | 94 | 86 | 99 | 85 | 92 | S | #docker #sandbox #mcp-compatible #harness #pipeline #local-first | **PRIMARY container harness + Grok Build operator path.** Overlay: `make cage-grok` (image, auth import, workspace sync, filesystem MCP, session resume T-0047, net smoke). Policy `coding-agent-grok` must allow xAI CLI hosts. Pin `ea0cdb3…`. Wrapper: `harness/agent-cage/`. |
| **adr-tools** (optional) | Pipeline & CI/CD Components | https://github.com/npryce/adr-tools | 70 | 90 | 75 | 85 | 78 | B | #pipeline #local-first #I1 | Classic CLI optional; skills default. Companion: [docs/ops/adr-tools-companion.md](docs/ops/adr-tools-companion.md). No bootstrap hard dep. |
| **codebase-memory-mcp** | Memory & RAG Systems | https://github.com/DeusData/codebase-memory-mcp | 92 | 88 | 95 | 85 | 91 | S | #mcp-compatible #code-memory #local-first #rag | **Primary** code-graph MCP for Grok (ADR-0002). Bootstrap `--with-codebase-memory`. Pin `ee68144`. **Smoke:** `make smoke-codebase-memory`. Decision vs Graphify: [docs/evaluation/codebase-memory-vs-graphify.md](docs/evaluation/codebase-memory-vs-graphify.md). **Implementation:** `code-graph` toolset (`./pfy toolset plan code-graph --harness <h>`; ADR-0017). |
| **Graphify** | Memory & RAG Systems | https://github.com/Graphify-Labs/graphify | 85 | 72 | 78 | 88 | 80 | B | #code-memory #graph #tree-sitter #mcp-compatible #local-first | **X Entry 017.** Tree-sitter explicit code graph; confidence-labeled edges. **Not integrated** — catalog reference only. Overlaps CM + repowise; primary remains codebase-memory-mcp. Re-open if cage smoke + S-tier head-to-head. |
| **LiteLLM** | Proxy & Routing | https://github.com/BerriAI/litellm | 95 | 85 | 98 | 90 | 93 | S | #litellm-ready #openai-shim #grok-cli #multi-llm #proxy | Critical unification layer. Route Grok API + local Ollama/MLX + fallbacks in one client. Excellent for agent loops. Native MCP? Easy to wrap. Docker ready. Top priority for any hybrid pipeline. |
| **Ollama** | Inference & Serving | https://github.com/ollama/ollama | 90 | 88 | 95 | 95 | 92 | S | #local-first #consumer-hw #openai-shim #tool-calling #apple-silicon #nvidia | Default local backend. Simple `ollama run` + REST API. Tool calling improving rapidly. Perfect entry for Grok CLI (set base_url). Strong community. MCP memory can be layered on top via custom tools or embeddings. |
| **Laguna S 2.1** | Inference & Serving | https://huggingface.co/poolside/Laguna-S-2.1 | 92 | 85 | 95 | 92 | 91 | S | #moe #agentic-coding #open-weights #1m-context #local-first #gguf #mlx | **X Entry 073.** Poolside 118B total / 8B active MoE, 1M context, thinking modes. OpenMDW-1.1. Strong Terminal-Bench / DeepSWE scores. Day-one llama.cpp, Ollama, vLLM, SGLang, TRT-LLM, GGUF, MLX, DFlash. High priority for local/hybrid coding agents. |
| **Kolibri-1** | Inference & Serving | https://huggingface.co/Aleph-Alpha/Kolibri-1 | 78 | 62 | 75 | 70 | 72 | B | #moe #reasoning #tool-calling #german #open-weights #1m-context #vllm | **X Entry 085.** Aleph Alpha 78B total / 3.46B active MoE, German+English, 262k native (1M extended), `reasoning_effort` none–high, Apache-2.0. FP8 ~78 GB needs vLLM + `aleph-alpha-inference` on >=2x A100 80GB / 1x H200. Stock llama.cpp/Ollama: no `kolibri1` support yet; community GGUF needs a patch. **nimo: I0, smoke pending** (`make smoke-kolibri1`, examples/kolibri1-llamacpp). Initial public-docs scores only. |
| **colibri** | Inference & Serving | https://github.com/JustVugg/colibri | 92 | 78 | 85 | 88 | 86 | A | #inference-engine #moe #cpu-only #low-ram #openai-shim #local-first | Extreme low-resource MoE (GLM-5.2 class) via disk-streamed experts. Pure C, OpenAI serve mode. **X Entry 003.** Pin only; no weights in-repo. Test serve+LiteLLM inside agent-cage when adopted. |
| **Continue.dev** | Coding & Dev Agents | https://github.com/continuedev/continue | 92 | 80 | 92 | 88 | 90 | S | #ide-integration #coding-agent #local-first #tool-calling #vs code | Best-in-class IDE surface for local models. Autocomplete + chat + edit with codebase context. Can call tools. High synergy with MCP code memory (index repo symbols). GitHub Actions integration possible for CI evals. |
| **Aider** | Coding & Dev Agents | https://github.com/paul-gauthier/aider | 88 | 82 | 85 | 90 | 87 | A | #terminal #git-native #coding-agent #local-first #headless | Excellent terminal/git-aware coding agent. Works great with Ollama. Strong at iterative editing. Easy to script in pipelines. Lower IDE friction than Continue for some workflows. Good MCP target (repo as context). |
| **DSPy** | Agent Frameworks & Orchestration | https://github.com/stanfordnlp/dspy | 85 | 75 | 90 | 85 | 85 | A | #agentic #optimizer #pipeline #litellm-ready #reasoning | Systematic programming of LM pipelines. Optimizers (BootstrapFewShot, MIPRO) dramatically improve reliability. Pairs perfectly with LiteLLM for local + Grok. High value for gom-jobbar style agents. MCP memory can feed into DSPy modules. |
| **llama.cpp** (server mode) | Inference & Serving | https://github.com/ggerganov/llama.cpp | 85 | 95 | 80 | 85 | 88 | A | #high-perf #quantized #gguf #openai-shim #cpu-gpu | Ultimate performance/quantization control. GGUF ecosystem is massive. Server has OpenAI compat. Slightly more setup than Ollama but unmatched speed/footprint on consumer HW. Good base for custom agents. |
| **MLX + MLX-LM** | Inference & Serving | https://github.com/ml-explore/mlx (mlx-lm) | 80 | 92 | 78 | 80 | 82 | A | #apple-silicon #high-perf #quantized #local-first | Best-in-class on Apple Silicon (M-series). Fast unified memory, 4/8-bit native. mlx-lm provides server. Excellent for Mac-based dev pipelines. Tool calling via adapters. |
| **LangGraph** (LangChain) | Agent Frameworks & Orchestration | https://github.com/langchain-ai/langgraph | 82 | 70 | 88 | 88 | 82 | A | #agentic #graph #orchestration #tool-calling #rag | Stateful multi-actor agent graphs. Excellent for complex pipelines. Can use local Ollama via LangChain integration. Strong RAG/memory support (can integrate MCP). More boilerplate than DSPy for simple cases. |
| **Open WebUI** | UI & Interfaces | https://github.com/open-webui/open-webui | 75 | 80 | 85 | 92 | 82 | A | #ui #chat #local-first #docker #multi-model | Polished ChatGPT-like UI for local models (Ollama, llama.cpp, etc.). Supports tools in recent versions. Great for human-in-loop debugging of agents before headless pipeline use. Docker one-liner. |
| **Chroma** (or LanceDB) | Memory & RAG Systems | https://github.com/chroma-core/chroma | 70 | 85 | 80 | 85 | 78 | B | #rag #vector #code-memory #local-first #embeddings | Solid local vector DB. Easy Python SDK. Good for code RAG (embed functions/classes). Can serve as foundation for MCP-style persistent code memory. Lightweight. |
| **Atomic Task Graph (ATG)** | Agent Frameworks & Orchestration | Prototype: https://github.com/themark-net/atg-framework (paper: https://arxiv.org/abs/2607.01942) | 88 | 75 | 90 | 60 | 82 | A | #agentic #graph #dag #planning #parallelism #failure-repair #paper-based #prototype #I2 | **I2 probe** (2026-10-06, Entry 101). Runnable core pinned at `543e778ed24fbf3fc903eb961feb627039019832` on `main` (live score recorded at `86d1b8905116fb7ec954ee5c4fe0d18f763b7e16` on `build/atg-finish`). The I2 score (2/10 valid, 2/10 sink-correct) was taken at 86d1b890 on build/atg-finish and has not been re-run at the main pin 543e778. Live atg-compile on Ollama `qwen3.6:35b`: exit 0, 2/10 valid DAGs, 2/10 sink-correct, repairs 0, wall 478s. `qwen3-coder-next` not loaded (memory gate). No pipeline coupling. Point `ATG_REPO` at a clean checkout or worktree of atg `main` at the pin. Independent reimplementation of Zhang et al. (2026), arXiv:2607.01942 — not official ATG code and not a paper-benchmark claim. Notes: [docs/ops/atg-coupling.md](docs/ops/atg-coupling.md). Next gate: stay I2. Do not self-promote to I3. |
| **harness2** | Agent Frameworks & Orchestration | https://github.com/google-research/harness2 | 70 | 55 | 58 | 45 | 59 | C | #agentic #local-first #opencode #sandbox #paper-based #I1 | **I1 staged evaluation** (2026-10-20, Entry 136). Pin `1cfe254e8d25b15f37048c3730134686abe60335`. nimo trial: own llama-server, `qwen3.6:35b`, sandboxed OpenCode, 48-case set. Held-out 15/16 on both bases and the chain final. Gain 0. No proposal branch. Receipt: `pipelines/dogfood/harness2-local/receipt.json`. Scores are the weighted rubric (0.35*70+0.25*55+0.25*58+0.15*45 = 59.5, recorded 59). Not a Feature GO. Not I3. I1 stay. Catalog HOLD 70-75 untouched. |
| **ponytail** (skills pack) | Coding & Dev Agents | https://github.com/DietrichGebert/ponytail | 80 | 92 | 88 | 82 | 86 | A | #terminal #coding-agent #local-first #grok-cli | Minimalism / YAGNI skill pack. Pin `8e69b4a`. |
| **karpathy-guidelines** | Coding & Dev Agents | https://github.com/forrestchang/andrej-karpathy-skills | 78 | 95 | 85 | 80 | 84 | A | #coding-agent #grok-cli #local-first | MIT single skill; pin `2c60614`. |
| **repowise** | Coding & Dev Agents | https://github.com/repowise-dev/repowise | 88 | 92 | 88 | 82 | 88 | A | #context #token-efficiency #coding-agent #local-first | **X Entry 006.** Pin `repowise==0.30.0`. |
| **gstack** | Agent Frameworks & Orchestration | https://github.com/garrytan/gstack | 85 | 85 | 90 | 95 | 88 | A | #skills #multi-agent #roles #workflow | **X Entry 010.** Docs-only / raw-port-blocked. Also comparison set under Autonomous AI Companies. |
| **Multica** | Agent Frameworks & Orchestration | https://github.com/multica-ai/multica | 88 | 78 | 92 | 95 | 88 | A | #multi-agent #orchestration #workflow #skills #self-host #docker | **X Entry 012.** Board + teammates. Also scored under Autonomous AI Companies (A). |
| **mattpocock/skills** | Agent Frameworks & Orchestration | https://github.com/mattpocock/skills | 82 | 90 | 90 | 90 | 87 | A | #skills #planning #tdd #review #composable | **X Entry 008.** |
| **marketing-skills (marketing-council)** | Agent Frameworks & Orchestration | https://github.com/coreyhaines31/marketingskills | 78 | 90 | 88 | 92 | 85 | A | #skills #multi-agent #council #prompt-pack | **X Entry 004.** First-party port. |
| **Antigravity-Manager** | Proxy & Routing | https://github.com/lbjlaq/Antigravity-Manager | 85 | 80 | 90 | 90 | 86 | A | #proxy #account-pool #tauri #openai-shim #I1 #low-pri | **X Entry 005. Skip install** (OQ-0007). LiteLLM+keys default. Low opportunity. [docs/ops/antigravity-catalog-posture.md](docs/ops/antigravity-catalog-posture.md). |
| **Jamon Holmgren agentic setup** | Pipeline & CI/CD Components | https://x.com/i/status/2076001786700394610 | 70 | 85 | 92 | 80 | 81 | A | #workflow #harness #agents-md #process | **X Entry 007.** |
| **Ruben Hassid context/token hacks** | Pipeline & CI/CD Components | https://x.com/i/status/2075807299638014212 | 65 | 92 | 80 | 75 | 77 | B | #token-efficiency #prompt #workflow | **X Entry 009.** |
| **eval-harness (pfy)** | Evaluation & Benchmarking | this repo (`examples/eval-harness/`) | 88 | 90 | 95 | 80 | 89 | A | #evaluation #pipeline #local-first #litellm-ready | First-party scored ladder. |
| **write-guard-mcp** | Tool Calling & Function Infrastructure | this repo (`harness/write-guard-mcp/`) | 90 | 92 | 95 | 80 | 90 | S | #mcp-compatible #security #filesystem #audit #local-first | First-party write mediation. Default audit. |
| **Hermes Agent (feedback loops)** | Agent Frameworks & Orchestration | https://github.com/NousResearch/hermes-agent | 90 | 82 | 92 | 90 | 89 | A | #agentic #self-healing #skills #memory #feedback-loop | **X Entry 048.** **Ported:** `/hermes-feedback` (`bootstrap/grok-cli/skills/hermes-feedback/`, T-0048) — pattern only, not Hermes runtime. Credential pools: Entry 055. **Entry 134:** runtime eval as a local bot interface (isolated `HERMES_HOME`). Scores unchanged. Not an embed. |
| **awesome-hermes-skills** | Agent Frameworks & Orchestration | https://github.com/ZeroPointRepo/awesome-hermes-skills | 88 | 90 | 90 | 92 | 89 | A | #skills #curated #prompt-pack | **X Entry 053.** |
| **LEANN** | Memory & RAG Systems | https://github.com/StarTrail-org/LEANN | 88 | 85 | 88 | 85 | 87 | A | #rag #compression #local-first #embeddings | **X Entry 052.** |
| **Memvid** | Memory & RAG Systems | https://github.com/memvid/memvid | 88 | 82 | 85 | 88 | 86 | A | #memory #versioning #local-first #rag | **X Entry 044.** |
| **opencode-mem** | Memory & RAG Systems | https://github.com/tickernelz/opencode-mem | 82 | 85 | 85 | 80 | 83 | A | #memory #vector #coding-agent #local-first | **X Entry 049.** |
| **llama.cpp ngram-mod** | Inference & Serving | https://github.com/ggerganov/llama.cpp | 85 | 95 | 88 | 90 | 89 | A | #high-perf #speculative-decoding #local-first #gguf | **X Entry 051.** |
| **Finn Loop / eval-loop / 8-exits patterns** | Agent Frameworks & Orchestration | docs / X Entries 024 · 027 · 031 · 032 · **068** | 92 | 90 | 92 | 88 | 91 | A | #agentic #loops #evaluation #human-in-loop #stop-conditions #exits | Loop engineering pedagogy + complete exit taxonomy. **Entry 068** (hanakoxbt): 8 mandatory exits. **Ported:** first-party Grok skill `/agent-loops` (`bootstrap/grok-cli/skills/agent-loops/`, T-0050) — exit card, 4 loop types, Finn phases, rubric layer; pairs with `/one-shot`. **Implementation:** `orchestration` toolset (ADR-0017). |
| **destructive_command_guard** | Tool Calling & Function Infrastructure | https://github.com/Dicklesworthstone/destructive_command_guard | 80 | 90 | 85 | 82 | 84 | A | #security #guardrail #coding-agent | **X Entry 041.** |
| **OpenClaude-Portable** | Coding & Dev Agents | https://github.com/techjarves/OpenClaude-Portable | 82 | 88 | 85 | 85 | 85 | A | #coding-agent #portable #folder-based | **X Entry 054.** |
| **MUE-X** | Agent Frameworks & Orchestration | https://github.com/KorroAi/mue-x | 85 | 70 | 90 | 72 | 81 | A | #agentic #self-evolving #ast-mutation #autonomous #memory #mcp-compatible #self-modifying #local-first | **X Entry 067.** Self-rewriting Python agent via 6 AST strategies + 7 drives + PAD mood + 6-layer memory + GitHub absorption. Standalone `python -m mue`. Immune system + sealed kernel. Pin main if adopted. Deeper local-backend + mutation-safety eval queued. Pattern extract for loop/skills packs. |
| **Bumblebee** | Tool Calling & Function Infrastructure | https://github.com/perplexityai/bumblebee | 88 | 90 | 92 | 85 | 89 | A | #mcp-compatible #security #supply-chain #local-first #go | **X Entry 069.** Perplexity read-only scanner for packages, extensions, **MCP configs**. NDJSON, zero deps, baseline/project/deep profiles. Directly addresses MCP install trust gap. Pair with write-guard-mcp. |
| **Hyperframes** | Agent Frameworks & Orchestration | https://github.com/heygen-com/hyperframes | 90 | 85 | 92 | 95 | 90 | S | #skills #multimodal #video #agent-native #html | **X Entry 070.** HeyGen open-source: agents write plain HTML → deterministic MP4. Ships skills (`npx skills add heygen-com/hyperframes`), CLI, catalog. Production use at HeyGen. Canonical agent-native video surface. |
| **Camofox Browser** | Tool Calling & Function Infrastructure | https://github.com/jo-inc/camofox-browser | 88 | 82 | 90 | 88 | 87 | A | #browser #anti-detection #mcp-compatible #agent-tool #local-first | **X Entry 071.** Camoufox (C++ fingerprint spoofing) wrapped as REST API for agents. Production engine behind jo/askjo.ai. MCP variants exist. Default candidate for stealth web tools in agent-cage. |
| **asm (agent-skill-manager)** | Agent Frameworks & Orchestration | https://github.com/luongnv89/asm | 90 | 88 | 95 | 90 | 91 | A | #skills #cli #cross-agent #security-audit #local-first #npm | **X Entry 075.** Universal skill manager across 19 agents (Claude Code, Codex, Cursor, Cline, Continue, Aider, Hermes, …). Install/search/audit/organize; `--json` for agents; security scan; 4.3k+ skill catalog. MIT. “npm for AI agent skills.” High priority for Grok CLI skill distribution. |
| **claude-codex-settings** | Coding & Dev Agents | https://github.com/fcakyon/claude-codex-settings | 88 | 85 | 90 | 88 | 88 | A | #configs #hooks #plugins #claude-code #codex #cursor #quality | **X Entry 076.** Battle-tested plugins, hooks, agents & shared guidance for Claude Code, Codex, Cursor, Gemini CLI. Targets Karpathy-style pitfalls (overcomplication, no clarification). Complements asm. Extract hooks for Grok policy packs. |
| **kanbots** | Agent Frameworks & Orchestration | https://github.com/leodavinci1/kanbots | 85 | 70 | 90 | 78 | 81 | A | #multi-agent #kanban #worktree #mcp-compatible #parallel #opencode #local-first #ui | **X Entry 078.** Unified Kanban that dispatches 11 agent CLIs (Claude Code, Codex, OpenCode, Qwen, …) in parallel, each in isolated worktree. Local SQLite or GitHub issues, autopilot, decision prompts, MCP server, branch preview + promote. Stage 0 pass (npx). Complements Multica + agent-cage. |
| **multi-agent-generator** | Agent Frameworks & Orchestration | https://github.com/aakriti1318/multi-agent-generator | 83 | 68 | 87 | 74 | 79 | B | #agentic #orchestration #litellm-ready #codegen #crewai #langgraph #local-first | **X Entry 079.** Plain-English multi-agent team generator (CrewAI/LangGraph/ReAct/Agno) with LiteLLM/Ollama, NL tool gen, orchestration patterns. Scaffolding utility (I0). See `sources/entries/079-multi-agent-generator.md`. |
| **DeepSeek-V4.1-Flash-1017 GGUF** | Inference & Serving | https://huggingface.co/unsloth/DeepSeek-V4.1-Flash-1017-GGUF | 40 | 20 | 50 | 70 | 42 | D | #gguf #quantized #moe #local-first #open-weights | **X Entry 153.** Unsloth Dynamic V3.1 GGUF. Smallest quant UD-IQ1_S is 232979608420 bytes. nimo RAM+VRAM is 132524449792 bytes, so the file plus 8 GiB context does not fit. Not downloaded. Quality claim not measured. I0. Not integrated. No weights. NO-GO as a local default. Receipt: `eval/mvp-1031/dsv4/REPORT.md`. |
| **SkillSpector** | Tool Calling & Function Infrastructure | https://github.com/NVIDIA/SkillSpector | 86 | 92 | 84 | 82 | 86 | A | #security #skills #local-first #static-analysis #python | **Entry 148.** Advisory static scan before a fetched skill is copied. Pin `e7172462caf367736645f66c1aa154ca5f9c64dc`. `make skill-scan`. See [docs/ops/skill-scan.md](docs/ops/skill-scan.md). Not a CI gate. Receipt: `eval/catchup-1107/skillspector/REPORT.md`. |

## Autonomous AI Companies

Full multi-agent simulated companies. **Do not** score with S1–S4 alone. Use [docs/evaluation/autonomous-ai-companies-rubric.md](docs/evaluation/autonomous-ai-companies-rubric.md).

| Tool | Primary Cat | GitHub | C1 Org | C2 Cycle | C3 Mem | C4 Safety | C5 Econ | C6 Local | Weighted | Tier | Key Tags | Integration Notes |
|------|-------------|--------|--------|----------|--------|-----------|---------|----------|----------|------|----------|-------------------|
| **Auto-Company** | Autonomous AI Companies | https://github.com/MaxMiksa/Auto-Company | 5 | 5 | 5 | 4 | 4 | 5 | **4.7** | **S** | #ai-company #multi-agent-org #consensus-memory #persona-roles #cycle-autonomy #local-first | **X Entry 066.** 14 expert personas (Bezos CEO, Vogels CTO, Munger critic, DHH eng…); shared `memories/consensus.md` baton (human-editable steer); cycle: brainstorm → pre-mortem GO/NO-GO → build/deploy; pure discussion forbidden; 30+ skills; daemon macOS/Win/Linux; Claude Code + Codex CLI; local dashboard. Honest: costs real money/cycle, early stability. **Posture:** extract patterns (personas, consensus baton, Munger gate, forbidden-action table, squad formation) into Grok skills/AGENTS.md — **not** primary runtime (no ADR to adopt company daemons). Compare Multica / gstack / paperclip templates. |
| Multica (cross-ref) | Autonomous AI Companies (secondary) | https://github.com/multica-ai/multica | 3 | 4 | 4 | 3 | 3 | 4 | 3.5 | A | #ai-company #multi-agent-org #board | Primary row under Agent Frameworks; company-rubric A for teammate-board use. |
| paperclipai/companies (cross-ref) | Autonomous AI Companies (secondary) | https://github.com/paperclipai/companies | 4 | 2 | 3 | 2 | 2 | 4 | 2.9 | B | #ai-company #templates | **X Entry 050.** Importable org templates; weak autonomy engine. |
| Claude Company 122 skills (cross-ref) | Autonomous AI Companies (secondary) | multiple skill packs | 4 | 2 | 3 | 3 | 3 | 4 | 3.2 | B→A | #ai-company #skills | **X Entry 037.** Org chart + skills; cycles operator-built. |

## Recommended stack (2026-07)

| Role | Tool | Lab proof |
|------|------|-----------|
| Operator CLI | Grok Build + bootstrap | host `grok` + `make cage-grok*` |
| Isolation lab | agent-cage | `cage-test`, smokes, net smoke |
| Local models | Ollama + LiteLLM | `smoke-litellm-ollama`, `eval-matrix` |
| Code memory | codebase-memory-mcp (+ repowise) | `smoke-context-tools` |
| Write policy | write-guard-mcp | `smoke-write-guard` |
| Scored eval | eval-harness | `eval-v02` |
| Company patterns (docs) | Auto-Company patterns | scoring-summary Cluster 5 |

*v0.4.10 — Entry 078: kanbots (multi-CLI Kanban parallel agent dispatcher).*

## Paper Analysis Use Case (Recurring Workflow)

'Read a paper' is now a supported method for discovering and evaluating new agentic tools/methodologies (e.g., from X posts). Process: identify paper → check for code → distill methods → feasibility score → catalog → optional prototype.

## Evaluation Notes & Known Gaps (v0.4)

- **Grok CLI Integration**: Most S/A tier tools expose OpenAI-compatible endpoints or LiteLLM support.
- **MCP Code Memory**: codebase-memory-mcp is the active MCP code-graph server.
- **Company systems**: Use dedicated rubric; default integration is pattern extraction only.
- **DSPy + LiteLLM Synergy**: Still recommended for new agent development.

## Update Process

1. New X link / paper / tool → sources/x-posts.md append + TOOLS.md + data/tools.json when scoring.
2. New **AI company** → company Stage 0 gate + C1–C6 rubric; Cluster 5 in scoring-summary.
3. Integration experiment → empirical notes + score adjust.
4. Major release → re-score.

## claude-code-unified-agents (A-tier · I1)

| Field | Value |
|-------|-------|
| Source | https://github.com/stretchcloud/claude-code-unified-agents |
| X | https://x.com/i/status/2082997925014053075 |
| Scores | R4 I3 Repro5 UV4 → **A** overall ~80 |
| Integration | Curated **16** paths skills under `bootstrap/grok-cli/skills-external/claude-unified-agents/` |
| Eval | `pipelines/eval/unified-agents-eval.latest.md` (98% gate pass, mean 4.06) |
| Non-goal | Claude Code primary; full 54 first-party |
| Ops | [unified-agents-recipes.md](docs/ops/unified-agents-recipes.md) |

## Exo / exoharness (A-tier · I1)

| Field | Value |
|-------|-------|
| Source | https://github.com/exoharness/exo |
| Pin | `372602d1b553af06e9843e19f31fa8a7f749ab6e` |
| Scores | R5 I2–3 Repro4–5 UV5 → **~81 A** |
| Differentiator | Recursive self-mod + immutable event log + rebuild guardian |
| Self-eval | Practice loop (SELF-CONTROL §8), **not** a numeric RSI rubric |
| Our extract | [exo-self-mod-patterns.md](docs/ops/exo-self-mod-patterns.md) · [integration-self-mod-eval.md](docs/ops/integration-self-mod-eval.md) |
| Automation | `make eval-integration-change` |
| Non-goal | Primary runtime; unattended monorepo RSI |
