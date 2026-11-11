# AGENTS.md — pfy-deanery

Instructions for coding agents working in this repository.

## North star: no reinvention

pfy-deanery exists to **track, catalog, evaluate and integrate** outside tools, local-first. It is not trying to out-build harnesses or skill packs; it adopts them. If another project does that full suite better, we stop and use theirs. Near-matches live in `data/supersede-watchlist.json`; rules in [docs/ops/supersede-watch.md](docs/ops/supersede-watch.md). Before building a pipeline piece, check the watchlist and the catalog for one that already exists.

## Mandatory reads (before non-trivial design or multi-step work)

1. [docs/DESIGN.md](docs/DESIGN.md) — goals, shape, non-goals, process model  
2. [docs/adr/README.md](docs/adr/README.md) — decision index (open full ADRs that touch your area)  
3. [docs/TODO.md](docs/TODO.md) — next steps  
4. [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md) — do not silently “solve” P0/P1 OQs  

Also use as needed: `CATEGORIZATION.md`, `SUBTREES.md`, `TOOLS.md`, `bootstrap/grok-cli/README.md`.

## Process rules

| Situation | Action |
|-----------|--------|
| Architecture pivot / hard-to-reverse choice | Write **ADR** under `docs/adr/` with **rejected alternatives** (`/adr`) |
| Uncertain / can wait / needs human | **Open question** in central index; optional detail file or in-context note citing `OQ-NNNN` (`/open-questions`) |
| Implementation work item | Update **TODO** row; link OQs when blocked |
| Non-trivial module or bootstrap change | Operator + agent docs (`/docs`) |
| New catalog tool | Score with rubric; update TOOLS.md + data/tools.json + sources log |

## Do not

- Re-propose designs rejected in ADRs without a superseding ADR and new context  
- Leave P0–P2 questions only in chat  
- Embed large upstream repos without meeting `SUBTREES.md` (see ADR-0003)  
- Commit secrets, API keys, or `auth.json`  
- Create a second decision log outside `docs/adr/`  
- No tautological or implementation-detail unit sprawl as Done.  

## Bootstrap environment

```bash
# Preferred simple surface (G8 / ADR-0012):
#   ./pfy setup && ./pfy status && ./pfy start
./bootstrap/grok-cli/install.sh
# optional: --with-codebase-memory
# operator lab (Grok Build in agent-cage — primary path, ADR-0002/0010/0011):
#   make cage-grok && make cage-grok-net-smoke
# local Ollama path (cost-aware; ADR-0011):
#   ./examples/litellm-ollama/host-ollama-gateway.sh start && make smoke-litellm-ollama
# OpenCode (secondary surface; same skills SoT): bootstrap/opencode/README.md
# env sanity (does not install AgenC):
#   python3 bootstrap/setup-local-agent-env.py
```

