# pfy-mentat

**pfy-mentat — Your PFY, a Mentat. It gets sent out, finds the tools, applies the standards, and reports back with receipts.**

pfy-mentat is both a high-standard catalog of local LLM development tools *and* an orientation toward building the software that actually deploys and runs them reliably.

The system (the PFY) is sent out to discover candidates, apply strict local-first standards, reject what doesn’t meet them, and deliver only the components that are worth using. The goal is not merely “tools that exist,” but tooling that helps people ship working local LLM systems instead of fighting endless “it works on my machine” problems — both for the tools themselves and for the products built with them.

Repository: https://github.com/themark-net/pfy-mentat

## Simple path

Operator environment: local inference, then product stage (honest skip if a piece is missing), then the native operator window. Loop paints **LOCAL COMPUTE | CLOUD ORCHESTRATION** plus gathered catalog **MODULES**. **Launch session** applies enabled modules into an enterable TUI — that session is the proof. Attach grok/opencode remains on the Attach tab. Do not exec a harness into the GUI process.

```bash
./pfy           # inference → env-stage → native window (no harness exec)
./pfy board     # same native window (Tauri if built, else already-on-box webkit, else stdlib tk)
./pfy start grok  # named harness after inference/stage (still execs that harness)
./pfy launch      # Launch session: apply enabled Loop modules, then enterable TUI
./pfy models    # inspect-only: live GET /v1/models (and Ollama /api/tags); usage if exposed
```

Bare `./pfy` / `./pfy up` / `./pfy start` (no name) open the native window. `./pfy board` aliases it. Optional `./pfy board --open` is a browser hatch only (not the main path). Board is not a supervisor.

If continue or agent-cage is the active harness: FAIL and copy `pfy harness use grok` (no grok/opencode fallback). Chips bind `./pfy status` **live** (`missing` not `unknown`).

`./pfy start <harness>` runs inference and stage, then that harness. Listing model tags is not success. Empty `ollama ps` is OK. A missing harness process is not. FreeToken model env: **`PFY_FT_MODEL`** (then `LOCAL_CODER_MODEL` or `FREETOKEN_MODEL`).

Tauri is primary when `gui/operator/src-tauri/target/{release,debug}/pfy-operator` exists. Else already-on-box webkit (`scripts/pfy-gui.py`). Else stdlib tk with the same IA (Loop local/cloud + modules → Launch session, engine status, env-stage, Attach tab for grok / opencode sidecar). pywebview is PFY_GUI_DEV=1 only. The window always opens; not install-tips-as-UI.

## What it is

- A living, gate-checked catalog of local LLM dev tools, frameworks, patterns, and methods.
- An operator posture (the PFY) for discovery on X and elsewhere: apply non-negotiable criteria, log every decision with receipts, and keep the catalog current.
- A deliberate focus on **reproducibility and deployment**, not just “it builds” — components and patterns that support shipping working systems.
- Practical operator stack: **Grok CLI**, custom agents, **MCP** code memory, LiteLLM routing, **containerized harnesses** (agent-cage), and process docs so multi-session agents stay aligned.

## Core principles

- **Local first, always.** Tools must be self-hostable and runnable on normal developer hardware with minimal ceremony.
- **Permissive and embeddable.** Licenses must allow real use and modification.
- **Receipts over vibes.** Every inclusion or rejection is logged with explicit reasoning in [`sources/x-posts.md`](sources/x-posts.md) (and related sources).
- **Beyond “it builds.”** While many projects struggle to even compile successfully, pfy-mentat orients toward components and practices that support working, deployable results — for the tools themselves and for the systems people build with them.

We recognize that perfect reproducibility is impossible in computing (just as Ansible’s idempotency guarantees can be broken by the environment). The intent is still to raise the baseline: tools and patterns that are more likely to result in something that actually runs and keeps running, rather than another local-only prototype.

## Stage 0 gate

Items must satisfy all of the following before catalog consideration (full rubric: [CATEGORIZATION.md](CATEGORIZATION.md)):

