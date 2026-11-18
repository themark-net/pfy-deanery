# One-shot workflow (minimize user questions, iterate cheaply)

**Status:** Accepted design (ADR-0008)  
**Related:** agent-cage harness, deployment profiles, write-guard, `/one-shot` skill  

## Intent

A **one-shot** is an agent mode for a single user request where:

1. **Questions back to the human are minimized** - only hard blockers that cannot be safely assumed.
2. **Cheap iterations run automatically** - local/zero-cost loops until the request’s success criteria pass or a hard stop is hit.
3. **Guardrails and prerequisites are mandatory** - no “yolo implement forever” without a test environment and a definition of done.

This is complementary to normal collaborative mode (many clarifying questions OK).

---

## Prerequisites (fail closed)

Before one-shot starts, **all** of the following must hold or the agent must **stop and ask once** (or refuse with a checklist):

| Prerequisite | How to verify |
|--------------|----------------|
| Repo process map known | `docs/DESIGN.md` + `AGENTS.md` readable |
| Deploy profile selected | `DEPLOY_PROFILE` set; `make env-check` passes for that profile |
| Isolation lab available **or** explicitly waived | Prefer: agent-cage `status` healthy **or** documented host-only smoke path in request |
| Success criteria written | Agent writes a short **Definition of Done (DoD)** before coding |
| Cost tier chosen | `local` / `cheap-cloud` / `allowed-cloud` - default from profile |

If cage is required by DoD (e.g. “integration test in container”) and cage is down: **one** question or a single automated `make cage-up-mcp` if docker is available and policy allows unattended up.

**Hard refuse (do not one-shot):**

- Destructive host ops outside workspace without write-guard + cage
- Secrets missing for a profile that requires them (`max-performance` without any cloud key)
- Request would embed large weights / buy infra without prior OQ/OK

---

## Cost ladder (iterate cheap → expensive)

Run verification and repair loops **bottom-up**. Do not burn expensive cloud models until cheaper layers fail.

| Tier | Examples | Use for |
|------|----------|---------|
| **0 - free/local static** | `json.load`, `make catalog-json`, linters, unit tests, `make env-check` | Always first |
| **1 - local model / Ollama** | Small coding models for generate/fix | bulk code, rewrites |
| **2 - cage integration** | Install tool in `/workspace`, policy tests, compose smokes | isolation proof |
| **3 - mid cloud** | Cheaper API models if profile allows | when local stuck |
| **4 - heavy cloud** | Grok / strong models | only if DoD needs it or lower tiers exhausted |

Profile mapping (default):

| `DEPLOY_PROFILE` | Max auto tier without asking |
|------------------|------------------------------|
| `local-only` | 0-2 only (no cloud) |
| `balanced` | 0-3; tier 4 only if DoD says “production quality” or 3 failed N times |
| `max-performance` | 0-4 allowed; still try 0-2 first for mechanical checks |

---

## One-shot loop

```text
1. Restate goal + write DoD (pass/fail checks) + list assumptions
2. Prerequisites check → fail closed or fix automatically if safe
3. Implement smallest change
4. Run cheapest applicable verification (tier 0 → …)
5. If fail: diagnose, fix, repeat from 3
6. Stop when:
   a. DoD all green → summarize + paths changed, OR
   b. Budget hit (max iterations / max tier) → stop with failure report + exact next human decision, OR
   c. Hard blocker (missing secret, destructive ambiguity) → ONE structured question
```

### Default budgets (overridable in request)

| Budget | Default |
|--------|---------|
| Max implement→test iterations | 8 |
| Max consecutive same-error loops | 3 then escalate tier or stop |
| Max cloud completion calls in one-shot | profile-dependent (local-only: 0) |
| Ask user | only hard blockers or budget exhaustion |

### What counts as a hard blocker (allowed to ask)

- Ambiguous product choice with **irreversible** consequences (data model, public API)
- Missing secret the operator must supply
- Explicit destructive scope (“wipe production”) without confirmation
- Prerequisite environment the agent cannot create (no Docker permission, no GPU, etc.)

### What must **not** ask (assume + document)

- Formatting, file layout within repo conventions
- Pin vs latest when ADR-0003 says pin
- Whether to run local tests if DoD includes them
- Whether to use cage if DoD says integration-in-container and cage can start

Assumptions go in the final report under **Assumptions**.

---

## Guardrails

1. **No silent scope creep** - DoD is the contract; extra polish only if free (tier 0-1) and small.
2. **Write-guard / workspace** - prefer edits under repo or cage `/workspace`; respect `WRITE_GUARD_MODE` when MCP is on.
3. **No secrets in git or images.**
4. **Prefer pins** (ADR-0003); no huge subtrees in one-shot.
5. **Triple-write catalog** if the request adds a tool seed (`/catalog-docs seed`).
6. **Record outcome** in TODO/OQ only if residual work or a new decision remains.

---

## Prerequisites matrix by request type

| Request type | Min lab |
|--------------|---------|
| Docs / ADR / TODO only | Host |
| Catalog row + JSON | Host + `make catalog-json` |
| Bootstrap skill change | Host + reinstall skill |
| New integration (LiteLLM, repowise, …) | **agent-cage up** + in-cage smoke |
| Grok-in-image | Cage + overlay build + runtime key |
| Full eval harness | Profile + local and/or cloud per OQ-0002 |

---

## Operator invocation

```text
/one-shot <request>
```

Or: “one-shot: …” / “unattended until green: …”

Agent should load this doc + profile + harness status, then enter the loop.

### Ready-made DoDs for this repo’s smokes

Copy-paste contracts for LiteLLM, codebase-memory, repowise, write-guard, and full regression:

→ **[one-shot-example-dods.md](one-shot-example-dods.md)**

| Green target | One-shot area |
|--------------|---------------|
| `make smoke-litellm-ollama` | LiteLLM → host Ollama (gateway :11435) |
| `make smoke-codebase-memory` | codebase-memory-mcp index+search |
| `make smoke-repowise` | repowise health (zero LLM) |
| `make smoke-context-tools` | both context tools + compare note |
| `make smoke-write-guard` | write-guard audit/enforce policy |

---

## Relationship to other modes

| Mode | Questions | Iteration |
|------|-----------|-----------|
| Collaborative (default) | Many OK | Human-paced |
| **One-shot** | Minimal | Auto cheap→expensive |
| Plan-only | Clarifying OK | No implement |
| YOLO without lab | Forbidden here | - |
