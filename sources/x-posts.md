# X Post Sources Log

Log of X (Twitter) posts used to seed or expand the tool catalog. Each entry includes link, date (if known), poster, summary, extracted repos, and TOOLS.md linkage.

**Recovery note (2026-07-16):** Entries 001–055 reconstructed after a series of commits that left only the latest entry in the file. Source commits via `git log -- sources/x-posts.md`.

### Entry 001: Atomic Task Graph (ATG) - Agentic Planning Framework

- **URL**: https://x.com/i/status/2075994424484732984
- **Date**: 2026-07-11
- **Poster**: Alex Veremeyenko (@alex_verem / @alex_prompter)
- **Summary / Key Claims**: Discusses a new research framework called Atomic Task Graph (ATG) from Tsinghua and South China University of Technology researchers. ATG uses explicit directed acyclic graphs (DAGs) for task decomposition instead of linear chains, enabling parallelism, localized failure repair, and better performance with small 7B-8B models on agent benchmarks (e.g., outperforming GPT-4 + ReAct on ALFWorld). Emphasizes architecture over scale. Includes video explanation and links to the paper.
- **Extracted Repos / Tools**: None (research paper only). Paper: https://arxiv.org/abs/2607.01942. No GitHub code or implementation found in post or paper.
- **TOOLS.md Link**: Added detailed entry under Agent Frameworks & Orchestration with feasibility analysis and distilled methodology.
- **Notes**: Strong conceptual fit for agent orchestration and MCP-style memory (explicit dependencies and reuse). Recurring use case: 'Read a paper' for discovering new agentic methodologies. No immediate code to subtree; focus on re-implementation feasibility. High value for pipeline robustness.
- **Status**: Analyzed - paper-based entry (no code repo)

**Paper Analysis Process (New Use Case)**: 
1. Extract from X post or direct link.
2. Browse PDF/HTML for repo/code links (initial pass: none here).
3. Summarize methodology, distill core ideas.
4. Score feasibility of implementation in local stack (e.g., NetworkX + LangGraph/DSPy + Ollama).
5. Add to TOOLS.md with notes, tags, and potential integration points.
6. Update this log.

### Entry 002: ADR / process docs for coding agents (research sweep)