- Runnable self-hosted path under ~5 minutes on a clean Ubuntu or macOS system (or a documented one-liner).
- Permissive open-source license suitable for embedding and modification.
- Working hello-world or quickstart that demonstrates the core capability.

Rejections are logged with short, explicit reasons. There is no silent ignoring of candidates.

## Goals

- Maintain a living, versioned catalog of the best local-first LLM tools.
- Apply consistent, multi-stage evaluation criteria for compatibility, performance, agentic capability, and pipeline readiness.
- Identify synergies for a unified local development stack (inference + agents + memory + orchestration + CI/CD).
- Enable rapid prototyping and deployment of custom pipelines using the highest-ranked components.
- Support Grok CLI as primary interface initially, with fallback/hybrid to other identified toolsets based on task requirements.
- Provide selective, reproducible copies of critical tools via pinned commits (rare subtree) while keeping the tracking repo lean.
- Test integrations in **versioned container sandboxes** (agent-cage) so host systems stay clean and results are reproducible.

## Using the catalog

| Consume | Path |
|---------|------|
| Human catalog | [TOOLS.md](TOOLS.md) — categories, scores, tiers, notes |
| Machine catalog | [data/tools.json](data/tools.json) — structured, must stay valid JSON |
| Decision receipts | [sources/x-posts.md](sources/x-posts.md) — examined posts and decisions |
| Taxonomy & rubric | [CATEGORIZATION.md](CATEGORIZATION.md) — Stage 0 + weighted stages → 0–100 → S/A/B/C |
| Work queue | [docs/TODO.md](docs/TODO.md) — deeper eval and integration work |

**Default tracking:** pinned commit + shallow clone (`data/tools.json`). Rare subtree only if [SUBTREES.md](SUBTREES.md) criteria are met.

**Catalog triple-write rule:** every processed tool seed must update `sources/x-posts.md` (if social/paper) **and** `TOOLS.md` **and** `data/tools.json` (JSON must parse). `/catalog-docs seed` or `/catalog-docs audit` enforces this.

### Automation (the PFY)

Discovery is not a slowly rotting list: candidates from X (and related monitors such as [@tom_doerr](docs/automation/tom-doer-monitor.md)) are triaged against the gate and relevance rules, with traceable entries for what was examined. Catalog updates happen only when justified. Full daily unattended PFY automation is evolving; until then, operators and agents run the same receipt-backed process by hand or on demand.

### Philosophy on deployment and working results

pfy-mentat does not treat “it builds on my machine” as success. While we cannot eliminate all environment-specific failures, selection criteria and patterns here prioritize components that support reproducible builds *and* working deployments. People using this catalog should spend less time debugging why something only works for the original author and more time shipping functional local LLM systems.

## Process docs (agents & humans)

| Artifact | Path | Role |
|----------|------|------|
| **Design** | [docs/DESIGN.md](docs/DESIGN.md) | Master goals, system shape, non-goals |
| **Architecture** | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Short structural snapshot |
| **ADR** | [docs/adr/](docs/adr/README.md) | Settled decisions + **rejected alternatives** |
| **TODO** | [docs/TODO.md](docs/TODO.md) | Ordered next steps (links to OQs) |
| **Open questions** | [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) | TBDs; detail may live next to work citing `OQ-NNNN` |
| **Agent entry** | [AGENTS.md](AGENTS.md) | Mandatory read list + do-nots |
| **Contributing** | [CONTRIBUTING.md](CONTRIBUTING.md) | How to add seeds/tools |
| **Catalog docs skill** | `/catalog-docs` | Keep README, triple-write catalog, harness docs consistent |
| **Consultant eval** | [docs/ops/consultant-eval.md](docs/ops/consultant-eval.md) | Outsider map: real vs stub vs catalog; `./pfy` + `make eval-structural` |
| **Module docs** | [docs/modules/](docs/modules/README.md) | Operator + agent maps for pfy, detector, grok, opencode, cage, write-guard |

When architecture pivots: `/adr`. When something is unsettled: `/open-questions`. When documenting this repo: **`/catalog-docs`**. Work queue: `docs/TODO.md`.

## Skills (Grok)

