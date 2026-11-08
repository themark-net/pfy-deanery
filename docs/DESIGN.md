# Design: pfy-mentat

**Status:** Active  
**Last updated:** 2026-08-24  
**Authority for *why*:** [docs/adr/](adr/README.md)  
**Next work:** [docs/TODO.md](TODO.md) · open items [docs/OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)

This is the **master design document**: primary goals, intended shape of the system, and how pieces fit. It describes intent and boundaries. Settled architecture choices live in ADRs; day-to-day work lives in TODO + open questions.

---

## 1. Vision

Build a **living, scored catalog** of local-first LLM development tools and a **reproducible operator stack** so humans and agents can evaluate, integrate, and run continuous local pipelines—with **Grok CLI** as the primary interface and MCP-style code memory in the loop.

One-line purpose: **Track · Categorize · Rank · Integrate** tools for robust self-hosted agentic development.

**No reinvention:** if another project does track, catalog, evaluate and integrate better, we stop and adopt it. See [supersede-watch.md](ops/supersede-watch.md) and `data/supersede-watchlist.json`.

The **product you ship** is the operator stack (`./pfy` onboard / stage / ship). The catalog is how we choose pieces, not the end-user surface.

---

## 2. Primary goals

| # | Goal | Success looks like |
|---|------|--------------------|
| G1 | Living catalog | `TOOLS.md` is the scored catalog (X/community + rubric). `data/tools.json` is a slim machine subset ([ADR-0015](adr/0015-catalog-json-slim-subset.md)), not a 1:1 dump of all ~79 rows |
| G2 | Consistent evaluation | Stage 0 gate + weighted Stages 1–4 (see `CATEGORIZATION.md`); tiers S/A/B/C stay comparable over time |
| G3 | Stack synergies | Clear recommended combos (Grok monitor + LiteLLM + **pluggable local inference** + MCP memory) documented with integration notes |
| G4 | Rapid integration | Highest-value components installable/replayable without repo bloat (pins, rare subtree, bootstrap) |
| G5 | Grok-first interface | Operator env and agent skills bootstrapped from this repo; hybrid/fallback to other harnesses when scored higher for a task |
| G6 | Lean tracking | Prefer pinned SHA + shallow clone; embed only when criteria in `SUBTREES.md` are met |
| G7 | Durable process | Design + ADR + TODO + open questions keep multithreaded agents from re-litigating or losing TBDs |
| **G8** | **Simple deploy path** | Bare clone → `./pfy setup` → `./pfy start` : **local inference up once** (FreeToken first, then llama-swap/llama-server, Ollama adapter), any harness attaches; stubs for unfinished adapters |

### G8 detail — harness-agnostic simplicity

**Inspiration:** FreeToken / llama.cpp / Ollama as *inference*, Hermes/OpenCode integrated installers, Exo `setup.sh`, one-CLI auth, Grok Build login.

**Shape:**

```text
./pfy setup     → env + skills + detect local runtime
./pfy status    → ready | partial | stub | missing  (honest; missing ≠ partial)
./pfy start     → inference → env-stage → active harness (default grok)
./pfy harness use <id>
```

**Inference detect order** (ADR-0014): FreeToken (`ft` :1919) → llama-swap (:9292) → llama-server (:8080) → Ollama (:11434). Shimmy optional.

**Harness slots** (see `data/harnesses.json`): freetoken, llama-swap, llama.cpp, ollama, grok, opencode, hermes, claude-code, codex, gemini, exo, continue, agent-cage.

Grok stays **default harness** (ADR-0002). Local **worker** uses `LOCAL_OPENAI_BASE_URL`. Eval pipeline (`pfy eval`) remains core for the catalog mission — it is not the first screen for newcomers.

**Authority:** [ADR-0012 simple launch](adr/0012-simple-harness-agnostic-launch.md) · [ADR-0014](adr/0014-pluggable-local-inference-spine.md) · [local-runtime.md](ops/local-runtime.md)

---

## 3. Non-goals (current horizon)

- Becoming a monorepo of large inference engines or full IDE products
- Auto-submitting external systems or holding user secrets in-repo
- Replacing Grok’s own binary, auth, or marketplace plugins
- Exhaustive “awesome list” coverage without scoring or pipeline value
- Forcing a single commercial harness monoculture (G8: multi-slot, Grok default only)
- Selling lab-IT / Entra Linux / MDM (PNNL/Battelle IP) from this repo

---

## 4. System shape

