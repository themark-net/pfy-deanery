# Loop engineering (operator map)

**Status:** Active · Skills: `/agent-loops` (T-0050), `/one-shot` (ADR-0008), `/hermes-feedback` (T-0048), `/investigate` (T-0017)  
**Catalog:** Finn Loop / eval-loop / 8-exits row · Entries 018 · 024 · 027 · 031 · 032 · 048 · 068  
**Verify skills:** [skill-verification.md](skill-verification.md)

## Iron laws

1. **Write exits before the loop** (Entry 068) — a loop with one exit hangs.  
2. **No fix without root cause** when debugging (`/investigate`).  
3. **DoD before unattended build** (`/one-shot`).
4. **Grill before a CI, pipeline, or gate ticket is cut.** Tools off, turn cap 12, coordinator answers, behavior changes become exit tests. Command and the nimo flag check: [GRILL-STEP.md](GRILL-STEP.md).

## Which skill when

| Situation | Skill / action |
|-----------|----------------|
| Design stop conditions, pick turn/goal/time/proactive | **`/agent-loops plan`** or **`exits`** |
| Run a goal-based delivery with cost ladder | **`/one-shot`** (DoD from [one-shot-example-dods.md](one-shot-example-dods.md)) |
| Audit an existing workflow for missing exits | **`/agent-loops audit`** |
| Bug / regression | **`/investigate`** then one-shot/loops |
| End of multi-step work: memory + optional skill draft | **`/hermes-feedback`** |
| Architecture pivot | **`/adr`** |
| Parked product/tech choice | **`/open-questions`** |

## Four loop types (Entry 027)

| Type | Starts | Done | Default here |
|------|--------|------|--------------|
| Turn | User message | End of turn | Normal chat |
| Goal | Goal + criteria + budget | External check of DoD | `/one-shot`, eval-harness |
| Time | Schedule / interval | Prompt finished or exit fires | Future cage cron / host scheduler |
| Proactive | Event (CI, ticket) | Workflow + review | Later; not default |

## Eight exits (Entry 068) — checklist

Copy into any multi-iteration plan:

1. **Goal met** — tests / `make smoke-*` / human rubric (not “model says done”)  
2. **Turn cap** — default 8 (`/one-shot`)  
3. **Budget cap** — tokens / $ / `DEPLOY_PROFILE` max tier  
4. **Wall clock** — session or deploy window  
5. **No progress** — identical state hash N times (default 3)  
6. **Human interrupt** — always honor stop / approval  
7. **Error threshold** — N consecutive same failures (default 3)  
8. **External event** — work obsolete (merged, closed) or n/a  

Structural proof that skills exist: `make smoke-grok-skills`.  
Behavioral proof: [skill-verification.md](skill-verification.md) Layer 2–3.

## Finn phases (Entry 024)

Spec → Build → Review, with a **human gate** before merge/ship. Map to mattpocock `to-spec` / Grok build / `code-review` + cage smokes.

## Eval layer (Entry 032)

Rubric first → draft → score → miss becomes permanent rubric/test line. Prefer suite smokes over self-score for this repo.

## Related Make targets

| Target | Role |
|--------|------|
| `make eval-structural` | Design/coding gates (no LLM) — **always run** |
| `make smoke-grok-skills` | Skills on disk + manifest |
| `make cage-grok` | Full operator ladder (auth refresh + skills install) |
| `make cage-grok-skills-install` | First-party skills → cage `GROK_HOME` only |
| `make smoke-*` / `make eval-v02` | Goal exits for integration / model tasks (Ollama) |