After `./bootstrap/grok-cli/install.sh`, these are available:

| Skill | Slash | Purpose |
|-------|-------|---------|
| **catalog-docs** | `/catalog-docs` | **This repo’s** documentation skill (README, TOOLS/json/x-posts triple-write, harness, audit) |
| **one-shot** | `/one-shot` | Min questions; cheap local→cage→cloud loops until DoD green (lab required) |
| **marketing-council** | `/marketing-council` | First-party multi-advisor marketing council + dissenter (T-0011) |
| **investigate** | `/investigate` | Root-cause debugging — no fix without confirmed hypothesis (T-0017) |
| docs | `/docs` | Portable module/ops docs for any project |
| adr | `/adr` | Architecture decisions + rejected alternatives |
| open-questions | `/open-questions` | TBD parking lot |
| project-process | `/project-process` | Scaffold DESIGN/ADR/TODO/OQ into a new repo |
| karpathy-guidelines | (auto) | Anti-overcomplication defaults |
| ponytail | (via skills path) | Minimalism / YAGNI modes |
| mattpocock subset | (via skills path) | tdd, code-review, to-spec (T-0011) |

Project skill source of truth: [`.grok/skills/`](.grok/skills/) (also vendored under `bootstrap/grok-cli/skills/` for reinstall).  
One-shot design: [docs/ops/one-shot-workflow.md](docs/ops/one-shot-workflow.md) · ADR-0008.

## Current status (v0.4 → G8 launch)

- **`./pfy`** simple surface (ADR-0012): bare `./pfy` / `up` / unnamed `start` bring up inference + stage + native operator window; named `start <harness>` still execs that harness; `models` is inspect-only
- Catalog + eval pipeline remain first-class (`./pfy eval`, structural/golden)


- Methodology: taxonomy, rubric, SUBTREES, aggregates intake.
- Process layout: DESIGN + multi-file ADR + TODO + open questions (ADR-0001).
- **Grok CLI bootstrap** + **project-process** scaffold (replayable operator + new-project process).
- **Phase 0 catalog sync:** mobile X seeds Entries 001–010 + structured `data/tools.json` (18 tools); see [TOOLS.md](TOOLS.md).
- **agent-cage (PNNL)** as primary **container integration lab** under [`harness/agent-cage/`](harness/agent-cage/) (Make + pin + MCP).
- **`/catalog-docs`** skill for repository documentation consistency.
- Deploy runbook: [docs/ops/DEPLOY.md](docs/ops/DEPLOY.md).

**Next steps** (authoritative: [docs/TODO.md](docs/TODO.md) · GitHub issues):

1. ~~Cage smokes + tool integrations~~ (done) — see `make help-platform`  
2. Write-guard MCP implement — T-0031  
3. Skill ports (mattpocock / marketing-council / gstack patterns) — T-0011  
4. Eval harness prototype — T-0003 / [OQ-0002](docs/open-questions/OQ-0002-eval-harness-shape.md)  

Plans: [docs/ops/plan-mobile-seed-integration.md](docs/ops/plan-mobile-seed-integration.md), [docs/ops/harness-integration-framework.md](docs/ops/harness-integration-framework.md).

## Deploy runbook

Full new-machine path: **[docs/ops/DEPLOY.md](docs/ops/DEPLOY.md)**.

## Bootstrap (new machine + new projects)

### Simple path (recommended — G8)

One launcher. Inference first, then product stage, then the native operator window:

```bash
git clone https://github.com/themark-net/pfy-mentat.git
cd pfy-mentat
./pfy setup              # env + Grok skills if CLI present
./pfy                    # inference → env-stage → native operator window
./pfy board              # same native window
./pfy models             # inspect-only; listing tags is not success
# or: ./pfy up            # same as bare ./pfy
# or: ./pfy start grok    # named harness after inference/stage
```

Bare `./pfy` opens the native window (Tauri if built, else already-on-box webkit, else stdlib tk). pywebview is PFY_GUI_DEV=1 only. Browser `--open` is not the main path.

