# Evaluation Rubric: Autonomous AI Companies

**Status:** v1.0 - 2026-07-20  
**Purpose:** Separate evaluation criteria for full multi-agent "AI company" systems (org charts, role personas, shared memory/consensus, cycle-based autonomous operation). These are **not** single tools or skill packs; they are complete simulated organizations.

**Why separate?**  
Standard Stage 1-4 scoring (LLM compatibility, tok/s, Docker glue, stars) underweights what matters here: role fidelity, consensus quality, safety under autonomy, economic realism, and whether the loop actually *converges* instead of thrashing. A 14-agent Bezos/Vogels/Munger company that burns tokens forever without shipping is a different failure mode than a slow Ollama server.

**Operator default:** Grok Build CLI + agent-cage. These systems are evaluated as **patterns + optional external runtimes**, not as replacements for the primary stack ([ADR-0010](../adr/0010-reject-agenc-as-primary-runtime.md)).

---

## Category Definition

**Autonomous AI Companies** = systems that:

1. Define a multi-role org (CEO, CTO, eng, product, marketing, critic, etc.) with **named personas** or mental models (not generic "helpful assistant").
2. Run **cycles or loops** (wake → read shared state → form squad → act → write consensus → sleep) with minimal or no human in the loop after start.
3. Maintain **shared memory** (markdown consensus file, vault, board, or equivalent) that persists across cycles.
4. Aim at **end-to-end outcomes** (ideate → decide → build → deploy → market), not just chat or single-task coding.

**In scope examples:** Auto-Company, paperclipai/companies templates, large Claude Company org-chart stacks when run as closed-loop orgs, Multica when used as full agent teammates board + skills compound.

**Out of scope (stay in other categories):**
- Single coding agents (Aider, Continue, OpenCode)
- Skill packs without a company runtime (mattpocock/skills, marketing-council)
- Pure loop pedagogy without org (Finn Loop docs, 4-tier autonomy guides)
- Isolated memory backends (Memvid, LEANN)

---

## Stage 0 Gate (binary)

Must pass all to enter the catalog under this category:

| Gate | Pass criteria |
|------|----------------|
| Self-hostable | Runnable on a personal machine (or clear Docker/self-host path); not cloud-only SaaS |
| Reproducible bootstrap | Documented install + start; clone → run in <30 min for a motivated operator |
| Open inspection | License allows reading/forking; agents/prompts/skills visible (not black-box API-only) |
| Shared state | Explicit shared memory or consensus artifact (file, DB, board) across cycles |
| Multi-role | ≥3 distinct roles with differentiated instructions/personas |

Fail any gate → track as D/Watch under Agent Frameworks, or reject.

---

## Scoring Dimensions (1-5 each)

Use integer 1-5. Overall = weighted average (see weights). Map to S/A/B/C priority bands below.

### C1. Org Design & Role Fidelity (weight 20%)

| Score | Criteria |
|-------|----------|
| 5 | Named expert personas (Bezos, Vogels, Munger, DHH…) with deep mental models; clear strategy / product / eng / critic layers; role load-on-demand skills |
| 4 | Clear department roles + some persona depth; critic or inversion role present |
| 3 | Generic titles (CEO, engineer) with light specialization |
| 2 | Flat multi-agent with weak role separation |
| 1 | "Team of agents" in name only |

### C2. Autonomy & Cycle Design (weight 20%)

| Score | Criteria |
|-------|----------|
| 5 | Explicit cycle types (brainstorm → pre-mortem → build); pure discussion loops forbidden; GO/NO-GO gates; daemon 24/7 path |
| 4 | Documented multi-phase loops with evaluator/critic; scheduled or continuous run |
| 3 | Loop exists but easy to thrash or stay in chat mode |
| 2 | Human still drives every turn after start |
| 1 | No real cycle; one-shot multi-agent chat |

### C3. Shared Memory & Consensus (weight 15%)

| Score | Criteria |
|-------|----------|
| 5 | Single durable baton (e.g. consensus.md) human-editable to steer; versioned; no heavy orchestrator bloat required |
| 4 | Solid shared store (vault, board, DB) with clear handoff |
| 3 | Memory present but opaque or multi-system |
| 2 | Ephemeral chat history only |
| 1 | No shared state |

### C4. Safety & Blast Radius (weight 15%)

| Score | Criteria |
|-------|----------|
| 5 | Explicit forbidden actions (no repo delete, no force-push main, credential isolation); Munger-style veto; human can pause via consensus edit; works under cage/write-guard |
| 4 | Documented guardrails + limited blast radius |
| 3 | Some safety notes; weak enforcement |
| 2 | Powerful tools, little policy |
| 1 | Unrestricted shell/API with no policy |

### C5. Economic Realism & Convergence (weight 15%)

| Score | Criteria |
|-------|----------|
| 5 | Honest cost model; unit-economics / market checks in loop; designed to ship or NO-GO; not infinite brainstorm |
| 4 | Cost awareness + some ship pressure |
| 3 | Acknowledges cost; weak convergence design |
| 2 | Token furnace with no product discipline |
| 1 | No cost or outcome model |

### C6. Local / Operator Fit (weight 15%)

| Score | Criteria |
|-------|----------|
| 5 | Runs on consumer HW with Claude Code / Codex / OpenCode / Grok-class CLI; local dashboard; macOS/Linux/Windows path; pin-friendly |
| 4 | Self-host workable; some cloud coupling OK |
| 3 | Self-host possible but painful |
| 2 | Primarily cloud multi-agent SaaS |
| 1 | Closed proprietary only |

---

## Priority Bands

| Band | Weighted avg | Meaning |
|------|--------------|---------|
| **S** | ≥4.4 | Study deeply; extract patterns into Grok skills/docs; optional external smoke |
| **A** | 3.6-4.3 | Plan pattern ports; compare org design; no mandatory runtime |
| **B** | 2.8-3.5 | Reference / inspiration |
| **C** | <2.8 | Awareness only |

**Integration posture (always):**
- Prefer **pattern extraction** (personas, consensus.md baton, pre-mortem critic, cycle gates) into first-party skills and AGENTS.md.
- Do **not** adopt full company daemons as primary operator runtime without ADR.
- Optional: pin + document external run; cage smoke only if isolation story is clear.

---

## Comparison Checklist (when evaluating 2+ companies)

1. Number of roles + persona depth  
2. Consensus artifact (format, human steerability)  
3. Critic / inversion / pre-mortem presence  
4. Forbidden-action table  
5. Cost per cycle honesty  
6. Engine support (Claude Code, Codex, OpenCode, local models)  
7. Dashboard / observability  
8. Overlap with Multica board, gstack roles, Hermes feedback loops, paperclip templates  

---

## Related

- [CATEGORIZATION.md](../../CATEGORIZATION.md) - primary taxonomy  
- [evaluation-framework.md](../evaluation-framework.md) - general tool pipeline  
- [scoring-summary.md](../scoring-summary.md) - cluster scores  
- Prior company-adjacent entries: 016, 037, 050, Multica (012), gstack (010), Hermes (048)  