Portable skills (SoT `bootstrap/grok-cli/skills/` — also for OpenCode): `adr`, `docs`, `open-questions`, `karpathy-guidelines`, `project-process`, `one-shot`, `marketing-council`, **`investigate`**, **`agent-loops`**, **`hermes-feedback`**, **`worker-monitor`** (local worker + Grok monitor), **`jev-decision`** (#230 typed Choice/Score), **`prefer-behavior-and-fail-recover-tests`** (Trophy / fail-recover), **`ui-is-the-app-design-in-loop`** (design pack before product UI), **`catalog-intake-dedupe`**, **`catalog-eval-lane`**, **`catalog-integrate-lane`**, **`catalog-apply-and-ceiling`**, **`catalog-fit-triage`**, **`catalog-loop-operator`** (catalog pipeline; each skill drives a script); ponytail + mattpocock via `skills.paths`.  
Verify: `make eval-structural` (no LLM) · `make smoke-grok-skills` · [skill-verification.md](docs/ops/skill-verification.md).  
**Surfaces:** Grok = **monitor** / hard tasks (subscription) · OpenCode+Ollama = **worker** / bulk — [local-cloud-split.md](docs/ops/local-cloud-split.md) · ADR-0011.  
**Local worker model:** `LOCAL_CODER_MODEL` (default `deepseek-coder:6.7b` after lab pass); set via `make eval-select-models`. Grok CLI does **not** auto-use it.  
**Product UX target:** onboard / stage / ship only — [product-operator-surface.md](docs/ops/product-operator-surface.md) · T-0090.  
Loop map: [loop-engineering.md](docs/ops/loop-engineering.md). Decisions: [human-decision-inventory.md](docs/ops/human-decision-inventory.md).  
Code memory: CM primary ([vs Graphify](docs/evaluation/codebase-memory-vs-graphify.md)).  
**Cage:** `make cage-grok` refreshes auth + installs first-party skills into container `GROK_HOME`.  
**Code sync (host only):** `make cage-code-sync` / `PUSH=1` — [cage-code-sync.md](docs/ops/cage-code-sync.md).  
**This repo:** `/catalog-docs` — document the catalog (README, triple-write, harness); source `.grok/skills/catalog-docs/`.

### Role router (gstack patterns, docs-first — T-0014)

Map **Think → Plan → Build → Review → Test → Ship → Reflect** without installing gstack:

| Stage / role | Prefer |
|--------------|--------|
| Product rethink (CEO) | Scope challenge → `/adr` or `/open-questions` |
| Plan / eng manager | mattpocock **`to-spec`** (paths) + DoD list |
| Build | Coding agent + karpathy / ponytail; **`/one-shot`** if DoD + lab ready; **`/agent-loops`** to set exits/type before long runs |
| Debug / RCA | **`/investigate`** — Iron Law: no fix without root-cause hypothesis (T-0017) |
| Review | mattpocock **`code-review`** (paths); optional second persona |
| QA | `make cage-test`, `make smoke-*` (see [docs/modules/examples-smokes.md](docs/modules/examples-smokes.md)); **`prefer-behavior-and-fail-recover-tests`** |
| UI / operator surface | **`ui-is-the-app-design-in-loop`** — design pack in `docs/design/` before product UI |
| Security | write-guard + cage policy; not full gstack `/cso` |
| Ship | Feature branch → green checks → merge; [DEPLOY.md](docs/ops/DEPLOY.md) |
| Reflect | **`/hermes-feedback`** (memory + optional skill/curator); TODO/OQ; `/docs` or `/catalog-docs` if modules changed |
| Marketing multi-view | **`/marketing-council`** |

Full recipes and non-goals: **[docs/ops/gstack-role-recipes.md](docs/ops/gstack-role-recipes.md)**.  
Deeper-port scores (why not raw gstack install): **[docs/ops/gstack-skill-port-comparison.md](docs/ops/gstack-skill-port-comparison.md)**.  
Do **not** clone garrytan/gstack into this repo (ADR-0009).

### Scaffold process into another repo

```bash
./bootstrap/project-process/init.sh /path/to/repo --name <name> --vision "..."
# or: /project-process init <path>
```

## Advanced Agentic Workflows & Harness Practices (enhanced guidance)

This repo supports robust, production-like agentic coding setups inspired by high-signal workflows (e.g., comprehensive agentic checklists and harness engineering principles). Use these to make interactions more reliable, observable, and self-improving.

### AGENTS.md as Router & Onboarding
- Treat this file as the primary **router**: It directs agents to the right skills, docs, tools, and processes based on task type (research, planning, implementation, review, autonomous work).
- Include or reference summaries of key docs for quick greppability (first 7 lines of important files should be self-descriptive).
- Agents should use this to discover and load context dynamically.

### Self-Healing & Living Documentation
- Agents are encouraged (and instructed via skills/docs) to keep relevant docs updated as part of their work ("self-healing docs").
- For every system or module, maintain up-to-date docs; tag or let agents discover them via AGENTS.md.
- Commit updates with the work.

### Traces, Worksheets & Session Continuity
- For non-trivial or multi-session tasks, create or update **agent traces/worksheets** that record actions, decisions, blockers, and progress.
- Commit these with the work (use git tags for easy reference, e.g., corresponding to worksheet names).
- This enables handoff: another agent (or future session) can pick up exactly where left off.
- Reference in open-questions or TODOs as needed.

### Cross-Agent Reviews & Personas
- At major milestones (research, plan, implementation, wrap-up), perform cross-agent reviews using different models or personas where possible.
- Personas/examples: maintainability expert, security reviewer, performance analyst, "AI smells" detector, domain specialist.
- Document review criteria in dedicated docs or skills; agents should own/update related system docs.

### Custom Scripts, Tools & Automation
- Maintain a `tools/` or `bin/` folder with Python/bash scripts that simplify agent tasks (e.g., agent_review CLI wrapper, test runners, benchmark helpers).
- Agents should be skilled at creating and documenting new helper scripts as needed.
- Include docs on effective script creation.

### Autonomous & Night-Shift Work
- Support agent loops for autonomous work via dedicated skills or docs (e.g., night-shift orchestration: how to approach tasks, use task queue, report back).
- Task queue example: TODOS.md or integrated system (e.g., Linear with CLI access).
- Periodic sweeps: Agents can review recent commits for problems/gotchas at a higher level.

## Testing standing rule
Prefer the Testing Trophy: mostly integration/E2E for product confidence. Unit tests only for shaky/non-obvious behavior. Forbidden: tautological tests and implementation-detail tests. Prefer sociable tests; doubles only at awkward boundaries + contract tests for externals. Every non-trivial change: How could this fail? How do we recover?

Skill and verbatim DoD paste line: **`prefer-behavior-and-fail-recover-tests`**.

## Modular CI (standing rule)

Landing work follows [docs/ops/MODULAR-CI.md](docs/ops/MODULAR-CI.md):

- run only the tests a change can affect
- run tests once per commit and cache the result
- no global lock or single runner for light jobs
- run non-GPU checks in parallel on hosted runners or containers
- give each tool its own state file
- cache tool and image layers
- only jobs bound by local-model token speed get a long serialized lane
- the full suite runs nightly as a backstop
- trading, release and secret changes always get the full run

## Pipeline changes check the catalog first

Before building any new or changed pipeline, CI, or gate step, check the cataloged tools that cover the job: [docs/eval/TOOLSET-RANKING.md](docs/eval/TOOLSET-RANKING.md) and the `uses`, `features`, and `tags` on `data/stages/<slug>.json`. Then answer software-factory's five questions. They are copied from mattpocock/skills at commit `4ae2317`, file `skills/in-progress/software-factory/SKILL.md` (https://github.com/mattpocock/skills). That skill is not vendored in this repo.

1. What triggers it?
2. What does it do, and which services does it read and write?
3. What does it trigger next?
4. Where does a human re-enter?
5. What stops two runs doing the same work?

Catalog pipeline skills, same SoT and a full copy under `.grok/skills/`: **`catalog-intake-dedupe`**, **`catalog-eval-lane`**, **`catalog-integrate-lane`**, **`catalog-apply-and-ceiling`**, **`catalog-fit-triage`**, **`catalog-loop-operator`**. They name the scripts. They do not reimplement them.

A tool whose uses cover CI, testing, or review cannot reach I3 until it has been applied to this repo's own pipeline, or a recorded reason says why not. The field is `self_pipeline` on the stage card. The check is `scripts/catalog_check.py`. Scheme: [docs/ops/integration-stages.md](docs/ops/integration-stages.md).

## Design-in-loop (UI is the app)

Operator-facing UI follows **`ui-is-the-app-design-in-loop`**: design pack in `docs/design/` before product UI; never ask what we already know; levers stay on the current view. Lab bolts are allowed; product/dogfood UI needs a Design pass. Verbatim DoD paste line is in that skill. This slice adds no product UI. Ops: a private ops note.

## Gate path (BEST_EFFORT default)

Docs, skills, and reversible dogfood follow the best-effort rule: land on a named branch and PR; do not share an open founder Build checkout; no Feature GO from the port.

### Verification, Benchmarks & Quality Gates
- Agents must run and test their changes (build, targeted tests, end-to-end where applicable).
- Prefer integration/E2E and behavior-level coverage over unit sprawl; unit tests only where behavior is shaky or non-obvious. Update test docs/lists when coverage meaningfully changes.
- Custom linters/pre-commit with auto-fix (or LLM-assisted fix for complex cases) — focus on actually cleaning code, not just flagging.
- Periodic audits: false-confidence test reviews (tests that don't actually test what they claim — including tautological and implementation-detail tests), performance benchmarks/profiling.
- Visual regression (screenshots + agent review) and automatic performance degradation detection where relevant.
- End-of-shift or major milestone full validations: run tests, reviews, sweeps, benchmarks, etc.

### Feedback & Continuous Improvement
- Agents should provide automatic end-of-session feedback (what worked, issues, suggestions), committed to a reviewable doc.
- Periodically ingest this feedback in interactive sessions to refine workflows, skills, and docs.
- Combine with harness engineering principles: focus on scaffolding, context, verification, observability, and constraints around the model for reliability.

These practices draw from production agentic setups and harness engineering resources. Adapt and extend via skills in `bootstrap/grok-cli/skills/` and project templates. Prioritize composable, controllable elements over monolithic frameworks.

Reference related resources: Learn Harness Engineering site, Matt Pocock skills (planning/TDD/review via paths), gstack **role patterns** (docs only — [gstack-role-recipes.md](docs/ops/gstack-role-recipes.md)), and repo process docs for implementation.