| Command | Purpose |
|---------|---------|
| `./pfy` / `./pfy up` / unnamed `./pfy start` | Inference, then env-stage, then native operator window. Does **not** exec a harness into that process. |
| `./pfy start <harness>` | Same bring-up, then that harness (stubs: STUB + issue, exit 2) |
| `./pfy board` / `./pfy board --open` | Same native window. --open is an optional browser hatch (honest skip if it fails) |
| `./pfy models` | Inspect-only: list models from the live endpoint (`GET /v1/models`, Ollama `/api/tags`) |
| `./pfy models pull <name>` | Live engine: FreeToken records name for next `ft serve --model`; Ollama `pull`; llama-* honest skip |
| `./pfy harness list` | Grok, OpenCode, Hermes, Claude Code, Codex, Gemini, Exo, … |
| `./pfy harness use opencode` | Switch active harness (stubs print next steps) |
| `./pfy stage` / `./pfy eval` / `./pfy ship` | Green checks + catalog gates + product verify |

Design: **G8** · [ADR-0012](docs/adr/0012-simple-harness-agnostic-launch.md) · [simple-launch.md](docs/ops/simple-launch.md).  
Platform builders: `make help-platform`. Product surface is `make help` (onboard / stage / ship).

### 1. Clone + environment profiles (advanced / same as before)


```bash
git clone git@github.com:themark-net/pfy-mentat.git
cd pfy-mentat
make env-init                 # creates .env from example (gitignored)
# edit .env: DEPLOY_PROFILE=local-only|balanced|max-performance + secrets
make env-check                # validates required vars for profile
```

| Profile | Intent |
|---------|--------|
| `local-only` | Local models only; no cloud keys required |
| `balanced` | Default — local bulk + cloud (e.g. Grok) for hard tasks |
| `max-performance` | Cloud-first; local optional |

Registry of all vars: [bootstrap/env/REGISTRY.md](bootstrap/env/REGISTRY.md).  
Design: [docs/ops/deployment-profiles.md](docs/ops/deployment-profiles.md) · ADR-0006.

### 2. Operator environment (Grok skills + MCP)

```bash
# After installing Grok: curl -fsSL https://x.ai/cli/install.sh | bash
./bootstrap/grok-cli/install.sh --with-codebase-memory
grok login   # or set XAI_API_KEY in .env
```

Installs skills: `adr`, `docs`, `open-questions`, `karpathy-guidelines`, `project-process`, **`catalog-docs`**, plus ponytail path + codebase-memory MCP wiring.  
Details: [bootstrap/grok-cli/README.md](bootstrap/grok-cli/README.md).

### New project process scaffold (DESIGN / ADR / TODO / OQ)

```bash
mkdir -p ~/work/my-app && cd ~/work/my-app && git init
/path/to/pfy-mentat/bootstrap/project-process/init.sh . \
  --name my-app \
  --vision "One-line product vision" \
  --install-skills
```

Or in Grok: `/project-process init .`  
Details: [bootstrap/project-process/README.md](bootstrap/project-process/README.md).

### Container harness (integration lab)

**Prefer testing catalog integrations inside this cage** (versioned images), not only on the host.  
**Filesystem writes:** stock cage MCP can r/w `/workspace`; **write-guard MCP** v0.1 adds audit/enforce policy — `make smoke-write-guard` · [docs/modules/write-guard-mcp.md](docs/modules/write-guard-mcp.md) · ADR-0007.

From **repo root** (do not run bare `make test` expecting cage — use `cage-*` targets):

```bash
export PATH="$HOME/.local/bin:$PATH"
make cage-doctor
make cage-setup          # install agentcage CLI
make cage-init           # once → ~/.agentcage runtime project
make cage-up-mcp         # START stack (first build is slow)
make cage-status && make cage-test
make cage-shell          # agent Ubuntu; workspace ~/.agentcage/workspace
make cage-down
```

Or: `cd harness/agent-cage && make help`.