```text
                    ┌─────────────────────────────────────┐
  X posts / papers  │  Intake                             │
  aggregates        │  sources/x-posts.md                 │
                    │  sources/aggregates.md              │
                    └──────────────┬──────────────────────┘
                                   │ score + synthesize
                    ┌──────────────▼──────────────────────┐
                    │  Catalog                            │
                    │  TOOLS.md  ·  data/tools.json       │
                    │  CATEGORIZATION.md rubric           │
                    └──────────────┬──────────────────────┘
                                   │ integrate
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
   bootstrap/grok-cli/      pipelines/ (future)      examples/ (future)
   skills · MCP · config    eval harnesses           compose / patterns
          │
          ▼
   Operator machine: Grok CLI (monitor) + local runtime (worker) + skills
          │
          ▼
   Downstream projects (e.g. gom-jobbar, ATG prototype) consume stack
```

### Layers

| Layer | Location | Role |
|-------|----------|------|
| Process | `docs/` | Design, ADR, TODO, open questions |
| Catalog methodology | `CATEGORIZATION.md`, `SUBTREES.md` | How to score and track tools |
| Catalog content | `TOOLS.md`, slim `data/tools.json`, `sources/` | Markdown catalog vs machine subset (ADR-0015) |
| Integration packages | `bootstrap/`, later `pipelines/`, `examples/` | How to run / replay stack pieces |
| External tools | pins / rare `tools/` embeds | Upstream code not owned here |

---

## 5. Delivered vs future

### Delivered

- Catalog methodology (taxonomy, rubric, subtree policy, aggregates intake)
- Seeded scored tools + paper analysis workflow (ATG)
- First-party **Grok CLI bootstrap** (`bootstrap/grok-cli/`)
- Process docs layout (this file + ADR + TODO + OQ)
- **project-process bootstrap** (`bootstrap/project-process/`)
- Phase 0 catalog sync + **agent-cage** as primary container harness
- **Deployment profiles** — ADR-0006
- **Write-guard MCP** — ADR-0007; **implemented** (T-0031)
- **One-shot workflow** — ADR-0008 · `/one-shot`
- **`./pfy` simple surface** — ADR-0012 (G8)

### Near-term (see TODO)

- **T-0090** product surface: onboard / stage / ship only
- **#76 / ADR-0014** pluggable local runtime (FreeToken preferred)
- Keep **`make eval-structural`** + local **`eval-suite`** green
- Platform Make complexity OK in MVP; product UX must stay ≤ ~3 levers

### Later / research

- Automated scoring dashboard from `data/tools.json`
- Continuous pipeline CI for agent evals
- DSPy + MCP scored tier (post eval MVP)

---

## 6. Process model (mandatory for agents)

| Artifact | Path | Holds |
|----------|------|--------|
| **Design** (this doc) | `docs/DESIGN.md` | Goals, shape, boundaries |
| **Architecture map** | `docs/ARCHITECTURE.md` | Current structural snapshot (keep short; link here) |
| **ADR** | `docs/adr/` | Settled *why*, including **rejected** alternatives |
| **TODO** | `docs/TODO.md` | Ordered next steps; links to OQs |
| **Open questions** | `docs/OPEN_QUESTIONS.md` | Unsettled TBDs |
| **Operator/agent module docs** | `docs/modules/`, `docs/ops/` | How to run / navigate non-trivial modules |

### Rules

1. **Read before design changes:** `docs/DESIGN.md` + open ADRs + relevant OQs.
2. **Architecture pivots → ADR:** record decision, rationale, and **paths decided against**.
3. **Work items → TODO:** central next steps; each item may reference OQ IDs.
4. **Uncertainty → Open Question.**
5. **Answered architectural OQs → promote to ADR.**

Skills: `/adr`, `/open-questions` (`/oq`), `/docs`.

---

## 7. External ownership boundaries

| System | This repo may | This repo must not |
|--------|---------------|--------------------|
| Grok CLI | Ship skills, config fragments, install scripts | Store `auth.json`, API keys, session DBs |
| Upstream tools | Pin, score, rarely embed | Fork large runtimes into default path |
| Sibling projects | Reference, bootstrap against | Silently mutate sacred user data |
| X / papers | Log sources, synthesize catalog rows | Claim ownership of third-party IP |

---

## 8. Related documents

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [adr/README.md](adr/README.md)
- [adr/0015-catalog-json-slim-subset.md](adr/0015-catalog-json-slim-subset.md)
- [TODO.md](TODO.md)
- [OPEN_QUESTIONS.md](OPEN_QUESTIONS.md)
- [ops/local-runtime.md](ops/local-runtime.md)
- Root: `README.md`, `CATEGORIZATION.md`, `SUBTREES.md`, `TOOLS.md`
- Bootstrap: `bootstrap/grok-cli/README.md`