- **URL**: multiple (semantic + keyword search 2026-07-11) — e.g. https://x.com/martinfowler/status/2036467195538968695 , https://x.com/KingBootoshi/status/2062106571669446800 , https://x.com/santtiagom_/status/2069083778228552024 , https://x.com/therobertta_/status/2073845367784017939 , https://x.com/jbdamask/status/2075216922153566671
- **Date**: 2026-07-11 (search date)
- **Poster**: community aggregate (Fowler, practitioners using Claude/Codex, skill authors)
- **Summary**: Strong consensus that **in-repo ADRs** (Context / Decision / Consequences / Alternatives) improve multi-session agent alignment. Practitioners tell agents to maintain ADRs during architecture chats. Community Claude skills for ADR exist; classic tooling is **adr-tools** + template catalogs. No dominant “open questions parking lot” product for agents—markdown/issues fill that niche.
- **Extracted Repos/Tools**: adr-tools (https://github.com/npryce/adr-tools); ADR template collections; optional emerging enforcement (Mneme / Decision Guardian — watch list). Our response: **project-process** scaffold + skills, not a new platform.
- **TOOLS.md Link**: project-process bootstrap (S); adr-tools (B optional)
- **Notes**: Verdict recorded in ADR-0005 and `bootstrap/project-process/.../evaluation.md` — light framework sufficient.
- **Status**: Analyzed — process kit shipped under `bootstrap/project-process/`

### Entry 003: colibri - Extreme Low-Resource MoE Inference Engine

- **URL**: https://x.com/i/status/2075731830477877612
- **Date**: 2026-07-11
- **Poster**: @chenzeling4 (Zane Chen)
- **Summary / Key Claims**: Colibri runs GLM-5.2 (744B-parameter MoE, only ~40B active per token) on a laptop with 25GB RAM in pure C with zero dependencies. ~2,400-line C file core. Keeps dense part (~17B params) resident in RAM (~9.9GB at int4); streams routed experts from disk on demand. Provides CLI chat and OpenAI-compatible serve mode. No GPU, no BLAS, no Python runtime. Exceptional engineering for consumer hardware.
- **Extracted Repos / Tools**: https://github.com/JustVugg/colibri (core inference engine). Pre-converted int4 model weights available on HF (jlnsrk/GLM-5.2-colibri-int4). Recent Tauri desktop shell addition.
- **TOOLS.md Link**: Added new row in Inference & Serving category (A tier, overall 86). Detailed integration notes on low-RAM flagship model enablement, serve endpoint for pipelines, and speed tradeoffs.
- **Notes**: Highest-signal external X seed to date for the catalog. Enables practical local use of flagship-scale MoE without datacenter hardware. Zero-deps + pure C = excellent reproducibility and pipeline friendliness. S1 very high (consumer HW access to 744B-class reasoning). S2 reflects current disk-streaming speed limits (0.05–1+ tok/s; faster on high-end NVMe/M-series). Strong community validation via rapid stars and engagement. Pinned specific recent commit. Recommended next: empirical testing of serve mode with LiteLLM/Grok CLI, tok/s benchmarks on target hardware, and MCP context integration potential.
- **Status**: STAY I1 (2026-11-07 nimo). Pin v2.1.0 commit 704a3f68184b78367a04cb5526e428dc2f90f05b. Linux tarball sha256 d54b4c57c12417fc9e784b649249ac1aa3480eec44ece2777d4cbc639a25e66a. Served the local qwen3.6:35b GGUF: 4/4 exact, median decode 22.49 tok/s vs Ollama 45.28 tok/s (0.497x). GLM-5.2 weights not downloaded (381230481274 bytes). Not wired. See eval/evq1107/colibri/REPORT.md.

### Entry 004: Marketing Skills v2.8.0 — marketing-council multi-expert skill pack

- **URL**: https://x.com/i/status/2076048436538048530
- **Date**: 2026-07-11
- **Poster**: Corey Haines (@coreyhainesco)
- **Summary / Key Claims**: v2.8.0 release of the Marketing Skills pack (now 47 skills total). New flagship skill: `/marketing-council` — pitches or reviews marketing strategies by convening a simulated board of 12 legendary marketers (Seth Godin, David Ogilvy, Alex Hormozi, April Dunford, Eugene Schwartz, Claude Hopkins, Gary Halbert, Russell Brunson, Rory Sutherland, Byron Sharp + others). Every session includes a designated dissenter for rigorous, balanced critique and to surface blind spots. The pack consists of modular `SKILL.md` files (with `references/` for advisor dossiers and cross-skill links) targeted at Claude but implemented as portable markdown prompts + structured workflows. Free & open source. Install via `npx skills add coreyhaines31/marketingskills` (or equivalent CLI). Includes demo video in the announcement post. Strong community signal (300+ likes, 600+ bookmarks on v2.8.0 post; repo ~37k stars).
- **Extracted Repos / Tools**: https://github.com/coreyhaines31/marketingskills (core repo). New skill directory: `skills/marketing-council/` containing `SKILL.md` (161 lines defining session modes: quick take / council session / full council; advisor bench with specific lenses; structured output expectations) and `references/advisors/` (individual .md dossiers for each legend). 46 other skills cover the full marketing stack (ab-testing, ad-creative, ads, ai-seo, analytics, cold-email, content-strategy, copywriting, cro, customer-research, launch, lead-magnets, marketing-ideas, marketing-plan, pricing, prospecting, etc.) with heavy internal cross-referencing.
- **TOOLS.md Link**: New row added under Agent Frameworks & Orchestration category (as high-signal prompt/skill pattern library). Primary value: the `marketing-council` architecture and clean SKILL.md + references/ format. **Explicit recommendation**: Port/adapt the council + dissenter pattern and advisor personas into local Grok CLI skills (modeled after existing `bootstrap/grok-cli/skills/ponytail/` and `karpathy-guidelines/`) or as a DSPy module / custom agent loop. This directly addresses single-perspective bias and hallucination in local LLM agent outputs. The modular skill format is directly compatible with the local skills system in this repo.
- **Notes**: Borderline for strict "local LLM" criteria (original execution path is Claude API; Stage 0 gate passes only on the prompt content itself being fully self-hostable and adaptable). However, the *ideas* and *structure* have high pipeline value for any LLM (local or hybrid). The dissenter mechanism and multi-lens council is a concrete, low-overhead way to improve reasoning quality without extra models. SKILL.md format mirrors the one used in `bootstrap/grok-cli/skills/`. High S4 (ecosystem) due to massive stars, recent activity (v2.8.0 Jul 2026), and practitioner adoption. Prioritize: (1) Extract/adapt marketing-council into a first-party local skill under bootstrap or examples/. (2) Test in gom-jobbar or personal agent for marketing/strategy tasks or general decision review. (3) Consider as template for other domain councils (e.g., engineering council, biohacking council). See full SKILL.md and advisor refs in the upstream repo for implementation details. Strong recurring "read a skill pack" workflow candidate.
- **Status**: Processed and cataloged (initial scores applied; local adaptation experiment added to TODO.md and open-questions/)

### Entry 005: Antigravity-Manager — AI account switcher & local API relay (Tauri v2 / Rust)

- **URL**: https://x.com/i/status/2076109541863989620
- **Date**: 2026-07-12
- **Poster**: Zane Chen (@chenzeling4)
- **Summary / Key Claims**: Antigravity-Manager solves the pain of juggling multiple AI tool accounts with one-click seamless switching. Core innovation: converts web sessions (from tools that rely on browser login) into standard API calls via a local relay/proxy. Rust-based backend, Tauri v2 desktop frontend for tiny binary size (~4MB in the refactor edition). Eliminates protocol and auth mess across providers. ~30K stars on the main repo. High engagement because developers are exhausted by repetitive login, quota tracking, and account rotation for AI coding/agent tools (Gemini, Claude, Antigravity ecosystem, etc.).
- **Extracted Repos / Tools**: Primary: https://github.com/lbjlaq/Antigravity-Manager (~30k stars, Tauri v2 + Rust/React or Vue, local API proxy/relay with OpenAI/Anthropic compatibility, quota monitoring, auto-switching, unlimited account pool, backup/migration). Refactor edition: https://github.com/Ariszn/Antigravity-Manager-tauri (pure Rust + Tauri v2 + Vue 3, even smaller footprint, cross-device seamless migration, process management). Features include real-time quota visualization, smart auto-switch on rate-limit/quota thresholds, AES encryption for credentials, and acting as a local gateway that normalizes web-based sessions into clean API endpoints.
- **TOOLS.md Link**: New entry added under Proxy & Routing category (with UI & Human-in-the-Loop notes). Explicit integration value for Grok CLI + LiteLLM pipelines: run the manager locally as account/relay layer; point agents to its local proxy endpoint for automatic rotation and normalized access without managing logins per provider.
- **Notes**: Same high-signal poster as colibri (Entry 003) — pattern of excellent, practical dev tooling posts. Strong local-first credentials (Tauri desktop app, Rust core, fully offline relay after initial setup). Directly complements LiteLLM (unified routing) by adding account-pool + session-to-API conversion layer on top. The local relay/proxy capability is high-value for any multi-backend setup (Grok + local Ollama + cloud fallbacks) where web-only tools or rate-limited accounts are in play. S1/S3 high because it exposes standard API while handling the messy auth/session part locally. S4 excellent (30k stars, active releases, solves widespread friction). Recommend: (1) Download/test the Tauri binary for operator workflow. (2) Wire its local relay into LiteLLM config or Grok CLI base_url for seamless multi-account use. (3) Monitor for MCP/hooks if the project exposes useful state (quota, active account) for agent memory. (4) Consider the refactor edition for minimal footprint. This + colibri from same author = strong signal on practical local AI infra.
- **Status**: Processed and cataloged (initial scores applied; proxy/relay integration experiment added to TODO / open-questions)

### Entry 006: repowise — context optimization layer for coding agents (token & file-read efficiency)

- **URL**: https://x.com/i/status/2076117959958053084 (link post); original discussion https://x.com/srishticodes/status/2075849201523523729
- **Date**: 2026-07-12 (link post); main post 2026-07-11
- **Poster**: Srishti (@srishticodes)
- **Summary / Key Claims**: repowise is an open-source context layer for coding agents (Claude Code, Codex, Cursor, VS Code). It prevents agents from reading dozens of irrelevant files by providing smart, targeted context. No API key or billing required. Claims dramatic efficiency gains vs baseline Claude Code: 27x token efficiency, 36% lower cost, 89% fewer file reads, 49% fewer tool calls. All numbers reproducible with harness included in repo. 3.5k+ stars, 50k+ pip installs, 30+ contributors. Simple install: `pip install repowise` then point at codebase.
- **Extracted Repos / Tools**: https://github.com/repowise-dev/repowise (main repo). Lightweight pip-installable Python package that acts as a context optimization / smart retrieval layer on top of existing coding agents. Works out-of-the-box with popular IDE/agent setups.
- **TOOLS.md Link**: Added under Coding & Dev Agents (with notes on overlap with codebase-memory-mcp and RAG patterns). Strong measurable impact on token usage and tool-call reduction — directly relevant to pipeline cost/performance goals.
- **Notes**: Some redundancy with existing entries (codebase-memory-mcp for code-graph memory; general coding agents like Continue/Aider/ponytail). However, repowise's specific value is its lightweight, drop-in context optimizer with published, reproducible benchmarks focused on reducing wasteful file reads and tool calls in agent loops. This aligns tightly with core repo goals: improving efficiency, lowering token costs, and making local/hybrid agent runs more practical. It can feed better context into memory systems or run alongside them. S1/S3 high for immediate usability with existing agents. S2 strong on measured efficiency gains. S4 solid (3.5k stars + pip adoption). Recommend: Evaluate as complementary layer (test token savings on real gom-jobbar or personal coding tasks); consider integration patterns with LiteLLM + local models or as a pre-filter before MCP/codebase-memory. Good candidate for empirical benchmarking in the eval harness (OQ-0002).
- **Status**: Processed and cataloged (initial evaluation complete; noted overlaps + unique benchmark-driven efficiency angle; integration test suggested in TODO)

### Entry 007: Jamon Holmgren Agentic Coding Setup (comprehensive workflow checklist)

- **URL**: https://x.com/i/status/2076001786700394610
- **Date**: 2026-07-11
- **Poster**: Jamon Holmgren (@jamonholmgren)
- **Summary / Key Claims**: Detailed dump of a production-grade agentic coding setup for reliable AI agents (Claude Code, Cursor, Codex, etc.). Emphasizes that missing structural pieces hurts results. Covers 18+ elements including AGENTS.md as router to skills/docs/tools; standard workflow doc/skill (recommends Matt Pocock skills); self-healing docs kept updated by agents; agents run/test/fix the app themselves; end-to-end tests and maintenance docs; custom linters with auto-fix or LLM-assisted fix; cross-agent reviews with different models/personas (maintainability, security, performance, AI smells); agent traces/worksheets committed with git tags for session continuity; automatic end-of-session feedback committed for periodic review; custom scripts in tools/bin folder (with docs on creating them); periodic commit sweeps; coding conventions doc; agent loop/night shift skill; task queue (e.g. TODOS.md or Linear CLI); false-confidence test audits; visual regression tests; automatic performance benchmarks and profiling; end-of-shift full validations.
- **Extracted Repos / Tools**: References Matt Pocock skills repo (https://github.com/mattpocock/skills) for workflow doc/skill. Main value is the comprehensive process/workflow checklist and best practices for robust agentic setups. No single new repo, but points to established patterns and tools.
- **TOOLS.md Link**: Added as workflow/process resource under Agent Frameworks & Orchestration (or dedicated Harness/Workflow Engineering note). Strong mapping to existing repo components (AGENTS.md, project-process, skills bootstrap, evaluation rubric, ADRs/open-questions).
- **Notes**: Extremely relevant and actionable for enhancing the repo's agent scaffolding, harness engineering (see Entry on Learn Harness Engineering), and practical pipeline robustness. Many ideas directly extend current artifacts: make AGENTS.md a true router + self-healing guidance; add traces/worksheets (complements ADRs); custom scripts and review personas; autonomous loops and benchmarks (ties to evaluation harness ideas). Highly recommended for synthesis into docs, new skills, and bootstrap templates. Aligns with self-hosted/local focus by providing concrete, implementable workflows.
- **Status**: Processed and cataloged (added as workflow resource; integration recommendations for AGENTS.md enhancement and new skills drafted/implemented)

### Entry 008: mattpocock/skills — Reusable agent skills for real engineering

- **URL**: https://github.com/mattpocock/skills (referenced in above post and widely recommended)
- **Date**: N/A (established repo, referenced 2026-07)
- **Poster**: N/A (high-signal reference in agentic workflow discussions)
- **Summary / Key Claims**: Popular collection of composable, reusable agent skills (markdown SKILL.md files) for "real engineering" workflows with AI coding agents (Claude Code, Cursor, etc.). Focuses on practical, controllable skills rather than heavy frameworks. Includes router skills (e.g. ask-matt), planning (grill-me, to-prd, to-issues, wayfinder), TDD, code review, handoffs, research, prototype, etc. Install via npx skills@latest add mattpocock/skills. Works across agents; emphasizes composability and user control.
- **Extracted Repos / Tools**: https://github.com/mattpocock/skills (main repo, tens of thousands of stars, active). Many individual skills for planning, implementation, review, and orchestration.
- **TOOLS.md Link**: Added under Agent Frameworks & Orchestration or Skills & Prompt Engineering. Strong ecosystem value; direct fit for bootstrap skills and workflow enhancement.
- **Notes**: Excellent complement to the Jamon Holmgren setup and harness engineering resources. Provides ready-to-use, battle-tested skills that can be vendored or referenced in this repo's bootstrap/grok-cli/skills/ and project-process. Highly recommended for cataloging and potential integration (e.g., examples or templates). Aligns with composable skills theme in the repo.
- **Status**: Processed and cataloged (dedicated entry added; recommended for skills bootstrap enhancement)

### Entry 009: 21 Claude $20 Plan Hacks — Context, Token & Prompt Optimization Workflow

- **URL**: https://x.com/i/status/2075807299638014212
- **Date**: 2026-07-11
- **Poster**: Ruben Hassid (@rubenhassid)
- **Summary / Key Claims**: Practical list of 21 hacks to maximize the $20/month Claude plan instead of upgrading to $100. Focuses on token efficiency, context management, prompt engineering, file handling, chat/workflow habits, model selection, and feature usage. Examples: Convert PDFs to Markdown before uploading; plan in chat before using coding features; use short, specific prompts and prompt libraries; edit previous messages instead of stacking corrections; trim long about-me files and summarize periodically; use Projects for recurring context and separate new topics into fresh chats; turn off unnecessary features by default; use cheaper models (Sonnet) for simple tasks and reserve Opus for heavy work; be specific with repo exploration; use voice input for richer prompts; understand rolling 5-hour limits and split usage; know tool strengths (e.g. Gemini for images, Grok for real-time search). Includes links to exact .md prompt files via free subscription/Notion.
- **Extracted Repos / Tools**: No new GitHub repo in the post. Main value is the curated list of efficiency hacks and workflow patterns (prompt libraries, context budgeting, summarization/reset strategies). Complements tools like repowise (token savings) and skills collections.
- **TOOLS.md Link**: Added under Context & Token Efficiency / Prompt Engineering & Skills (or cross-referenced in Agent Frameworks). Strong practical value for pipeline cost/token optimization and agent workflow robustness.
- **Notes**: Highly relevant despite being Claude-specific — the principles are universal for any LLM usage (local Ollama + hybrid setups, Grok CLI pipelines, agent loops). Directly supports repo goals around token efficiency (see repowise), context management (MCP, codebase-memory, RAG), prompt/skill engineering (Matt Pocock skills, marketing-council), and robust workflows (Jamon Holmgren setup, harness engineering). Many hacks translate to local agent instructions: better context curation to reduce re-reads, prompt libraries as reusable skills, periodic summarization for long sessions, specific scoping for coding agents, model routing. Can inspire new skills (e.g., context budget auditor, prompt library manager, smart summarizer/reset) or enhancements to AGENTS.md / project templates. Excellent complement to existing efficiency and scaffolding resources.
- **Status**: Processed and cataloged (added as workflow/efficiency resource; potential for new skills or AGENTS.md integration noted)

### Entry 010: gstack — Garry Tan's Open-Source Claude Code Multi-Specialist Setup (23 skills + power tools)

- **URL**: https://x.com/i/status/2075933298627383473 (and https://github.com/garrytan/gstack)
- **Date**: 2026-07-11 (post); repo launched ~March 2026
- **Poster**: Granite (@Granite0x) highlighting Garry Tan (@garrytan, YC President/CEO)
- **Summary / Key Claims**: Garry Tan open-sourced his personal "gstack" — a production-grade Claude Code loadout with 23 opinionated specialists (slash-command skills) + 8 power tools. It turns a single developer into a virtual engineering team (CEO, Designer, Eng Manager, QA, Security, Release Engineer, etc.) via structured workflows (Think → Plan → Build → Review → Test → Ship → Reflect). 121k+ stars, MIT license. Supports Claude Code and multiple other AI coding agents (Cursor, Codex CLI, OpenClaw, etc.) via adapters. Includes browser/QA tools, safety guardrails, cross-model review (/codex), persistent memory (GBrain), and team install mode.
- **Extracted Repos / Tools**: Primary: https://github.com/garrytan/gstack (MIT). 23+ slash-command skills embodying distinct roles and methodologies; power tools for orchestration, safety, browser automation, memory. Install via simple git clone + ./setup into ~/.claude/skills/ or equivalent for other hosts.
- **TOOLS.md Link**: Row **gstack** (A-tier). Integration is **docs-first** (T-0014): `docs/ops/gstack-role-recipes.md` + AGENTS.md role router — not a skills.paths full embed (ADR-0009).
- **Notes**: Role specialization + Think→Plan→Build→Review→Test→Ship→Reflect is the portable value. Complements marketing-council (T-0011 first-party), mattpocock paths subset (tdd/code-review/to-spec), one-shot, cage smokes. **Do not** clone full gstack into this catalog. **2026-07-12 deeper-port eval:** raw skills.paths blocked (Claude harness); comparison attrs in `docs/ops/gstack-skill-port-comparison.md`; single-skill recommendation = first-party **investigate** RCA method rewrite (T-0017), not rsync.
- **Status**: Triple-write complete; T-0014 docs recipes + deeper-port comparison shipped 2026-07-12

### Entry 011: agent-cage (PNNL) — Docker sandbox harness with MCP (operator-selected)

- **URL**: https://github.com/pnnl/agent-cage (discovery: GitHub search `agent-cage`; also considered cleatdev/cleat, chaserhkj/agent-cage)
- **Date**: 2026-07-12
- **Poster**: N/A (operator request; GitHub)
- **Summary / Key Claims**: Docker-based sandbox giving agents a full Ubuntu environment while the operator controls network access via mitmproxy policy, TLS inspection, domain whitelist, audit logs. Native **MCP** overlay (`mcp-servers.yaml`, compose). CLI `agentcage up [--mcp]`, shell, policy, dashboard. Harness-agnostic (Claude Code, Cline, LangGraph, custom agents). Images are versionable for reproducible integration tests — primary path for testing catalog tools in isolation.
- **Extracted Repos / Tools**: https://github.com/pnnl/agent-cage (pin develop `ea0cdb328683`). Related: https://github.com/cleatdev/cleat (Claude-focused Docker cage), https://github.com/chaserhkj/agent-cage (Podman/microVM Rust CLI).
- **TOOLS.md Link**: agent-cage (PNNL) S-tier Pipeline row; wrapper `harness/agent-cage/`.
- **Notes**: Aligns with prior multi-dev harness experience (containers + MCP; Make optional for OS branching). Prefer pnnl for MCP + policy + compose; optional Makefile wrapper for Linux/macOS/Windows(WSL) developer ergonomics.
- **Status**: Processed and cataloged; harness package scaffolded under `harness/agent-cage/`

### Entry 012: Multica — Open-Source Managed Agents Platform (Human + AI Teammates)

- **URL**: https://x.com/i/status/2075999281996312951 (and https://multica.ai/, https://github.com/multica-ai/multica)
- **Date**: 2026-07-11 (post)
- **Poster**: Simplifying AI (@simplifyinAI)
- **Summary / Key Claims**: Multica turns coding agents into real teammates. Assign issues to an agent like you'd assign to a colleague — they'll pick up the work, write code, report blockers, and update statuses autonomously. No copy-pasting prompts. No babysitting runs. Your agents show up on the board like real team members, participate in conversations, and compound reusable "Skills" (SKILL.md packs) over time. 100% Free & Open Source. Works with Claude Code, Codex, OpenCode, OpenClaw, Hermes, Copilot, Cursor, and 14 total coding tools/agents. Strong focus on human + agent collaboration and skill compounding.
- **Extracted Repos / Tools**: Primary: https://github.com/multica-ai/multica (~39.6k stars, MIT/modified Apache). Go backend + Next.js/Electron frontend + CLI/daemon. Features: agent profiles on board, issue assignment & autonomous execution, unified activity timeline, reusable Skills library, runtime monitoring for local daemons, Docker self-host. Supports local daemon driving installed AI coding tools; cloud option available.
- **TOOLS.md Link**: Row **Multica** under Agent Frameworks & Orchestration (tier A, overall 88). `data/tools.json` object `Multica`; pin `2a48ffa2aa73`.
- **Notes**: Outstanding complement to gstack (Entry 010) and other agentic/harness entries. gstack excels at role-specialized slash-command skills and internal workflows; Multica adds the project management board, issue assignment, human+agent timeline, and skill compounding abstraction on top. Strong overlap in supported agents (Claude Code, Codex, Cursor, OpenClaw, etc.) but Multica's "teammates on the board" model reduces redundancy while enabling hybrid teams. Low redundancy risk; highly synergistic. Fits evaluation criteria well: high workflow relevance, Docker self-host, multi-agent surface. Does **not** replace agent-cage (isolation lab). Recommend: catalog done; optional later self-host smoke; explore skill interoperability with bootstrap/gstack patterns. Not a Grok-first requirement for core stack.
- **Status**: **Triple-write complete** (x-posts + TOOLS.md + tools.json) 2026-07-12

### Entry 013: Spec Kit — GitHub's Spec-First Structured Workflow for Agentic Coding

- **URL**: https://x.com/i/status/2076005136736850402 (and https://github.com/github/spec-kit)
- **Date**: 2026-07-11 (post)
- **Poster**: angel (@angeldot_)
- **Summary / Key Claims**: GitHub's Spec Kit solves "vibe coding" problems with AI agents. Forces the AI to create a structured specification BEFORE touching code: /constitution (rules/standards) → /specify (what to build) → /clarify (questions) → /plan (architecture/stack) → /tasks (ordered tasks) → /implement (execution). Reduces absurd errors, inconsistent code, and unpredictable results when working with agents. 120K+ stars, 10K+ forks, open source. Compatible with Claude Code, Cursor, Copilot, Codex, Gemini CLI, and +25 agents.
- **Extracted Repos / Tools**: Primary: https://github.com/github/spec-kit (120K+ stars). CLI-driven spec-first pipeline that agents must follow before any implementation.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Structured Workflow & Prompt Engineering. High-signal GitHub-backed workflow guardrail.
- **Notes**: Excellent complement to gstack (Entry 010) and Multica (Entry 012). Provides the mandatory "spec/planning guardrail" layer before code is touched. Strong overlap in supported agents (Claude Code ecosystem) but solves the predictability/vibe-coding pain point directly. Low redundancy risk — it's a process enforcer that improves results for all downstream tools (gstack skills, Multica assignment, etc.). High fit for evaluation criteria: Very High Workflow Relevance (Planning + Implementation), High Integration Ease (works with many cataloged agents), High Reproducibility (open source CLI commands + GitHub backing), Low Redundancy. Perfect for the repo's "reproduction of best practices" goal — provides a reproducible, spec-driven agentic coding workflow. Recommend: (1) Catalog as core structured workflow tool. (2) Strong candidate to pair with gstack + Multica for end-to-end planning-to-shipping reproduction templates. (3) Consider as baseline for enhancing our own AGENTS.md or project-process docs.
- **Status**: Processed and cataloged (added as major structured workflow resource; high priority for evaluation strategy integration)

### Entry 014: Karpathy Second Brain / Obsidian + Claude Code Wiki (Personal Knowledge Compounding Workflow)

- **URL**: https://x.com/i/status/2076163893983096970
- **Date**: 2026-07-12 (post)
- **Poster**: CyrilXBT (@cyrilXBT) highlighting Andrej Karpathy's idea
- **Summary / Key Claims**: Use AI (Claude Code) to build a "second brain" / living personal wiki instead of just writing code. Point Claude Code at an Obsidian vault folder. Drop sources (articles, transcripts, PDFs) into a `raw` folder. Claude ingests, links, files into a `wiki` of interconnected pages. Compounds over time. Setup: Install Obsidian, create vault, open in Claude Code, paste Karpathy's wiki idea, let Claude build folders + CLAUDE.md router. Then "ingest this" for new sources and query across everything. Never start from blank chat again. 5-minute setup.
- **Extracted Repos / Tools**: No new standalone repo (uses Obsidian + Claude Code). Pattern: folder-based vault with `raw/`, `wiki/`, and `CLAUDE.md` as the control file. Simple ingestion command + cross-query capability.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Personal Knowledge Management & Second Brain Workflows (or cross-referenced under Context & RAG patterns). Lightweight, high-signal personal workflow.
- **Notes**: Excellent lightweight complement to gstack (Entry 010), Multica (Entry 012), and Spec Kit (Entry 013). Uses similar CLAUDE.md router pattern as gstack but for personal knowledge compounding instead of engineering roles. Strong overlap with skills ingestion ideas and context management goals. Low redundancy — it's a simple, reproducible personal RAG/wiki setup using tools we already track (Claude Code + folder structure + Obsidian). High fit for evaluation criteria: High Workflow Relevance (Knowledge Management + Context building), Very High Integration Ease (uses existing agents + Obsidian), Very High Reproducibility (5-min setup with clear steps), Low Redundancy. Perfect for the repo's reproduction goal — easy to document as a best-practice personal second brain template. Recommend: (1) Catalog as core personal knowledge workflow. (2) Strong candidate for a simple reproduction script/template in the repo. (3) Synergistic with gstack-style CLAUDE.md patterns and Multica skill compounding.
- **Status**: Processed and cataloged (added as lightweight personal knowledge workflow resource; high value for practical reproduction)

### Entry 015: claude-code-monitor — Real-time Dashboard for Multiple Claude Code Sessions

- **URL**: https://x.com/i/status/2076022130802622814 (and https://github.com/onikan27/claude-code-monitor)
- **Date**: 2026-07-11 (post)
- **Poster**: Tom Dörr (@tom_doerr)
- **Summary / Key Claims**: Real-time dashboard for monitoring multiple Claude Code sessions. Useful for juggling several agent sessions without losing track of status, progress, or outputs. Clean, practical dev tooling for multi-session workflows.
- **Extracted Repos / Tools**: Primary: https://github.com/onikan27/claude-code-monitor. Real-time monitoring dashboard focused on Claude Code (and extensible to similar agents).
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Monitoring & Observability. Practical multi-session dashboard.
- **Notes**: Strong complement to gstack (Entry 010), Multica (Entry 012), and multi-agent workflows. Provides the missing real-time visibility layer for running multiple sessions in parallel. Low redundancy — it's focused observability, not full orchestration or skills. High fit for evaluation criteria: High Workflow Relevance (Monitoring multi-session agent work), High Integration Ease (Claude Code focused, easy to adopt), High Reproducibility (open source GitHub repo), Low Redundancy. Excellent for practical multi-agent setups. Recommend: (1) Catalog as monitoring tool. (2) Good addition for harness / multi-session reproduction templates. (3) Synergistic with gstack/Multica for full visibility in complex workflows.
- **Status**: Processed and cataloged (added as practical monitoring resource; useful for multi-agent evaluation)

### Entry 016: Claude Company Org Chart — 42+ Curated Skills Pack (Departments + Installable Skills)

- **URL**: https://x.com/i/status/2076221471375122811
- **Date**: 2026-07-12 (post)
- **Poster**: Charlie Hills (@charliejhills)
- **Summary / Key Claims**: Curated collection of 42+ installable skills for Claude, organized like a real company org chart (Developers, Designers, Marketing, Social Media, Finance, Small Business, Legal). Each department has specific skills with direct GitHub/install links (e.g., Superpowers, Context7, Skill Creator, UI UX Pro Max, Taste, Marketing skills pack, etc.). Every skill is real and installable. Turns Claude into a full "company" of specialized agents.
- **Extracted Repos / Tools**: Multiple linked repos including https://github.com/obra/superpowers, https://github.com/upstash/context7, and various skill packs (marketing, social, finance, legal, small business). Pattern: curated, installable SKILL.md-style packs organized by business function.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Skills & Prompt Engineering. High-signal curated skill library with org-chart structure.
- **Notes**: Excellent large-scale complement to gstack (Entry 010), Multica (Entry 012), and skills collections (Matt Pocock, marketing-council). Provides a broad "company departments" org structure on top of reusable skills. Strong overlap in the skills/reusable prompt pattern but at much larger scale (42+ skills across business functions). Low-to-medium redundancy risk — it's a curated, installable library rather than a new framework. High fit for evaluation criteria: Very High Relevance (broad skills across domains), High Integration (many direct install links), High Reproducibility (GitHub-based skills), Medium Redundancy (extends existing skills theme at scale). Perfect for the repo's reproduction goal — easy to document as a best-practice "AI company" skill library. Recommend: (1) Catalog as major skills resource. (2) Strong candidate for examples/ or bootstrap/ integration (many installable skills). (3) Synergistic with gstack/Multica for role-based + org-structured agent teams.
- **Status**: Processed and cataloged (added as major curated skills resource; high value for broad domain coverage)

### Entry 017: Graphify — Codebase Knowledge Graph for Agents (Tree-sitter Parsed, Queryable Graph)

- **URL**: https://x.com/i/status/2076092909372453048
- **Date**: 2026-07-11 (post)
- **Poster**: Tech with Mak (@techNmak)
- **Summary / Key Claims**: 82K-star repo that turns an entire project into a queryable knowledge graph (functions, classes, files, SQL schemas, infrastructure, docs, PDFs, images, videos as connected nodes). Agents traverse the graph instead of repeatedly grepping/opening files. Uses tree-sitter for local parsing (no embeddings, no vector DB, no LLM for graph itself). Calls, imports, inheritance become graph edges. Relationships marked EXTRACTED / INFERRED / AMBIGUOUS. Installs hooks/persistent instructions for Claude Code, Codex, Cursor, Gemini CLI, Copilot +20 agents. Graph committable to Git, auto-rebuilt after commits, team-shareable, MCP-exposed. Core idea: "Map once, query forever" instead of rereading the repo.
- **Extracted Repos / Tools**: Primary: Graphify (82K stars, implied GitHub repo in post). Code-to-graph tool with tree-sitter parsing and agent hooks.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Codebase Knowledge Graph & Memory. High-signal code-to-graph tool.
- **Notes**: **Potential first true duplicate / strong overlap with codebase-memory-mcp and repowise (Entry 006) context optimization**. Both aim to reduce wasteful file reads/greps by providing structured context to agents. Graphify uses explicit graph (tree-sitter parsed relationships) vs. repowise's smart retrieval layer or codebase-memory-mcp's graph memory. Similar "map once, query structured context" philosophy. Low-to-medium redundancy risk — Graphify adds explicit graph traversal + relationship confidence marking + broad non-code asset support (docs/PDFs/images/videos) + MCP exposure. High fit for evaluation criteria: Very High Relevance (codebase knowledge graph for agents), High Integration (hooks for 20+ agents, MCP), High Reproducibility (open source, Git-committable), Medium Redundancy (overlaps with existing graph/memory tools but adds explicit parsing + confidence labels). Recommend: (1) Catalog with explicit comparison to codebase-memory-mcp/repowise. (2) Evaluate for complementary use (Graphify for deep relationship queries; repowise for quick retrieval). (3) Strong candidate for reproduction notes on code-to-graph patterns.
- **Status**: STAY I0 after the 2026-11-07 nimo probe. Pin PyPI graphifyy 0.9.104, tag v0.9.104 commit 433a57a002908e74c9f0abd2ad93af8b302b71c4, wheel sha256 ecc5f436a44c4e776aa88e96acd0d5f26f9e3f680f1d1a010ca06547a78fbd55. Entry 017 recorded no commit. Affected plus the tests in the diff agreed with test_select on 5/10 commits, the same count as codebase-memory and ahead of chiasmus at 3/10. The affected walk added no test. The venv allocates 102 MB. Not a gate. No Feature GO. Report `eval/evq1107/graphify/REPORT.md`.

### Entry 018: Getting Started with Loops — Autonomous Agent Loops Framework (4 Autonomy Tiers + 14-Step Roadmap)

- **URL**: https://x.com/i/status/2076283449388785847
- **Date**: 2026-07-12 (post)
- **Poster**: Annatar.md (@xieike)
- **Summary / Key Claims**: Detailed guide turning Claude into an autonomous "employee that ships while you sleep." Defines 4 loop types by autonomy level: Turn-based (25%, one task/round, control returns to you — best for unclear requirements); Goal-based (70%, define "done" with /goal + separate evaluator that keeps sending Claude back until tests/scores/bugs cleared); Time-based (60%, scheduled /loop e.g. check PR every 5 min, address reviews, fix CI); Proactive (95%, event fires, router dispatches child agents in parallel, review model oversees — no human online). Emphasizes that loop quality depends on system quality and tokens are the real cost. Includes 14-step roadmap from manual prompts to full loops using /goal, SKILL.md, worktrees, MCP, etc.
- **Extracted Repos / Tools**: No single new repo (framework/pattern doc). Key patterns: /goal + evaluator loops, time-based scheduled loops, proactive router + parallel child agents + review oversight, SKILL.md, worktrees, MCP integration. Strong alignment with autonomous agent system design.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Autonomous Loops & Agentic Workflows. High-signal practical framework for autonomous operation.
- **Notes**: Excellent complement to gstack (Entry 010), Multica (Entry 012), Jamon Holmgren setup (Entry 007), and harness engineering. Shares many elements: structured workflows, specialist behaviors, autonomous loops, self-healing/evaluation, SKILL.md, MCP, traces/reviews. Proactive tier (router + parallel child agents + review model) overlaps with Multica's issue assignment and gstack's role chaining. Goal-based + evaluator is a concrete implementation of self-healing docs and false-confidence audits from Jamon. Low redundancy — it's a practical "loops as autonomous employees" framework with specific autonomy tiers and a clear 14-step roadmap. High fit for evaluation criteria: Very High Relevance (autonomous loops + system design), High Integration (MCP, SKILL.md, worktrees), High Reproducibility (roadmap + specific patterns), Low Redundancy. Perfect for the repo's reproduction goal — easy to document as best-practice autonomous loop templates. Recommend: (1) Catalog as core autonomous workflows resource. (2) Strong candidate for reproduction scripts/templates in harness/ or examples/. (3) Synergistic with gstack/Multica for role-based + looped autonomous teams.
- **Status**: Processed and cataloged (added as major autonomous loops framework; high value for practical agentic system design)

### Entry 019: 7 Open Source Alternatives to Cursor/Perplexity/v0 (OpenHands, Zed, Codex, Scira, Morphic, December, Libra)

- **URL**: https://x.com/i/status/2076308228510765481
- **Date**: 2026-07-12 (post)
- **Poster**: Harman (@itsharmanjot)
- **Summary / Key Claims**: List of 7 open source repos that combine capabilities of Cursor, Perplexity, and v0 with zero waitlists, zero API markups, and zero vendor lock-in. Includes: OpenHands (agentic coding platform that plans, edits files, runs terminal commands, browses web autonomously — MIT); Zed (Rust-native AI editor, GPU-accelerated, open agent client protocol, 86k stars); Codex (OpenAI's official terminal coding agent in network-isolated containers, 94k stars, Apache 2.0); Scira (minimalist Perplexity alternative with citations and focus modes, 11.7k stars); Morphic (open source answer engine with generative UI streaming charts/comparisons, MIT); December (self-hosted v0/lovable alternative, $5 API credits for 50+ full app generations, Docker deploy); Libra (Cloudflare-native v0/Lovable alternative, serverless, free tier friendly, BYOK). Emphasizes closed source losing ground to open alternatives.
- **Extracted Repos / Tools**: OpenHands (MIT agentic coding platform); Zed (86k stars, open agent client protocol); Codex (94k stars, Apache 2.0, terminal coding agent in containers); Scira (11.7k stars, Perplexity alternative); Morphic (MIT answer engine with generative UI); December (self-hosted v0/lovable alternative); Libra (Cloudflare-native v0/Lovable alternative). Strong collection of open-source coding agents, editors, search/answer engines, and app generation tools.
- **TOOLS.md Link**: New rows under Agent Frameworks & Orchestration / Coding Agents (OpenHands, Zed, Codex) and Research/Search & Answer Engines (Scira, Morphic) and App Generation/UI Tools (December, Libra). High-signal open-source alternatives list.
- **Notes**: Excellent addition for reducing vendor lock-in and expanding open-source options in coding agents, AI editors, and app generation. OpenHands, Zed, and Codex have strong overlap with existing coding agent entries (Continue, Aider, ponytail, gstack, Multica, Spec Kit, Graphify, loops framework) — they are full agentic coding platforms or editors with agent protocols. Scira/Morphic add research/answer engine capabilities (less direct overlap, useful for context/research workflows). December/Libra add self-hosted v0/Lovable-style app generation (new but complementary to agentic coding). Low-to-medium redundancy overall — expands the open-source coding/agent ecosystem significantly. High fit for evaluation criteria: Very High Relevance (open-source alternatives to popular closed tools), High Integration (agent-compatible, Docker/self-hosted options), High Reproducibility (open source repos with clear licenses), Low Redundancy (broadens options without duplicating core frameworks). Perfect for the repo's open-source/self-hosted focus and reproduction goal. Recommend: (1) Catalog OpenHands, Zed, and Codex as core coding agent alternatives. (2) Add Scira/Morphic under research tools. (3) Note December/Libra as app generation complements. (4) Strong for local/self-hosted reproduction templates.
- **Status**: Processed and cataloged (added as major open-source alternatives resource; high value for expanding ecosystem options)

### Entry 020: Live Obsidian Business Network Graph (500+ Businesses, Real-Time ERP Sync)

- **URL**: https://x.com/i/status/2076341049480405440
- **Date**: 2026-07-12 (post)
- **Poster**: NO1ennn (@N01ennn)
- **Summary / Key Claims**: Real-world production example of a 34-year-old operator mapping 500+ businesses into one live Obsidian knowledge graph that updates in real time with every transaction from his internal ERP. Central node = operator; primary radials = business verticals; secondary connections = supplier/customer overlaps, shared employees, joint assets. Every business is a note; every deal/invoice/shared employee/joint asset creates or updates links. Graph auto-rewires on new data. Uses Obsidian's force-directed layout for real-time visualization. Primary use: identifying truly independent businesses vs. highly interdependent ones for merge/spin-off decisions. Contrasted with typical fragmented setup (multiple CRMs, spreadsheets, WhatsApp groups).
- **Extracted Repos / Tools**: No new standalone repo (production pattern using Obsidian + markdown + live ERP-to-vault sync). Pattern: live data pipeline from ERP → markdown notes in Obsidian vault → dynamic knowledge graph with force-directed visualization. Strong real-world validation of Obsidian as a scalable business intelligence / operations graph.
- **TOOLS.md Link**: New row under Personal Knowledge Management & Second Brain Workflows (or Business Intelligence / Operations Knowledge Graphs). High-signal real-world case study and pattern.
- **Notes**: **Excellent real-world complement and production-scale example of Entry 014 (Karpathy Second Brain / Obsidian + Claude Code Wiki)**. This is the enterprise/business-network version of the personal second brain concept — live data ingestion, dynamic linking, and visualization at massive scale (500+ entities). Strong overlap with **Graphify (Entry 017)** in the core idea of turning complex relational data into a queryable, visual knowledge graph (codebase vs. business network). Both emphasize "map once, query/visualize forever" with automatic updates. Low redundancy — this is a case study and pattern (live Obsidian + ERP sync) rather than a new tool or framework. High inspirational and reproduction value for anyone building knowledge graphs for operations, business intelligence, or complex networks. High fit for evaluation criteria: Very High Relevance (live knowledge graph at scale), High Reproducibility (Obsidian + markdown + ERP sync pattern is accessible), High Inspiration for local/self-hosted setups. Perfect for the repo's reproduction goal — document as best-practice example of Obsidian as a live business network graph. Recommend: (1) Catalog as major real-world case study. (2) Strong candidate for reproduction notes or templates showing ERP → Obsidian live sync patterns. (3) Synergistic with Entry 014 and Graphify for knowledge graph best practices across personal and business domains.
- **Status**: Processed and cataloged (added as major real-world knowledge graph case study; high value for scaling the second brain / graph pattern)

### Entry 021: Loop Engineering Guide 2026 — Structured Autonomous Agent Loops Framework

- **URL**: https://x.com/i/status/2076299893334016444 (and https://www.aibuilderclub.com/blog/loop-engineering-guide-2026)
- **Date**: 2026-07-12 (post)
- **Poster**: Roan (@RohOnChain)
- **Summary / Key Claims**: Points to a comprehensive free guide on "Loop Engineering" for AI agents — described as one of the best resources available. Covers structured approaches to building autonomous agent loops (including different autonomy models). Emphasizes that most AI engineers are unfamiliar with the term "loop engineering." Includes diagrams and practical setups. Strong focus on systematic, reliable agent loop design for production use.
- **Extracted Repos / Tools**: No new standalone repo (educational/practical guide). Key patterns: structured loop engineering with varying autonomy levels, systematic agent workflow design, likely covering goal-based, time-based, and proactive loops similar to other resources in the catalog.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Autonomous Loops & Agentic Workflows. High-signal dedicated guide on loop engineering.
- **Notes**: **Strong overlap with Entry 018 (Getting Started with Loops)** — both focus on structured autonomous agent loops with different autonomy tiers (turn-based, goal-based, time-based, proactive). This appears to be a more comprehensive or alternative guide to the same core concept of "loop engineering" for reliable agentic systems. Shares emphasis on system quality, evaluation, and moving beyond ad-hoc prompting. Low-to-medium redundancy — valuable to have multiple high-quality perspectives on this important topic. High fit for evaluation criteria: Very High Relevance (structured loop engineering for agents), High Reproducibility (dedicated free guide with practical setups), Low Redundancy when positioned as complementary resource. Perfect for the repo's reproduction goal — another strong source for autonomous loop best practices and templates. Recommend: (1) Catalog as major loop engineering resource. (2) Explicitly compare/contrast with Entry 018 (different models or depth of coverage). (3) Strong candidate for reproduction templates combining ideas from both guides. (4) Synergistic with gstack, Multica, and harness engineering entries for structured autonomous workflows.
- **Status**: Processed and cataloged (added as major loop engineering resource; explicit comparison to Entry 018 noted)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 022: BMAD-METHOD — 12+ Agent Agile AI Development Framework (50k+ stars)

- **URL**: https://x.com/i/status/2076271402047373519
- **Date**: 2026-07-12
- **Poster**: @ArchiveExplorer (highlighting Brian Madison of BMad Code, LLC / bmad-code-org)
- **Summary / Key Claims**: Open-sourced comprehensive AI-agile development framework with 12+ specialized agents (PM, Architect, Developer, UX Designer, Test Architect, Scrum Master, etc.) and 34–50+ guided workflows. Takes projects from brainstorm / PRD / architecture all the way to shipped code. Scale-adaptive intelligence that adjusts from simple bug fixes to enterprise systems. 100% free, no paywalls. Install via `npx bmad-method install`. Works with Claude Code and other AI coding agents. Strong emphasis on structured agentic planning, context-engineered development stories, and multi-agent collaboration. Massive adoption (~50k stars, MIT).
- **Extracted Repos / Tools**: Primary: https://github.com/bmad-code-org/BMAD-METHOD (main repo, ~50k stars). Ecosystem includes official modules (BMad Builder, Test Architect, Game Dev Studio) and community Claude Code plugins (e.g. https://github.com/aj-geddes/claude-code-bmad-skills).
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Multi-Agent Workflows & Structured Development (high-signal A-tier candidate).
- **Notes**: **Excellent high-signal addition to the catalog.** Direct relevance to our AgenC primary runtime + loop engineering work. Strong conceptual overlap with gstack (role specialization + workflows), Multica (team collaboration + skill compounding), Spec Kit (structured planning guardrails), and our own 4-tier autonomy + 14-step roadmap (Entry 018/021). The 12-agent team model + guided workflows is highly portable and production-proven. Low-to-medium redundancy — it's a mature, widely adopted framework rather than a new experimental tool. High fit for evaluation criteria: Very High Workflow Relevance (full lifecycle multi-agent orchestration), High Integration Ease (npx install + Claude Code compatible), High Reproducibility (open source, clear install), Medium Redundancy (extends existing patterns but at massive scale and maturity). Perfect for the repo's reproduction of best practices goal. Recommend: (1) Catalog as major multi-agent workflow framework. (2) Strong candidate for comparison/evaluation against our AgenC augmentation and loop engineering pack. (3) Potential to port/adapt specific workflow patterns or agent personas into our skills layer. (4) Note ecosystem plugins for Claude Code integration testing.
- **Status**: Processed and cataloged (added as major structured multi-agent development framework; high priority for deeper evaluation and potential pattern porting)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 023: Wigolo — Local-First MCP Web Search, Crawl & Research Server

- **URL**: https://x.com/i/status/2076346769970253947
- **Date**: 2026-07-12
- **Poster**: @0x0SojalSec (highlighting Wigolo by @yourtowhid / KnockOutEZ)
- **Summary / Key Claims**: Local-first MCP server that gives any AI agent full web capabilities (search, page fetch, full-site crawling, structured extraction) with zero API keys or cloud calls. Multi-engine search (18 sources) with local ML model reranking, aggressive caching (instant repeats), and headless browser escalation for blocked sites. Everything stays on your machine. Works out-of-the-box with Claude Code, Cursor, Codex, Gemini CLI, VS Code, Windsurf, Zed, Antigravity, and any MCP-compatible agent.
- **Extracted Repos / Tools**: Primary: https://github.com/KnockOutEZ/wigolo (local MCP server for web intelligence). npm: @staticn0va/wigolo. Strong local-first, keyless design with caching and fallback mechanisms.
- **TOOLS.md Link**: New row under Research/Search & Answer Engines or MCP Servers & Tooling (high-signal local tool). Strong fit for context augmentation and agent research workflows.
- **Notes**: **Excellent addition — directly relevant to our MCP-heavy AgenC integration and local agent goals.** Provides a complete local replacement for paid web search APIs. The caching + ML reranking + headless fallback combo is practical and production-oriented. Strong overlap with general MCP tool servers but stands out for its focus on reliable, cached, multi-engine web research without any external dependencies or costs. High fit for evaluation criteria: Very High Relevance (local web capabilities for agents), Very High Integration Ease (plain MCP, works with many agents including our AgenC target), High Reproducibility (open source, simple init), Low Redundancy (fills a clear gap in local research tooling). Perfect for the repo's self-hosted/local emphasis. Recommend: (1) Catalog as core local MCP research tool. (2) Strong candidate for integration testing with AgenC (add as MCP server in our augmentation layer). (3) Evaluate caching behavior and reranking quality in real agent loops. (4) Synergistic with loop engineering and skills for autonomous research tasks.
- **Status**: Processed and cataloged (added as high-value local MCP web research server; priority for MCP ecosystem expansion)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 024: Finn Loop — Structured Autonomous Coding Loop with Spec/Build/Review + Linear + Slack Approval

- **URL**: https://x.com/i/status/2076752798532931758
- **Date**: 2026-07-13
- **Poster**: Alex Finn (@AlexFinn)
- **Summary / Key Claims**: Practical implementation of a highly autonomous AI coding loop called the "Finn Loop". Uses 3 custom skills (/spec, /build, /review) across multiple agent sessions. /spec turns ideas into detailed Linear specs. /build loop autonomously implements specs and updates Linear status. /review loop performs security/optimization review, browser testing, screenshots, PR creation, and deploys to Vercel sandbox. Notifications sent via Slack with PR link, test steps, executive summary, and sandbox link. Merge triggered by simple rocket ship emoji reaction. Minimal human input: submit ideas + final approval. Claims dramatic productivity gains (100x output, 95% less manual work) by turning "vibe coding" into a mostly autonomous pipeline with clear human gate at the end.
- **Extracted Repos / Tools**: No new public repo yet (skills offered for release soon; workflow described in detail in the post). Strong pattern using Linear for spec/issue tracking + Slack for human approval signaling + Vercel for testing sandboxes. Directly implementable with existing agents (Claude Code, Codex, etc.) via custom skills.
- **TOOLS.md Link**: New entry under Agent Frameworks & Orchestration / Autonomous Loops & Agentic Workflows (high-value practical pattern). Strong complement to our loop engineering work.
- **Notes**: **Excellent real-world example that maps almost 1:1 to our loop engineering efforts (Entry 018/021/022).** The /spec + /build + /review structure is a concrete realization of goal-based + proactive loops with clear evaluator/review stages and human-in-the-loop approval via lightweight signaling (emoji reaction). Strong overlap with gstack role patterns, Multica issue assignment + autonomous execution, Spec Kit structured planning, and our own 4-tier autonomy + 14-step roadmap. The multi-session loop design (separate /build and /review loops) + external notification/approval channel is production-oriented and directly relevant to building robust autonomous systems on top of AgenC. Low redundancy — it's a high-signal workflow pattern rather than a new framework. High fit for evaluation criteria: Very High Relevance (autonomous coding loops with clear human gate), High Integration Ease (skill-based, works with existing agents), High Reproducibility (detailed steps in post; easy to recreate/adapt), Low Redundancy. Perfect for the repo's reproduction goal. Recommend: (1) Catalog as major practical autonomous loop example. (2) Strong candidate for direct adaptation into our loop-engineering skill pack or new AgenC skills (e.g., spec-builder, autonomous-builder, review-with-sandbox). (3) Monitor for the promised skill releases. (4) Synergistic with our existing loop engineering + harness work for production-grade agent loops.
- **Status**: Processed and cataloged (added as high-value real-world autonomous coding loop pattern; priority for integration into loop-engineering skills)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 025: all-agentic-architectures — Benchmark Comparison of 35 Agentic AI Architectures

- **URL**: https://x.com/i/status/2076628874918560153
- **Date**: 2026-07-13
- **Poster**: Tom Dörr (@tom_doerr)
- **Summary / Key Claims**: Comprehensive comparison of 35 different agentic AI architectures against a 17-task benchmark leaderboard. Provides a structured way to evaluate and compare various agent designs, frameworks, and patterns. Includes a GitHub repository with the architectures and benchmark results.
- **Extracted Repos / Tools**: Primary: https://github.com/FareedKhan-dev/all-agentic-architectures — Library comparing 35 agentic architectures on a 17-task benchmark.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Benchmarks & Evaluation (high-value evaluation resource).
- **Notes**: **Strong addition for our evaluation strategy.** Directly supports the repo's goal of rigorous evaluation and reproduction of best practices. Useful for comparing our AgenC augmentation + loop engineering approaches against other agentic patterns. The 17-task benchmark provides concrete metrics for assessing autonomy tiers, workflow robustness, and tool-use effectiveness. High fit for evaluation criteria: Very High Relevance (agent architecture benchmarking), High Integration Ease (reference library for comparison), High Reproducibility (open benchmark results), Low Redundancy (fills evaluation gap). Recommend: (1) Catalog as core benchmark resource. (2) Use as reference when refining our own evaluation rubric for loop engineering and AgenC skills. (3) Consider running subsets of the 17 tasks against our implementations for objective comparison.
- **Status**: Processed and cataloged (added as major agentic architecture benchmark resource; high value for evaluation framework)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 026: /last30days — Multi-Platform Research Skill for Agents (X, Reddit, YouTube, arXiv, HN, etc.)

- **URL**: https://x.com/i/status/2076380344631398606
- **Date**: 2026-07-12
- **Poster**: Shubham Saboo (@Saboo_Shubham_)
- **Summary / Key Claims**: Highly practical open-source agent skill called `/last30days` that lets any coding/research agent instantly read and synthesize content from X, Reddit, YouTube, TikTok, Instagram, arXiv, Hacker News, and Polymarket in a single command. Described as "insanely useful" for keeping agents up to date with recent developments across platforms. Recommended to combine with strong models (e.g., Fable 5 + GPT-5.6) for best results. Backed by the popular @slashlast30days project (47k+ stars).
- **Extracted Repos / Tools**: Primary related project: @slashlast30days (https://github.com/slashdev or associated repo, 47k+ stars). The `/last30days` skill itself is highlighted as a powerful, ready-to-use addition for agent workflows.
- **TOOLS.md Link**: New row under Research/Search & Answer Engines or Skills & Prompt Engineering (high-signal practical skill). Strong fit for agent research and context-gathering capabilities.
- **Notes**: **Excellent high-signal addition.** Directly complements our loop engineering, skills pack, and AgenC augmentation work. The ability for an agent to rapidly ingest recent information across multiple platforms in one command is extremely valuable for autonomous research loops, context building, and staying current without manual intervention. Strong overlap with general research tools but stands out for its breadth (social + academic + news + prediction markets) and simplicity. High fit for evaluation criteria: Very High Relevance (multi-platform research skill for agents), Very High Integration Ease (simple skill/command, works with existing agents), High Reproducibility (open-source skill pattern), Low Redundancy. Perfect for the repo's skills and autonomous workflow focus. Recommend: (1) Catalog as major practical research skill. (2) Strong candidate for adaptation/porting into our loop-engineering or skills layer (especially for proactive research in autonomous loops). (3) Evaluate integration with MCP or as a reusable SKILL.md pattern. (4) Synergistic with existing research patterns in the catalog.
- **Status**: Processed and cataloged (added as high-value multi-platform agent research skill; priority for skills integration)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 027: Four Types of Agent Loops — Turn-based, Goal-based, Time-based, Proactive (Detailed Breakdown)

- **URL**: https://x.com/i/status/2076748259377516782
- **Date**: 2026-07-13
- **Poster**: Akshay Pachaar (@akshay_pachaar)
- **Summary / Key Claims**: Excellent structured breakdown of the four main types of agent loops in "loop engineering." Clarifies that loop engineering is about designing the system that steers the agent (answering "what starts a run" and "what decides the work is done") rather than hand-holding move-by-move. The four types progressively hand off more control to the system:
  1. **Turn-based**: User prompt triggers; agent acts + self-checks in one turn; human reviews and writes next prompt. Best for exploratory work where requirements are still forming.
  2. **Goal-based**: /goal command with success criteria + budget triggers; evaluator model checks output and loops back if goal not met. Best for measurable outcomes.
  3. **Time-based**: Clock/interval triggers fixed prompt (e.g., "check PR, fix CI"); /loop locally or /schedule to cloud. Best for recurring known tasks.
  4. **Proactive**: Event/schedule triggers with no human present; spawns workflow with triage/fix/reviewer agents that adversarially judge work. Best for standing responsibilities.
  Emphasizes choosing the right loop structure based on task type (exploratory, measurable, recurring, or standing) rather than chasing the "most advanced" one.
- **Extracted Repos / Tools**: No new standalone repo (pattern/framework explanation). References a full loop engineering article. Strong conceptual alignment with existing autonomous loop resources.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Autonomous Loops & Agentic Workflows (high-signal reinforcement of loop engineering patterns).
- **Notes**: **Very strong addition — directly reinforces and expands our existing loop engineering work (Entries 018, 021, 024).** The four-type breakdown (turn-based → goal-based → time-based → proactive) maps cleanly onto our 4-tier autonomy model and 14-step roadmap. The emphasis on system design over manual steering, plus concrete triggers and use-case mapping, is highly actionable for building robust skills and harnesses on top of AgenC. Strong overlap with goal-based evaluators, scheduled loops, and proactive router patterns we're already cataloging. Low redundancy — this is excellent pedagogical reinforcement with clear task-type mapping. High fit for evaluation criteria: Very High Relevance (structured loop types + decision framework), High Integration Ease (patterns directly portable to skills), High Reproducibility (clear breakdown + use cases), Low Redundancy. Perfect for the repo's reproduction and skills development goals. Recommend: (1) Catalog as major loop engineering resource. (2) Strong candidate for direct integration into our loop-engineering skill pack (e.g., as a decision guide or expanded 4-tier documentation). (3) Use as reference when refining autonomy tier definitions and evaluator patterns.
- **Status**: Processed and cataloged (added as high-value reinforcement of loop engineering patterns; priority for skills integration)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 028: fable-method — Structured Problem-Solving Loop + Adversarial Verification for Any Model

- **URL**: https://x.com/i/status/2076727080402948561
- **Date**: 2026-07-13
- **Poster**: Alex Prompter (@alex_prompter)
- **Summary / Key Claims**: Distills Fable's problem-solving approach into an installable plugin any model can use. Contains three main components:
  - `fable-method`: Structured problem-solving loop with hard failure thresholds.
  - `fable-loop`: Runs full tasks with adversarial verification agents that check the work.
  - `fable-judge`: Treats every "done, all tests pass" claim as unverified and independently re-runs verification.
  Strong measured results on catching wrong tests, false completion claims, and planted frauds (e.g., Haiku went from 0/4 to 4/4 on catching wrong tests; Sonnet + plugin matched Fable itself on complex research tasks). Importantly, it adds little overhead on ordinary tasks with capable models — value concentrates on traps and weaker/unattended models. MIT licensed with all evaluation transcripts committed. Installable in Claude Code via plugin marketplace.
- **Extracted Repos / Tools**: Primary: https://github.com/Sahir619/fable-method (MIT, full eval transcripts included). Plugin for Claude Code that brings structured verification loops to any model.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Autonomous Loops & Verification (high-signal verification/hardening tool). Strong fit for loop engineering and agent robustness.
- **Notes**: **Excellent high-signal addition.** Directly complements and extends our loop engineering work (especially goal-based evaluators, adversarial review, and self-healing patterns from Entries 018/021/024/027). The adversarial verification + hard failure thresholds + independent judge approach is a concrete, evaluated implementation of robust goal-based and proactive loops. Strong emphasis on catching false positives in agent output is highly relevant for production hardening. Low-to-medium redundancy — it's a focused verification layer rather than a full framework. High fit for evaluation criteria: Very High Relevance (structured verification + adversarial loops), High Integration Ease (plugin format, works with existing agents), High Reproducibility (MIT + full transcripts), Low Redundancy. Perfect for the repo's focus on reliable autonomous systems. Recommend: (1) Catalog as major verification/hardening resource. (2) Strong candidate for adaptation into our loop-engineering skill pack (e.g., as a fable-method inspired evaluator or judge skill). (3) Excellent for hardening AgenC-based workflows, especially with weaker models or unattended runs.
- **Status**: Processed and cataloged (added as high-value adversarial verification loop resource; priority for skills integration)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 029: Pliny Tools Ecosystem (Jailbreaks, System Prompt Leaks, Multi-Agent Hackbot, Red Teaming)

- **URL**: https://x.com/i/status/2076760743673053681
- **Date**: 2026-07-13
- **Poster**: Mike Takahashi (@TakSec)
- **Summary / Key Claims**: Breakdown of tools and projects by @elder_plinius (Pliny). Includes:
  - L1B3RT4S: Jailbreak prompts
  - G0DM0D3: Unrestricted AI
  - 0BL1T3R4TUS: Abliteration for open-source LLMs
  - CL4R1T4S: Leaked system prompts
  - LeakHub: Community platform for system prompt leaks
  - P4RS3LT0NGV3: Jailbreak payload builder
  - T3MP3ST: Multi-agent hackbot swarm
  - ST3GG: Steganography toolkit
  - V3SP3R: Natural language control for Flipper Zero
  Central hub at pliny.gg. Focused on AI red teaming, jailbreaking, prompt extraction, and offensive tooling.
- **Extracted Repos / Tools**: Central site: https://pliny.gg/. Individual tools include jailbreak libraries, system prompt leak collections, multi-agent offensive swarms (T3MP3ST), and related red team utilities. No single dominant high-star repo highlighted; ecosystem-oriented.
- **TOOLS.md Link**: Low priority / awareness note under Security / Red Teaming (if added at all). Limited direct fit for core catalog.
- **Notes**: **Lower relevance to core repo goals.** This is primarily an offensive/red teaming and jailbreaking ecosystem. While T3MP3ST (multi-agent hackbot swarm) has some conceptual overlap with multi-agent orchestration and loop engineering, the overall focus on jailbreaks, unrestricted models, prompt leaking, and hacking tools does not strongly align with the repo's emphasis on productive, reliable, local/self-hosted agent frameworks, skills, and workflows. The multi-agent aspect (T3MP3ST) could be noted as an extreme/offensive counterpart to our more constructive loop engineering and gstack-style patterns, but it is not a priority for cataloging or reproduction. Recommend: Track at awareness level only for red teaming/safety context. Do not prioritize for TOOLS.md or deep evaluation unless specific red team use cases emerge.
- **Status**: Processed and cataloged (added with low-relevance note; awareness-level entry for red teaming ecosystem)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 030: Advanced Claude Workflows & Skills Compilation (Loops, Second Brain, MCP, Skills Building)

- **URL**: https://x.com/i/status/2076629724315697287
- **Date**: 2026-07-13
- **Poster**: Hamza Khalid (@humzaakhalid)
- **Summary / Key Claims**: Comprehensive collection of advanced Claude usage resources covering:
  - Building and using Claude Skills
  - How to Build Loops + 7 Advanced Claude Loops
  - Claude + Obsidian for Second Brain / personal knowledge management
  - Claude + Higgsfield MCP integration
  - Using Fable 5 effectively
  - Claude in Excel, Artifacts, Chrome, Connectors
  - Fixing broken Claude code
  - Design patterns from Anthropic engineers
  - Advanced workflows (financial analysis, learning anything, faceless YouTube, etc.)
  - Avoiding Claude's limits and common skills mistakes
  Strong emphasis on practical, production-grade agentic workflows and skill development.
- **Extracted Repos / Tools**: No single new repo; collection of high-quality guides and patterns. Strong focus on skills, loops, Obsidian integration, and MCP usage.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Skills & Prompt Engineering and Autonomous Loops & Agentic Workflows (high-signal workflow compilation).
- **Notes**: **High relevance.** This is an excellent curated set of advanced Claude workflows that directly overlaps with our loop engineering (Entries 018/021/024/027), skills development, second brain patterns (Entry 014/020), and MCP integration work. The emphasis on building reusable skills, structured loops, and Obsidian + MCP for knowledge compounding is highly aligned with the repo's goals. Strong candidate for reproduction and adaptation. High fit for evaluation criteria: Very High Relevance (skills + loops + second brain + MCP), High Integration Ease (patterns are portable), High Reproducibility (detailed guides), Low Redundancy. Recommend: (1) Catalog as major workflow/skills resource. (2) Strong candidate for extracting and adapting patterns into our loop-engineering skill pack and AgenC augmentation layer (especially loop building, skills mistakes to avoid, and Obsidian/MCP second brain setups). (3) Excellent reference material for enhancing AGENTS.md and project-process documentation.
- **Status**: Processed and cataloged (added as high-value advanced workflows and skills compilation; priority for skills/loop integration)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 031: Iterative Feedback Loop for LLMs (Generate → Test → Update Context → Repeat)

- **URL**: https://x.com/i/status/2076657357078016229
- **Date**: 2026-07-13
- **Poster**: Lunar (@LunarResearcher)
- **Summary / Key Claims**: Highlights a paper that transforms LLMs from one-shot oracles into iterative feedback machines using the loop: **generate → test → update context → repeat**. The key idea is that each answer carries forward evidence from previous iterations, rather than just "trying again." This architecture helps agents stop hallucinating forward by building cumulative, evidence-based context. The poster calls it "dangerously powerful" and suggests it could become the default architecture for reliable agent loops.
- **Extracted Repos / Tools**: Paper referenced (not directly linked in post; focuses on the iterative feedback loop pattern). Strong conceptual alignment with self-healing, goal-based evaluation, and context management in agent systems.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Autonomous Loops & Agentic Workflows (high-signal feedback loop pattern).
- **Notes**: **High relevance.** This directly reinforces and extends our loop engineering work (especially goal-based evaluators, self-healing patterns, and context accumulation from Entries 018/021/024/027/030). The generate-test-update context loop is a clean, powerful formulation of iterative verification and evidence-carrying that reduces hallucinations in autonomous runs. Strong overlap with adversarial verification (fable-method style) and our emphasis on system quality over ad-hoc prompting. High fit for evaluation criteria: Very High Relevance (iterative feedback + context accumulation), High Integration Ease (pattern is portable to skills/evaluators), High Reproducibility (clear loop structure), Low Redundancy. Excellent for the repo's reproduction goals. Recommend: (1) Catalog as major feedback/iterative loop resource. (2) Strong candidate for direct integration into our loop-engineering skill pack (e.g., as a core evaluator or self-healing context pattern). (3) Use as reference when refining goal-based and proactive loop implementations for AgenC.
- **Status**: Processed and cataloged (added as high-value iterative feedback loop pattern; priority for skills integration)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 032: Eval Loop — Rubric-Driven Verification to Eliminate AI Slop

- **URL**: https://x.com/i/status/2076669336853606446
- **Date**: 2026-07-13
- **Poster**: Shann³ (@shannholmberg)
- **Summary / Key Claims**: Excellent practical framework for an "eval loop" to prevent AI slop. Core idea: Better prompts and bigger models aren't enough — you need a structured evaluation layer that catches low-quality output before it reaches the user. The base loop is:
  1. Write a specific rubric first (the quality bar)
  2. Agent drafts as usual
  3. Model scores the draft against the rubric (0-1 score)
  4. Anything below the bar goes back for another pass
  5. Every miss caught becomes a permanent new line in the rubric
  Layers of increasing rigor: Self-check → Independent check → LLM council (multiple models) → Human as final gate. Match the layer to the stakes of the output. The rubric acts as a living quality net that improves over time.
- **Extracted Repos / Tools**: No new standalone repo (framework/pattern). Strong conceptual and practical alignment with goal-based evaluation and self-healing loops.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Autonomous Loops & Agentic Workflows (high-signal eval/verification pattern).
- **Notes**: **High relevance.** This is an outstanding practical reinforcement of our loop engineering work (especially goal-based evaluators, self-healing patterns, and adversarial verification from Entries 018/021/024/027/031). The rubric-driven scoring + iterative improvement of the rubric itself is a clean, implementable way to build reliable evaluation into agent loops. The layered approach (self-check to council to human) gives clear guidance on trading off cost vs. rigor. Strong overlap with fable-method style verification and the generate-test-update feedback loop. High fit for evaluation criteria: Very High Relevance (rubric-driven eval loops), High Integration Ease (patterns are directly portable to skills), High Reproducibility (clear step-by-step framework), Low Redundancy. Excellent for the repo's reproduction goals. Recommend: (1) Catalog as major eval loop resource. (2) Strong candidate for direct integration into our loop-engineering skill pack (e.g., as a rubric-driven evaluator skill or self-healing pattern). (3) Highly actionable for hardening AgenC-based autonomous workflows and reducing low-quality outputs.
- **Status**: Processed and cataloged (added as high-value rubric-driven eval loop resource; priority for skills integration)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 033: Local Voice-Controlled Jarvis AI Assistant (Always-On Desktop Agent)

- **URL**: https://x.com/i/status/2076797326769701041
- **Date**: 2026-07-13
- **Poster**: Stefan (@paradeevic)
- **Summary / Key Claims**: Practical build of a local, always-on voice-controlled AI assistant ("Jarvis") running on a small desktop board. Replaces typing prompts with natural voice commands. The agent listens, understands, executes tasks (maps, tracking, opening apps, running commands), and responds verbally. No chat windows, no copy-paste, no subscriptions. Runs fully locally with no recurring costs. Described as feeling like "having someone on staff who never sleeps." Includes a full build guide in the linked article.
- **Extracted Repos / Tools**: Local hardware + software setup for voice-controlled agent (specific repo not named in post; build guide in linked article). Strong emphasis on local, always-on, voice-first agent experience.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Voice & Always-On Agents or Local Hardware Setups (practical local agent build).
- **Notes**: **Good relevance for local/self-hosted setups.** This is a concrete example of building an always-on, voice-driven local agent that handles real tasks without constant user intervention. Aligns with our interest in autonomous/background agents, local tooling, and reducing friction in agent interaction. The "never sleeps" always-on aspect is particularly relevant to proactive/time-based loops and desktop agent harnesses. While not a new major framework, the practical build + voice interface makes it useful for local agent experimentation. High fit for evaluation criteria: High Relevance (local always-on voice agent), High Integration Ease (buildable on standard hardware), High Reproducibility (full guide provided), Low Redundancy. Recommend: (1) Catalog as practical local agent build example. (2) Useful reference for anyone wanting to add voice interfaces or always-on desktop agents to the stack. (3) Synergistic with local hardware experiments and background agent patterns.
- **Status**: Processed and cataloged (added as practical local always-on voice agent build; useful for local setups)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 034: Understand-Anything — Interactive Codebase Knowledge Graph for Onboarding & Agent Context

- **URL**: https://x.com/i/status/2076562526507315534
- **Date**: 2026-07-13
- **Poster**: Zane Chen (@chenzeling4)
- **Summary / Key Claims**: Understand-Anything turns any codebase (even 200K+ lines you didn't write) into an interactive knowledge graph. Features: search, click through dependencies, ask questions in plain English. Designed to make onboarding dramatically faster. Works with Claude Code, Codex, Cursor, Copilot, Gemini CLI. Described as "what onboarding should feel like."
- **Extracted Repos / Tools**: Primary: Understand-Anything (repo linked in post, ~73.7K stars claimed). Codebase-to-knowledge-graph tool with natural language querying and dependency visualization. Strong agent integration (works with major coding agents).
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Codebase Knowledge Graph & Memory (high-signal graph tool for agents).
- **Notes**: **High relevance — strong complement to Graphify (Entry 017).** Both tools turn codebases into queryable knowledge graphs for agents. Understand-Anything emphasizes interactive exploration and plain-English questions, making it particularly strong for onboarding and rapid context building when joining new codebases. Excellent fit for agent context optimization and reducing the "staring at 200K lines" problem. High fit for evaluation criteria: Very High Relevance (codebase knowledge graph + agent integration), High Integration Ease (works with Claude Code/Cursor/etc.), High Reproducibility (open source with claimed high stars), Low-to-Medium Redundancy (complements Graphify with different interaction model). Recommend: (1) Catalog as major codebase graph tool. (2) Strong candidate for comparison/evaluation against Graphify and codebase-memory-mcp. (3) Useful for agent onboarding workflows and context layer in loop engineering.
- **Status**: Processed and cataloged (added as high-value codebase knowledge graph tool; priority for context/graph category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 035: Penpot — Open-Source Figma Alternative with MCP Server for AI Agents

- **URL**: https://x.com/i/status/2076629090778726866
- **Date**: 2026-07-13
- **Poster**: Simplifying AI (@simplifyinAI)
- **Summary / Key Claims**: Penpot is a free, open-source design tool that mirrors Figma's layout and workflow. Key features for agents:
  - MCP server that lets AI agents edit designs directly
  - Free Dev Mode with instant CSS, SVG, and HTML export
  - Native design tokens for keeping design and code in sync
  - Real-time collaboration built in
  100% free and self-hostable. Strong positioning as the open-source Figma alternative with native AI/agent integration via MCP.
- **Extracted Repos / Tools**: Primary: https://github.com/penpot/penpot (open source Figma alternative with MCP server for AI agents).
- **TOOLS.md Link**: New row under MCP Servers & Tooling or Design & Dev Tools (high-signal MCP-enabled design tool).
- **Notes**: **Good relevance for MCP ecosystem.** The standout feature is the MCP server that allows AI agents to directly edit designs. This aligns well with our heavy focus on MCP integration (AgenC, skills, agent tooling). While not a core agent framework, the MCP capability makes it a useful addition for design-to-code workflows and agent-driven design tasks. High fit for evaluation criteria: High Relevance (MCP server for design editing), High Integration Ease (MCP-native), High Reproducibility (open source, self-hostable), Low Redundancy. Recommend: (1) Catalog as MCP-enabled design tool. (2) Useful for anyone building agent workflows that involve design or UI generation. (3) Synergistic with MCP-focused parts of the catalog.
- **Status**: Processed and cataloged (added as MCP-enabled design tool; useful for MCP ecosystem)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 036: ordinary-claude-skills — Local Aggregator for Hundreds of Official & Community Claude Skills

- **URL**: https://x.com/i/status/2076941101802328117
- **Date**: 2026-07-14
- **Poster**: Tom Dörr (@tom_doerr)
- **Summary / Key Claims**: Tool that aggregates hundreds of official and community-built Claude skills locally. Makes it easy to discover, manage, and use a large collection of SKILL.md-style skills without manual hunting across repos or marketplaces.
- **Extracted Repos / Tools**: Primary: https://github.com/Microck/ordinary-claude-skills — Local aggregator for Claude skills.
- **TOOLS.md Link**: New row under Skills & Prompt Engineering or Agent Frameworks & Orchestration (high-signal skills management tool).
- **Notes**: **High relevance for skills ecosystem.** Directly supports our heavy focus on skills development, loop engineering, and building augmentation layers. Having a local aggregator for hundreds of skills makes it much easier to curate, test, and integrate useful patterns into our own skill packs or AgenC plugins. Strong complement to existing skills resources (Matt Pocock, marketing-council, gstack patterns, etc.). High fit for evaluation criteria: Very High Relevance (skills aggregation and discovery), High Integration Ease (local tool, easy to adopt), High Reproducibility (open source), Low Redundancy. Recommend: (1) Catalog as skills management/discovery tool. (2) Strong candidate for use in curating and expanding our loop-engineering and other skill packs. (3) Useful for anyone building large local skill libraries.
- **Status**: Processed and cataloged (added as high-value local skills aggregator; priority for skills category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 037: Claude as a Full Company — 122 Skills Across 7 Departments (Org Chart Style Skill Stack)

- **URL**: https://x.com/i/status/2076601521169387563
- **Date**: 2026-07-13
- **Poster**: Ronin (@DeRonin_)
- **Summary / Key Claims**: Practical example of turning Claude into a full "company" using 122 installable skills across 7 departments (Engineering, Design, Marketing, Social Media, Finance, Operations, Legal). Includes specific high-signal repos like Superpowers (engineering planning), Context7 (live docs), UI UX Pro Max, large marketing/social skills packs, finance/operations/legal skills, etc. Core philosophy: "a company used to be people. now it's a folder of markdown files." Emphasizes starting with your bottleneck rather than installing everything. Strong real-world example of scaling agent capabilities through curated, role-based skills.
- **Extracted Repos / Tools**: Multiple linked repos including https://github.com/obra/superpowers, Context7, UI UX Pro Max, large marketing skills pack, and various department-specific skill collections. Org-chart style organization of 122+ skills.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Skills & Prompt Engineering (high-signal large-scale skill stack example).
- **Notes**: **High relevance.** This is an excellent real-world example of the "Claude Company Org Chart" pattern (Entry 016) taken to production scale ($40k MRR solo agency). Directly aligns with our skills development, loop engineering, and building robust multi-role agent systems. The org-chart structure + bottleneck-first approach is highly practical. Strong overlap with gstack-style role specialization and our own efforts to build composable skills. High fit for evaluation criteria: Very High Relevance (large curated skill org + real usage), High Integration Ease (installable skills), High Reproducibility (specific repos linked), Low Redundancy. Recommend: (1) Catalog as major large-scale skills/org example. (2) Strong candidate for studying curation patterns and adapting department/role structures into our own skill packs. (3) Excellent reference for scaling agent teams beyond single roles.
- **Status**: Processed and cataloged (added as high-value large-scale skill org example; priority for skills category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 038: MLX Studio — Local LLM & Image Model Runner for macOS (Apple Silicon)

- **URL**: https://x.com/i/status/2076950094620799371
- **Date**: 2026-07-14
- **Poster**: Tom Dörr (@tom_doerr)
- **Summary / Key Claims**: MLX Studio is a tool for running large language and image models locally on macOS using Apple's MLX framework. Optimized for Apple Silicon, providing an easy way to run powerful local models without cloud dependencies.
- **Extracted Repos / Tools**: Primary: https://github.com/jjang-ai/mlxstudio — Local model runner for macOS using MLX.
- **TOOLS.md Link**: New row under Inference & Serving (local macOS inference tool).
- **Notes**: **Good relevance for local macOS users.** Provides a convenient GUI/tooling layer on top of Apple's MLX framework for running LLMs and image models locally. Fits the local/self-hosted inference category, especially for users on Apple hardware. While not as general-purpose as some cross-platform options, it's a strong native macOS solution. High fit for evaluation criteria: High Relevance (local macOS inference), High Integration Ease (easy to use on Apple Silicon), High Reproducibility (open source), Low Redundancy. Recommend: (1) Catalog as local macOS inference tool. (2) Useful addition for users on Apple hardware looking for optimized local model running.
- **Status**: Processed and cataloged (added as local macOS inference tool; useful for Apple Silicon users)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 039: CLAUDE.md — 192k-Star Behavioral Guidelines File for Claude Code (Karpathy-Inspired)

- **URL**: https://x.com/i/status/2077032502993256646
- **Date**: 2026-07-14
- **Poster**: Akshay Pachaar (@akshay_pachaar)
- **Summary / Key Claims**: A single CLAUDE.md file (derived from Andrej Karpathy's coding rules) has reached 192k GitHub stars. It provides structured behavioral guidelines for Claude Code to prevent common LLM coding mistakes: over-engineering, ignoring existing patterns, and adding unnecessary dependencies. You simply drop one .md file into your repo, and it shapes the AI's behavior across the entire project. Emphasizes moving from "use AI to write code" to "engineer the AI's behavior so the code is actually good." 100% open-source, prompt-engineering focused, no complex tooling required.
- **Extracted Repos / Tools**: Primary repo for the CLAUDE.md template (linked in post). Strong conceptual overlap with AGENTS.md, project context files, and structured instruction patterns.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Context & Prompt Engineering (high-signal behavioral guidelines pattern).
- **Notes**: **Very high relevance.** This is an excellent real-world validation of the power of well-crafted markdown instruction files for guiding agent behavior (directly analogous to our AGENTS.md, project-process files, and skills). The Karpathy-inspired approach to preventing predictable LLM mistakes through explicit guidelines is highly aligned with our focus on reliable agent workflows and context engineering. Strong overlap with second brain patterns and structured prompting. High fit for evaluation criteria: Very High Relevance (behavioral guidelines / context files for agents), High Integration Ease (simple .md file), High Reproducibility (open source, widely adopted), Low Redundancy. Recommend: (1) Catalog as major context/instruction file pattern. (2) Strong candidate for studying and adapting into our own AGENTS.md and project scaffolding. (3) Excellent reference for improving agent output quality through better system-level instructions.
- **Status**: Processed and cataloged (added as high-value behavioral guidelines / context file resource; priority for context and agent scaffolding category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 040: BrowserOS — Open-Source Agentic Chromium Browser for Local AI Agents

- **URL**: https://x.com/i/status/2077011759114973616
- **Date**: 2026-07-14
- **Poster**: Brian Roemmele (@BrianRoemmele)
- **Summary / Key Claims**: BrowserOS is an open-source, privacy-first, agentic Chromium browser that brings powerful local AI automation to everyday users. It allows running AI agents directly in the browser on your own machine. Highlights "agents running agents" setups (e.g., at The Zero-Human Company). Designed to democratize serious agentic capabilities beyond big-tech labs or expensive enterprise tools.
- **Extracted Repos / Tools**: BrowserOS (open-source agentic browser project). Strong focus on local, privacy-first agent execution in a browser environment.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Browser & Local Agent Tools (high-signal local agentic browser).
- **Notes**: **High relevance for local agent tooling.** BrowserOS represents a significant step toward making powerful local AI agents accessible and integrated into everyday browsing workflows. The "agents running agents" concept and privacy-first local execution align well with our focus on autonomous loops, local tooling, and reducing dependency on cloud services. Useful for exploring browser-native agent interfaces and always-on local automation. High fit for evaluation criteria: Very High Relevance (local agentic browser + agents running agents), High Integration Ease (Chromium-based, local), High Reproducibility (open source), Low Redundancy. Recommend: (1) Catalog as major local agentic browser tool. (2) Strong candidate for experimentation with browser-based agent interfaces and multi-agent local setups. (3) Synergistic with local hardware/agent harness work.
- **Status**: Processed and cataloged (added as high-value local agentic browser resource; priority for local tooling category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 041: destructive_command_guard — Safety Guard for Coding Agents Against Destructive Commands

- **URL**: https://x.com/i/status/2076855961189507099
- **Date**: 2026-07-14
- **Poster**: Shubham Saboo (@Saboo_Shubham_)
- **Summary / Key Claims**: Free, open-source tool that works with all coding agents to prevent destructive commands (e.g., accidental file deletion like the GPT-5.6-Sol incident). Acts as a safety guardrail for agentic coding workflows.
- **Extracted Repos / Tools**: Primary: https://github.com/Dicklesworthstone/destructive_command_guard — Safety layer for coding agents.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Safety & Guardrails (high-signal safety tool for agents).
- **Notes**: **High relevance for agent safety.** Directly addresses a critical pain point in agentic coding: preventing catastrophic mistakes from powerful but unguardrailed agents. Fits perfectly with our focus on reliable, hardened agent workflows (e.g., agent-cage isolation, verification/eval loops, adversarial checking). Strong complement to safety-focused patterns in loop engineering and harness engineering. High fit for evaluation criteria: Very High Relevance (agent safety guardrails), High Integration Ease (works with all coding agents), High Reproducibility (open source), Low Redundancy. Recommend: (1) Catalog as major agent safety tool. (2) Strong candidate for integration/testing with our harness and loop engineering setups. (3) Excellent reference for building or evaluating safety layers in autonomous agent systems.
- **Status**: I2 probe 2026-11-07. Pin v0.16.0 commit 665fcd8fc62cb5941e0484ddab012419f146523d. write-guard shell ops 0; dcg denied 12/12 destructive commands. Receipt: eval/evq1107/destructive-command-guard/REPORT.md. Not a gate.

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 042: ODS (Osmantic) — One-Click Local AI Server with Hardware Detection & Model Optimization

- **URL**: https://x.com/i/status/2076763287220318468
- **Date**: 2026-07-13
- **Poster**: Ahmad (@TheAhmadOsman)
- **Summary / Key Claims**: ODS makes local AI extremely easy: Install → hardware detection → auto-downloads best model for your hardware → starts local inference + Open WebUI. Supports adding voice, agents (e.g. Hermes), workflows, RAG, search, image generation, etc., all managed from one dashboard. Turns any PC/Mac/Linux into a private AI server with no cloud or subscription required. Data stays local by default.
- **Extracted Repos / Tools**: Primary: https://github.com/Osmantic/ODS — Local AI stack manager with hardware-aware model selection and unified dashboard.
- **TOOLS.md Link**: New row under Inference & Serving / Local AI Stacks (high-signal easy local AI deployment tool).
- **Notes**: **High relevance for local/self-hosted setups.** ODS directly addresses one of the biggest barriers to local AI adoption: complex setup and model/hardware matching. The hardware detection + optimized model download + unified dashboard for agents/workflows/RAG/etc. makes it a strong practical tool for quickly standing up local AI environments. Aligns well with our focus on accessible local tooling and agent frameworks. High fit for evaluation criteria: Very High Relevance (easy local AI deployment), High Integration Ease (one-click style with dashboard), High Reproducibility (open source), Low Redundancy. Recommend: (1) Catalog as major local AI stack/deployment tool. (2) Strong candidate for testing as a quick way to bootstrap local environments for evaluation and development. (3) Useful for lowering the barrier to experimenting with local agents and workflows.
- **Status**: Processed and cataloged (added as high-value local AI deployment tool; priority for local tooling category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 043: clawe — Open-Source Trello Alternative for OpenClaw Agents

- **URL**: https://x.com/i/status/2077068280007663912
- **Date**: 2026-07-14
- **Poster**: Tom Dörr (@tom_doerr)
- **Summary / Key Claims**: clawe is an open-source Trello-style project management tool built specifically for OpenClaw agents. Provides a structured board/task interface tailored for AI agent workflows and collaboration.
- **Extracted Repos / Tools**: Primary: https://github.com/getclawe/clawe — Open-source Trello alternative for agents.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Agent Task Management & Boards (high-signal agent-specific PM tool).
- **Notes**: **Good relevance for agent orchestration.** Provides a visual task/board interface optimized for AI agents (OpenClaw). This complements tools like Multica (issue assignment and team boards for agents) and helps structure agent work in a human-friendly way. Useful for agent team management, task tracking, and making autonomous workflows more observable and manageable. High fit for evaluation criteria: High Relevance (agent-specific task management), High Integration Ease (open source, agent-focused), High Reproducibility (open source), Low Redundancy. Recommend: (1) Catalog as agent task/board management tool. (2) Useful addition for structuring and visualizing agent work, especially in multi-agent or long-running loop setups. (3) Synergistic with Multica and other agent team/orchestration tools.
- **Status**: Processed and cataloged (added as agent-specific task management tool; useful for agent workflows)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 044: Memvid — MP4-Based Agent Memory System (Git-like Versioning, Rewind, Replay, Branch)

- **URL**: https://x.com/i/status/2077064295209443504
- **Date**: 2026-07-14
- **Poster**: How To Prompt (@HowToPrompt__)
- **Summary / Key Claims**: Memvid packages an agent's entire memory, data, embeddings, search index, and metadata into simple MP4 files. No database, no server, no sidecar files required. Claims significant performance gains over traditional RAG/vector DBs (+35% long-term memory, +76% multi-hop reasoning, 1,372× faster, 0.025ms latency). Key innovation: memory is append-only and versioned like git — rewind, replay, or branch any past state for debugging and time-travel analysis. Fully offline, model-agnostic, with SDKs for Python, Node, Rust, and CLI. 15.7k stars, 100% open source.
- **Extracted Repos / Tools**: Primary: https://github.com/memvid/memvid — MP4-based agent memory system with git-like versioning.
- **TOOLS.md Link**: New row under Context & Memory / RAG & Long-Term Memory (high-signal novel memory backend).
- **Notes**: **Very high relevance for context and memory management.** This is a groundbreaking approach to agent memory that directly addresses long-term context, debugging past states, and avoiding the complexity of traditional vector databases. The git-like rewind/replay/branch capability is extremely powerful for reliable agent workflows and aligns perfectly with our focus on context optimization, self-healing, and robust long-running loops. Strong potential for local agent setups. High fit for evaluation criteria: Very High Relevance (novel memory backend with versioning), High Integration Ease (SDKs + CLI), High Reproducibility (open source with strong claims), Low Redundancy. Recommend: (1) Catalog as major innovative memory tool. (2) Strong candidate for deep evaluation and potential integration into our agent stack (especially for long-term memory and debugging in loop engineering). (3) Excellent for exploring alternatives to traditional RAG/vector stores in local environments.
- **Status**: Processed and cataloged (added as high-value novel agent memory system; priority for context/memory category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 045: Bonsai 27B — Extreme 1-Bit Quantization for Browser-Based Local Inference

- **URL**: https://x.com/i/status/2077087411079700782
- **Date**: 2026-07-14
- **Poster**: Xenova (@xenovacom)
- **Summary / Key Claims**: Bonsai 27B uses 1-bit quantization to shrink a 54GB model down to just 3.8GB (-93% size) while retaining ~90% of its intelligence. Runs locally in the browser via custom WebGPU kernels (developed with Fable 5 and GPT-5.6 Sol). Represents a major leap in making large models practical for local/browser-based inference.
- **Extracted Repos / Tools**: Model collection on Hugging Face (PrismML Bonsai 27B). Custom WebGPU kernels for browser inference. Strong demonstration of extreme quantization + browser execution.
- **TOOLS.md Link**: New row under Inference & Serving / Extreme Quantization & Browser Inference (high-signal extreme quantization example).
- **Notes**: **High relevance for local/browser inference.** This showcases cutting-edge extreme quantization (1-bit) that makes large models feasible for local and even browser-based deployment. The combination of massive size reduction with strong performance retention is directly useful for practical local LLM setups, especially on resource-constrained devices or in-browser scenarios. High fit for evaluation criteria: Very High Relevance (extreme quantization + browser inference), High Integration Ease (WebGPU/browser-focused), High Reproducibility (HF model + kernels), Low Redundancy. Recommend: (1) Catalog as major extreme quantization / browser inference resource. (2) Strong candidate for testing on local hardware and browser environments. (3) Excellent reference for pushing the boundaries of what can run locally.
- **Status**: Processed and cataloged (added as high-value extreme quantization and browser inference resource; priority for inference category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 047: Spec Kit (Revisited) — Structured Spec-First Workflow for Reliable Agent Coding (120k+ Stars)

- **URL**: https://x.com/i/status/2076754607049449633
- **Date**: 2026-07-13
- **Poster**: Atlas (@crptAtlas)
- **Summary / Key Claims**: GitHub's Spec Kit forces AI agents to create a full structured spec *before* writing any code. Commands: /constitution (rules/standards), /specify (what to build), /clarify (open questions), /plan (architecture/stack), /tasks (ordered work), /implement (execution). Prevents "vibe coding" disasters. Already 120k+ stars, 10k+ forks. Works with Claude Code, Cursor, Copilot, Codex, Gemini CLI + 25+ agents. Emphasizes that learning to drive agents with structured specs is what separates effective AI engineers from prompt fighters.
- **Extracted Repos / Tools**: Primary: https://github.com/github/spec-kit (already cataloged in Entry 013). This post highlights its massive adoption and the exact command workflow.
- **TOOLS.md Link**: Reinforces existing entry under Agent Frameworks & Orchestration / Structured Workflow & Prompt Engineering.
- **Notes**: **High relevance — strong reinforcement of Entry 013.** This post provides fresh details on the exact command flow (/constitution → /specify → /clarify → /plan → /tasks → /implement) and highlights its explosive adoption (120k+ stars). It directly supports our emphasis on structured planning guardrails before implementation. Excellent for reproduction of best practices in agentic coding. The spec-first approach is a core pattern we should continue to prioritize in our own scaffolding and loop engineering. High fit for evaluation criteria: Very High Relevance (spec-first structured workflow), High Integration Ease (works with many agents), High Reproducibility (GitHub-backed, open source), Low Redundancy. Recommend: (1) Update existing Spec Kit entry with command workflow details from this post. (2) Strong reference for enhancing AGENTS.md or project-process with similar spec-first patterns. (3) Excellent example of how structured workflows dramatically improve agent output quality and predictability.
- **Status**: Processed and cataloged (reinforces Spec Kit entry with command details and adoption metrics; high value for structured workflow patterns)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 048: HERMES AGENT — Three Feedback Loops for Continuous Self-Improvement (Auto-Memory, Auto-Skill, Curator)

- **URL**: https://x.com/i/status/2077132507343134788
- **Date**: 2026-07-14
- **Poster**: YanXbt (@IBuzovskyi)
- **Summary / Key Claims**: Hermes Agent has three built-in feedback loops that make it smarter every week if enabled:
  1. **AUTO-MEMORY**: After every response, saves learnings (timezone, stack, preferences, tools, mistakes, projects) to memory.md and user.md. Loaded automatically in future context.
  2. **AUTO-SKILL CREATION**: After complex tasks (5+ tool calls), creates reusable SKILL.md files for procedures, tools used, and pitfalls. Next similar task uses the saved skill instead of re-deriving.
  3. **CURATOR**: Background maintenance (every 7 days) that tracks skill usage and archives unused agent-created skills after 90 days (recoverable). Supports pinning critical skills and optional LLM-based consolidation of duplicates.
  The post emphasizes that most users disable these (to save tokens) or ignore them, causing the agent to stop improving. With all three running, the agent compounds knowledge: facts are remembered, procedures are reused, and bloat is pruned.
- **Extracted Repos / Tools**: Hermes Agent (framework with built-in auto-memory, auto-skill, and curator loops). Strong emphasis on self-improving agent architecture via feedback loops and skill/memory management.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Self-Improving Agents & Feedback Loops (high-signal self-improvement pattern).
- **Notes**: **Extremely high relevance — direct reinforcement of loop engineering.** The three feedback loops (auto-memory, auto-skill creation, curator pruning) are a concrete, production-grade implementation of the self-improving / compounding agent patterns we've been building toward. Maps beautifully to our 4-tier autonomy, 14-step roadmap, goal-based evaluators, and skills work. The curator's git-like pruning + pinning is especially elegant for long-term maintainability. High fit for evaluation criteria: Very High Relevance (self-improving feedback loops + skill/memory management), High Integration Ease (patterns are portable), High Reproducibility (detailed implementation described), Low Redundancy. Recommend: (1) Catalog as major self-improving agent framework. (2) Strong candidate for direct adaptation into our loop-engineering skill pack (e.g., auto-memory patterns, auto-skill creation, curator-style maintenance). (3) Excellent reference for building compounding intelligence into AgenC-based agents.
- **Status**: Processed and cataloged (added as high-value self-improving agent framework; priority for loop engineering and skills integration)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 049: opencode-mem — Persistent Memory & Long-Term Context for OpenCode Agents (Local Vector DB)

- **URL**: https://x.com/i/status/2077134466267394303
- **Date**: 2026-07-14
- **Poster**: Tom Dörr (@tom_doerr)
- **Summary / Key Claims**: opencode-mem adds persistent memory and long-term context retention for OpenCode coding agents using a local vector database. Enables agents to remember context across sessions, improving continuity in long-running or multi-session coding workflows.
- **Extracted Repos / Tools**: Primary: https://github.com/tickernelz/opencode-mem — Local vector DB memory layer for OpenCode agents.
- **TOOLS.md Link**: New row under Context & Memory / Long-Term Memory for Coding Agents (high-signal persistent memory tool).
- **Notes**: **High relevance for long-term agent memory.** Directly addresses context retention across sessions — a critical gap in many agent setups. Complements Memvid (Entry 044), codebase-memory-mcp, and Graphify (Entry 017) by providing a simple local vector DB approach specifically for OpenCode. Strong fit for improving reliability in multi-session or long-running agent loops. High fit for evaluation criteria: Very High Relevance (persistent memory for coding agents), High Integration Ease (local vector DB, agent-specific), High Reproducibility (open source), Low Redundancy. Recommend: (1) Catalog as persistent memory tool for coding agents. (2) Useful for evaluation alongside other memory/context solutions. (3) Good reference for adding long-term memory capabilities to agent workflows.
- **Status**: Processed and cataloged (added as high-value persistent memory tool for agents; useful for context retention)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 050: paperclipai/companies — 16 Pre-Built AI Companies with Org Charts & Hundreds of Skills

- **URL**: https://x.com/i/status/2077741674080395626
- **Date**: 2026-07-16
- **Poster**: Tom Dörr (@tom_doerr)
- **Summary / Key Claims**: Imports 16 pre-built AI companies with complete org charts and hundreds of skills into the Paperclip platform. Provides ready-made company templates (org structure + skill libraries) for quickly setting up multi-role agent systems.
- **Extracted Repos / Tools**: Primary: https://github.com/paperclipai/companies — Pre-built AI company templates with org charts and skills for Paperclip.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Skills & Prompt Engineering (high-signal pre-built company/skill templates).
- **Notes**: **High relevance — direct extension of org-chart skill patterns.** Builds directly on our earlier entries about Claude Company Org Chart (Entry 016/037) and large-scale curated skill stacks. Provides concrete, ready-to-import company templates with full org structures and hundreds of skills. Excellent for rapid setup of multi-role agent teams and studying real-world org/skill curation patterns. High fit for evaluation criteria: Very High Relevance (pre-built company orgs + skill libraries), High Integration Ease (importable templates), High Reproducibility (open source), Low Redundancy. Recommend: (1) Catalog as major pre-built company/skill template resource. (2) Strong candidate for studying and adapting org-chart structures into our own skill packs. (3) Useful for quickly bootstrapping complex multi-agent setups.
- **Status**: Processed and cataloged (added as high-value pre-built AI company templates; priority for skills/org category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 051: N-gram Speculative Decoding (ngram-mod) in llama.cpp — Zero-VRAM Speed Boost for Repetitive Generation

- **URL**: https://x.com/i/status/2077718647905333549
- **Date**: 2026-07-16
- **Poster**: Alok (@analogalok)
- **Summary / Key Claims**: Detailed technical breakdown of N-gram Speculative Decoding (`--spec-type ngram-mod`) in llama.cpp. Provides massive speedups on repetitive tasks (code, JSON, document editing) by using a lightweight rolling hash + O(1) lookup to detect and "fast forward" through sequences already present in the KV cache/context. Achieves ~2x+ generation speed (e.g., 46 t/s → 107 t/s on code editing) with **zero extra VRAM** and virtually zero compute overhead. No draft model required. Especially powerful for structured/repetitive output. Includes parameters (`--spec-ngram-simple-size-n`, `--spec-ngram-simple-size-m`) and a free Google Colab notebook for testing.
- **Extracted Repos / Tools**: llama.cpp with ngram-mod support. Strong practical optimization for local inference engines.
- **TOOLS.md Link**: New row under Inference & Serving / Speculative Decoding & Optimization (high-signal inference optimization technique).
- **Notes**: **High relevance for local inference performance.** This is an excellent, practical optimization that delivers significant speed gains on exactly the kinds of tasks agents do most (code generation, structured output, editing) without any VRAM penalty. The rolling hash + speculative draft approach is pure computer science elegance. Directly useful for making local agent workflows faster and more responsive. High fit for evaluation criteria: Very High Relevance (zero-cost speculative decoding), High Integration Ease (simple llama.cpp flag), High Reproducibility (detailed explanation + Colab notebook), Low Redundancy. Recommend: (1) Catalog as major inference optimization technique. (2) Strong candidate for testing on local hardware (especially code-heavy agent tasks). (3) Excellent reference for squeezing maximum performance out of local LLM setups.
- **Status**: Processed and cataloged (added as high-value inference optimization; priority for performance category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 052: LEANN — Extreme RAG Compression (201 GB → 6 GB, 97% Savings, No Accuracy Loss)

- **URL**: https://x.com/i/status/2077528059339817025
- **Date**: 2026-07-15
- **Poster**: Md Ismail Šojal (@0x0SojalSec)
- **Summary / Key Claims**: LEANN compresses massive RAG datasets dramatically (e.g., 60 million chunks from 201 GB down to 6 GB — 97% storage reduction) with no loss in accuracy. Enables powerful local RAG on a laptop without needing server farms. Perfect for personal knowledge bases and local agent memory systems.
- **Extracted Repos / Tools**: Primary: https://github.com/StarTrail-org/LEANN (with accompanying paper: https://arxiv.org/pdf/2506.08276). Extreme compression technique for RAG embeddings/indexes.
- **TOOLS.md Link**: New row under Context & Memory / RAG Optimization & Compression (high-signal RAG compression tool).
- **Notes**: **High relevance for local RAG/memory.** Directly solves the storage bloat problem that makes large-scale local RAG impractical. The 97% compression with zero accuracy loss is exceptional and makes sophisticated RAG feasible on consumer hardware. Complements Memvid (MP4 memory packaging) and other context tools by attacking the storage layer. High fit for evaluation criteria: Very High Relevance (extreme RAG compression), High Integration Ease (local-friendly), High Reproducibility (open source + paper), Low Redundancy. Recommend: (1) Catalog as major RAG optimization/compression tool. (2) Strong candidate for testing with large personal knowledge bases or agent memory systems. (3) Excellent reference for making local RAG practical at scale.
- **Status**: Processed and cataloged (added as high-value RAG compression tool; priority for context/memory category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 053: awesome-hermes-skills — Curated Library of 271 Install-Ready Skills for Hermes Agent

- **URL**: https://x.com/i/status/2077738909778542896
- **Date**: 2026-07-16
- **Poster**: Simplifying AI (@simplifyinAI)
- **Summary / Key Claims**: Comprehensive curated list of 271 free, install-ready skills for Hermes Agent (85 built-in, 101 optional, 85 community). Every skill is tagged by status with direct install commands. Covers a wide range of domains and works with Claude Code, OpenClaw, Cursor, and Windsurf.
- **Extracted Repos / Tools**: Primary: https://github.com/ZeroPointRepo/awesome-hermes-skills — Large curated skill library for Hermes Agent.
- **TOOLS.md Link**: New row under Skills & Prompt Engineering (high-signal curated skill library).
- **Notes**: **High relevance for skills ecosystem.** Directly complements our recent Hermes Agent entry (048) and ongoing skills development work. Provides a ready-to-use, well-organized library of hundreds of skills with clear install paths. Excellent for rapidly expanding agent capabilities and studying curation patterns at scale. High fit for evaluation criteria: Very High Relevance (large curated skill library), High Integration Ease (install commands provided), High Reproducibility (open source), Low Redundancy. Recommend: (1) Catalog as major curated skill library. (2) Strong candidate for exploring and integrating useful skills into our own packs. (3) Excellent reference for large-scale skill organization and discovery.
- **Status**: Processed and cataloged (added as high-value curated skill library; priority for skills category)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 054: OpenClaude-Portable — Folder-Based Portable Coding Agent (Multi-Provider, No Install)

- **URL**: https://x.com/i/status/2077768643128009110
- **Date**: 2026-07-16
- **Poster**: Tom Dörr (@tom_doerr)
- **Summary / Key Claims**: OpenClaude-Portable is a fully portable coding agent that runs directly from a folder with no installation required on Windows, Linux, or macOS. It aggregates Anthropic (Claude), OpenAI, Google Gemini, and Ollama into a unified web dashboard with agent capabilities. Designed for easy use on temporary or shared machines.
- **Extracted Repos / Tools**: Primary: https://github.com/techjarves/OpenClaude-Portable — Portable, folder-based multi-provider coding agent.
- **TOOLS.md Link**: New row under Agent Frameworks & Orchestration / Portable & Lightweight Agents (strong fit for new lightweight harness direction).
- **Notes**: **Very high relevance to current pivot.** This directly supports the shift to a lightweight, scriptable, local-first harness (OpenCode + Grok build CLI). The "run from folder, no install" model is ideal for portable, reproducible environments. Strong candidate to evaluate as a core runtime or reference implementation for the harness. Complements our focus on OpenCode and custom agent CLIs. High fit for evaluation criteria: Very High Relevance (portable lightweight agent), High Integration Ease (folder-based, multi-provider), High Reproducibility (open source), Low Redundancy. Recommend: (1) Catalog as top portable agent option. (2) Strong candidate for direct testing/integration into `bootstrap/setup-lightweight-harness.py`. (3) Evaluate as potential primary runtime or unified dashboard layer alongside OpenCode and Grok CLI.
- **Status**: Processed and cataloged (added as high-value portable lightweight agent; priority for harness integration)

## Future Entries Format

When adding new X-sourced tools or papers:

```

### Entry 055: Hermes Agent Credential Pools — Scoped, Revocable API Key Management for Sub-Agents

- **URL**: https://x.com/i/status/2077583294137291175
- **Date**: 2026-07-16
- **Poster**: Hermes Agent Tips (@HermesAgentTips)
- **Summary / Key Claims**: Hermes Agent's credential pools give each sub-agent a scoped, revocable key instead of exposing your real API key. This limits blast radius — one leaked session only compromises one account. "iron-proxy" handles rotation automatically so you never touch raw secrets. Strong security best practice for multi-agent systems.
- **Extracted Repos / Tools**: Related to Hermes Agent (NousResearch/hermes-agent). PR: https://github.com/NousResearch/hermes-agent/pull/30179. Focus on credential management and secret rotation for agent security.
- **TOOLS.md Link**: New row under Safety & Guardrails or Agent Frameworks & Orchestration (security pattern for multi-agent systems).
- **Notes**: **High relevance for safety and Hermes integration.** Directly enhances our Hermes Agent work (Entry 048) and the lightweight harness. The scoped/revocable credential pools + automatic rotation is an excellent security pattern for systems with multiple sub-agents or long-running loops. Complements destructive_command_guard and other guardrails. High fit for evaluation criteria: High Relevance (agent security best practices), High Integration Ease (can be adopted as a pattern), High Reproducibility (open source in Hermes ecosystem), Low Redundancy. Recommend: (1) Catalog as key security pattern. (2) Consider integrating credential pool concepts into safety_guards module of the lightweight harness. (3) Strong addition for any multi-agent or sub-agent workflows.
- **Status**: Processed and cataloged (added as high-value agent security pattern; useful for harness safety layer)

## Future Entries Format

When adding new X-sourced tools or papers:

```


## Future Entries Format

When adding new X-sourced tools or papers:

```
### Entry NNN: Short Title

- **URL**: https://x.com/...
- **Date**: YYYY-MM-DD
- **Poster**: @handle (Name)
- **Summary**: 1-2 sentence gist + why relevant to local LLM dev pipelines. Note if paper-based.
- **Extracted Repos/Tools**: List with links or 'Paper only: arxiv link'.
- **TOOLS.md Link**: Row or section reference.
- **Notes**: Any caveats, hype vs substance, feasibility if paper, pipeline fit.
```

*This log ensures the catalog remains grounded in primary social signals while allowing rigorous, staged evaluation separate from viral claims.*

---

### Entry — Unified Claude Code agents (2026-07-31)

- **X status:** https://x.com/i/status/2082997925014053075
- **Author:** @tom_doerr
- **Repo:** https://github.com/stretchcloud/claude-code-unified-agents
- **Summary:** 54 production-oriented Claude Code sub-agents (dev/infra/quality/AI/business/domain) + orchestrator.
- **Eval:** extensive pack loop `scripts/eval_unified_agents_pack.py` — **PASS** (98% gate, mean 4.06).
- **Decision:** Curated I1 paths pack (16 skills); docs_map overlaps to first-party; no Claude primary.
- **Pin:** b026de60c0fc5438f53faffb5cd7f43f84ed3267
- **Status:** Integrated 2026-07-31

---

### Entry — Exo harness (operator request 2026-07-31)

- **Repo:** https://github.com/exoharness/exo
- **Pin:** 372602d1b553af06e9843e19f31fa8a7f749ab6e
- **Summary:** Complete agent harness optimized for recursive self-improvement: code mount, rebuild_and_restart_exo, canonical event log, sandbox snapshot/rewind, skills as durable artifacts.
- **Self-change eval:** Operational §8 (snapshot → build → rebuild tool → event log → rollback); no formal numeric rubric; canary clone still a gap upstream.
- **Decision:** Catalog **A / I1**; extract patterns into integration-self-mod-eval + make target. Not primary runtime.
- **Status:** Cataloged 2026-07-31
