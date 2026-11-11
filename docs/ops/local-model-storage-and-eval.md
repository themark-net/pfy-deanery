# Local model storage & evaluation policy

**Status:** Accepted 2026-07-30 (OQ-0008)  
**Related:** [evaluation-framework.md](../evaluation-framework.md) · [eval-harness README](../../examples/eval-harness/README.md) · [integration-stages.md](integration-stages.md) · ADR-0003 (no weights in git)

## Intent

**Models are high-value** for this stack. We evaluate them seriously — not only via external leaderboards — using tasks this repo has already accomplished (human request → agent work). Storage is budgeted; downloads are gated by prior evidence + size class, not by a blanket “no weights.”

## Storage budget

| Limit | Value |
|-------|-------|
| **Total local model weights pool** | **≤ 250 GB** (operator-approved) |
| Location | Host / external path only — **never** commit to catalog git |
| Env knobs | `EVAL_DISK_BUDGET_GB` (fit selection), optional `MODEL_POOL_MAX_GB=250`, `MODEL_POOL_PATH` |
| Concurrent residency | Enough headroom for **several mini / small** models loaded or hot alongside larger experiments |

`select_ollama_models.py` already ranks by RAM + disk; set `EVAL_DISK_BUDGET_GB` against free space **within** the 250 GB pool policy (do not fill the pool with one model without a plan).

**Never** store weights under the pfy-deanery git tree (ADR-0003).

## Pre-download suitability ladder

Before `ollama pull` / HF download of a **large** model (roughly ≥ 15–20 GB class, e.g. colibri/GLM int4):

1. **External evidence scan** — existing evals, blogs, SWE-bench-ish reports, day-one Ollama/llama.cpp notes (catalog entry + X post).  
2. **X-post / operator-forward exception** — if the catalog seed already carries a **compelling, specific** argument to eval (flagship MoE, coding scores, day-one local path), may go to **direct lab eval** faster; still respect pool budget.  
3. **Do not rely solely on external sources** — lab must still run **golden / implement** tasks.  
4. **Mini models** — always evaluate for suitability as concurrent helpers (smoke, router, high-first low tier, cheap implement). Prefer keep several small coders hot under the same 250 GB pool.

Colibri specifically: **allowed within budget after steps 1–3**, not blocked as “never download.” Prefer external path; track size in an inventory note (not git LFS).

## Evaluation: golden tasks from this repo’s own work

### Idea

Models that built (or helped build) this repo already completed real work. Capture a **sample** of:

| Field | Meaning |
|-------|---------|
| **Human request** | What the operator asked (this chat message class) |
| **Agent task decomposition** | Subtasks the agent ran |
| **Artifacts / outcome** | Commits, files, issue updates, DoD |
| **Scale** | orchestration · multi-file · single-code · docs-only |

Then score a candidate model on **proximity** to the original accomplished outcome (not “vibes”).

### Sampling policy (feasibility)

- **Do not** require logging every human turn.  
- **Do** capture high-signal sessions: OQ resolutions, ADRs, P0/P1 TODOs, new eval lanes, product-surface changes.  
- Prefer **structured golden cards** under `data/golden-tasks/` over full chat dumps.  
- Optional later: session export tools (Grok cage sessions, OpenCode logs) — see catalog / tool queue below.

### Proximity scoring (lanes)

| Scale | How to score |
|-------|----------------|
| **Single code** | Existing implement tasks (`001`, `002`) + hidden tests |
| **Docs / process** | Structural text scorers + checklist fixtures |
| **Multi-step agent** | Golden task: prompt = human request; scorer checks required artifacts exist / shape (files, issue state, OQ status) |
| **Orchestration** | Worker/monitor or voice-orchestrate smokes + golden “exit card” completeness |

New lane id (planned): **`golden_replay`** in `data/eval-lanes.json` — may require LLM; missing model → SKIP (exit 2).

## Immediate vs queued

| Piece | Now | Later |
|-------|-----|-------|
| Policy + 250 GB budget | **Done** (this doc) | Tune pool inventory script |
| Golden-task schema + seed cards | **Started** (`data/golden-tasks/`) | Auto-export from sessions |
| Fit selection disk/RAM | **Exists** (`select_ollama_models.py`) | Wire default `MODEL_POOL_MAX_GB=250` docs in pins.env |
| Mini concurrent suitability | Matrix + tools-model select | Explicit “mini set” pin list |
| Colibri / large MoE lab | After evidence scan + free pool headroom | T-0016 unblocked as **eval when ready** |
| Full chat→golden pipeline | Queue | Tools: session resume mounts, hermes memory patterns, codebase-memory — document only until implement |

## Catalog tools useful for capture (queue)

Document in entries / ops; implement when cheap:

| Capability | Possible sources in catalog / stack |
|------------|-------------------------------------|
| Session persistence | Cage Grok session mount / import (T-0047 done) |
| Operator memory | hermes-feedback skill; memory-assist patterns |
| Repo-grounded recall | codebase-memory-mcp, repowise |
| Structural regression | `make eval-structural` |
| Implement regression | `make eval-suite` / `eval-auto` |

## Agent rules

1. Before large download: write a short **suitability note** (external + why X-post is compelling) under golden-tasks or catalog entry.  
2. Stay under **250 GB** total weights; prefer deleting demoted models over growing the pool.  
3. Always keep **≥ 1–2 mini** coding models for concurrent low-tier work.  
4. Prefer golden_replay + implement over hype for “is this model good for *us*.”  
5. Never commit weights.

## Resolution source

OQ-0008 (2026-07-30): Models interesting; pre-eval with external evidence when possible; X-forwarded models may eval more directly; 250 GB total OK; concurrent minis; primary lab metric = proximity to tasks already done building this repo; sample human+agent documentation; document tooling and queue full capture if not immediate.