Upstream: [pnnl/agent-cage](https://github.com/pnnl/agent-cage). Runtime dir after init: **`~/.agentcage`**.  
Details: [harness/agent-cage/README.md](harness/agent-cage/README.md).

## Repository structure

```
pfy-mentat/
├── README.md
├── AGENTS.md                  # Agent entry: mandatory reads + workflow practices
├── CONTRIBUTING.md            # Seed/tool contribution guidelines
├── CATEGORIZATION.md          # Taxonomy + Stage 0 gate + staged 0-100 rubric
├── SUBTREES.md                # Selective subtree/submodule/pinned-SHA policy
├── TOOLS.md                   # Master scored table + integration notes
├── .grok/skills/
│   ├── catalog-docs/          # Document this catalog
│   └── one-shot/              # Guardrailed unattended-until-green mode
├── docs/
│   ├── DESIGN.md              # Master design (goals + shape)
│   ├── ARCHITECTURE.md              # Structural snapshot
│   ├── TODO.md                    # Central next steps → OQ links
│   ├── OPEN_QUESTIONS.md          # Central TBD index
│   ├── adr/                       # ADRs (decisions + rejected paths)
│   ├── open-questions/            # OQ detail files
│   ├── ops/                       # DEPLOY, plans, harness framework, one-shot-workflow
│   ├── modules/                   # First-party package maps (bootstrap, cage, smokes)
│   └── automation/                # Standing monitors (e.g. tom-doer)
├── sources/
│   ├── x-posts.md                 # X/social seed log + receipts (Entries 001+)
│   └── aggregates.md
├── data/
│   └── tools.json                 # Structured catalog (must stay valid JSON)
├── bootstrap/
│   ├── grok-cli/                  # Operator env: skills + MCP + config
│   └── project-process/           # Scaffold process into any repo
├── harness/
│   └── agent-cage/                # Container sandbox (PNNL) + Makefile lab
├── gui/operator/              # Native operator GUI (Tauri 2 + shared frontend)
├── examples/                      # Future integration patterns / smokes
└── pipelines/                     # Future continuous eval & deploy
```

## Catalog & scoring (summary)

See [CATEGORIZATION.md](CATEGORIZATION.md) and [TOOLS.md](TOOLS.md). Tools get Stage 0 gate + weighted Stages 1–4 → overall 0–100 → S/A/B/C tiers. Focus: Grok CLI, tool calling, MCP memory, pipeline extensibility, and deployability.

### Highlighted tools

| Tool | Overall | Tier | Tracking |
|------|---------|------|----------|
| Grok CLI bootstrap | 94 | S | `bootstrap/grok-cli/` |
| project-process bootstrap | 92 | S | `bootstrap/project-process/` |
| **agent-cage (PNNL)** | 90 | S | pin + `harness/agent-cage/` |
| codebase-memory-mcp | 91 | S | pin + bootstrap MCP |
| LiteLLM / Ollama | 93 / 92 | S | pinned_commit |
| repowise / gstack / Multica / mattpocock / marketing-skills | 85–88 | A | pin / skill snapshots |
| colibri | 86 | A | pin (weights not in-repo) |

Full table: [TOOLS.md](TOOLS.md). Seeds: [sources/x-posts.md](sources/x-posts.md).

## How to contribute

1. Read [CONTRIBUTING.md](CONTRIBUTING.md).
2. High-signal tools that meet the Stage 0 gate are welcome — open an issue or PR with the link and a short justification.
3. New X/tool: apply rubric → **triple-write** x-posts + TOOLS.md + tools.json (or run `/catalog-docs seed`). Automation and operators will triage with receipts on the next pass.
4. Integration experiment: prefer `harness/agent-cage` for isolation; record notes in TOOLS.md.
5. Architecture pivot: `/adr`. Unsettled: `/open-questions`. Docs drift: `/catalog-docs audit`.

All additions should improve the local-first, deployable stack (Grok CLI + MCP + cage + pipeline) or fill a clear gap in the scored catalog.

## License

MIT for the catalog and documentation in this repository. Individual tools carry their own licenses.

---

*v0.4 — Phase 0 catalog sync, agent-cage harness, `/catalog-docs` skill, deploy runbook. Process backbone from v0.3 (DESIGN/ADR/TODO/OQ). Vision: receipts over vibes; beyond “it builds.”*
