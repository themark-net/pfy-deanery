---
name: agent-loops
description: >
  Design and run agent work as proper loops: pick loop type (turn / goal /
  time / proactive), write the eight mandatory exits before coding, apply
  Finn-style spec→build→review with a human gate, and optional rubric eval
  passes. Use when the user runs /agent-loops, /loops, "write exits first",
  "eight exits", "8 exits", "Finn loop", "loop engineering", "stop conditions",
  "agent loop design", "no infinite retry", or wants structured autonomous
  iteration without hanging or burning budget.
argument-hint: "[plan | run | audit | exits] [optional goal]"
---

# /agent-loops — Loop engineering for Grok (pfy-deanery)

**Iron Law: WRITE THE EXITS BEFORE YOU WRITE THE LOOP.**

A loop with one exit hangs. A loop with eight is a system. Most agents only
ship “stop when the model says done” — that is not enough.

**Pattern, not a new runtime.** Distilled from catalog loop engineering
(Entries **024** Finn, **027** four types, **031** generate→test→update,
**032** rubric eval, **068** eight exits). First-party for Grok Build +
agent-cage + `/one-shot`. No Hermes/AgenC/gstack install.

See [PORT.md](PORT.md).

## When to run

- Designing multi-step autonomous or semi-autonomous work  
- User: `/agent-loops`, “eight exits”, “Finn loop”, “loop engineering”  
- Before `/one-shot` on non-trivial builds (ensure exits/budgets match)  
- Auditing an existing skill, smoke, night-shift, or company-style workflow  
- After hangs, infinite retries, or surprise token bills  

**Do not** use this for single-turn Q&A with no iteration.

## Modes

| Argument | Behavior |
|----------|----------|
| *(none)* or `plan` | Choose loop type + write exit card + handoffs (default) |
| `run` | Execute a planned loop (or infer plan, then run) with live exit checks |
| `audit` | Review an existing workflow/skill/script against the 8 exits + type fit |
| `exits` | Print/fill only the eight-exit checklist |

---

## Step 0 — Exit card (always first)

Fill this **before** implement/iterate. Defaults in brackets are pfy-mentat-friendly;
override per task.

```text
LOOP EXIT CARD
════════════════════════════════════════
Goal (success criteria):     [observable DoD / rubric — not "looks good"]
1 Goal met:                  [who evaluates: test | make smoke | human | model score]
2 Turn cap:                  [default 8 iterations]
3 Budget cap:                [tokens/$ OR profile max tier — local-only: no cloud]
4 Wall clock:                [e.g. 30m session / deploy window / —]
5 No-progress:               [N identical outcomes = 3; hash: test output | git diff | error text]
6 Human interrupt:           [when to ask; kill switch = user stop / cage down]
7 Error threshold:           [3 consecutive same failure → stop or escalate tier]
8 External event:            [PR merged | ticket closed | OQ answered | — n/a]
Loop type:                   [turn | goal | time | proactive]
Human gate:                  [where approval is required]
════════════════════════════════════════
```

**Rule:** If any of 1–7 is blank for a multi-iteration task, **stop and fill it**.
Exit 8 may be `n/a` for pure local coding loops.

---

## Step 1 — Choose loop type (Entry 027)

Loop engineering answers: **what starts a run** and **what decides work is done**.
Pick by task shape — not by “most autonomous.”

| Type | Starts when | Done when | Best for | pfy-deanery default |
|------|-------------|-----------|----------|--------------------|
| **Turn-based** | User message | End of turn; human next prompt | Exploratory, requirements forming | Normal chat |
| **Goal-based** | Goal + success criteria + budget | External check of criteria | Measurable outcomes | **`/one-shot`**, eval-harness, this skill `run` |
| **Time-based** | Clock / schedule / interval | Fixed prompt finished or exits fire | Recurring known tasks | scheduler / cron + smokes |
| **Proactive** | Event (CI fail, webhook, ticket) | Workflow + adversarial review done | Standing ops | cage night jobs later; not default |

**Mapping tips**

- Spec still mushy → **turn**, then promote to **goal** once DoD is written.  
- “Green when `make smoke-X` passes” → **goal**.  
- “Every morning re-check catalog JSON” → **time**.  
- “On CI red, triage and open OQ” → **proactive** (needs harness + exits).

---

## Step 2 — Structure the work (Finn-inspired, Entry 024)

For non-trivial delivery, prefer three phases with a **human gate** before merge/ship:

| Phase | Intent | This stack |
|-------|--------|------------|
| **Spec** | Idea → clear criteria, files, risks | mattpocock **`to-spec`**, DoD list, optional `/open-questions` |
| **Build** | Implement against spec | Grok + karpathy/ponytail; **`/one-shot`** if DoD + lab ready |
| **Review** | Correctness / security / blast radius | mattpocock **`code-review`**; cage smokes; human approve merge |

**Human gate (required for ship):** user approval, PR review, or explicit “merge ok” —
not an emoji to a third-party bot unless the operator already runs that channel.
Do **not** force-push main or skip gates “because the loop is autonomous.”

Multi-session OK: separate sessions for spec / build / review as long as the
**exit card** and DoD live in-repo (TODO, PR body, or short worksheet).

---

## Step 3 — Eval layer (Entry 032 + 031)

When quality matters (not pure mechanical green tests):

1. **Write a rubric first** (pass/fail or 0–1 dimensions).  
2. Draft / implement.  
3. **Score** against the rubric (tests preferred; model self-score only as weak layer).  
4. Below bar → another pass (counts as a **turn**).  
5. Every real miss → **add a permanent line** to the rubric or a regression test.

**Rigor ladder (match stakes):**

| Layer | Use when |
|-------|----------|
| Self-check | Low stakes, drafts |
| Independent check | Different prompt/model or second agent |
| Suite / smoke | Default for this repo (`make smoke-*`, `make eval-*`) |
| Human gate | Ship, public API, destructive ops |

**Generate → test → update context:** failed checks become facts for the next
iteration (not silent retry with the same broken assumption).

---

## The eight exits (Entry 068) — detail

| # | Exit | Trigger | Failure mode it prevents | Enforce how (Grok) |
|---|------|---------|--------------------------|--------------------|
| 1 | **Goal met** | External evaluator passes rubric/DoD | “Model claims done” lies | Tests, `make smoke-*`, checklist — not vibe |
| 2 | **Turn cap** | Iteration count ≥ N | Infinite implement→fail | Hard count; default **8** (`/one-shot`) |
| 3 | **Budget cap** | Tokens, $, or **cost tier** max | 3am bill / profile breach | `DEPLOY_PROFILE` max tier; stop at cap |
| 4 | **Wall clock** | Elapsed ≥ deadline | Missed window / runaway session | State deadline in exit card; stop and report |
| 5 | **No progress** | N consecutive identical state hashes | Busy loop, same error/diff | Hash error text, test output, or `git diff` summary; default **N=3** |
| 6 | **Human interrupt** | User stop, approval denied, kill | Unstoppable autonomy | Always honor user; pause on irreversible fork |
| 7 | **Error threshold** | N consecutive failures (reset on success) | Whack-a-mole thrash | Default **3** then stop **or** escalate cost tier once, then stop |
| 8 | **External event** | Work obsolete (merged, closed, superseded) | Solving yesterday’s ticket | Check PR/issue/OQ status when relevant |

### Progress hash (practical)

After each iteration, record one line:

```text
state: <pass|fail> | tests: <cmd summary> | diff: <files changed count or short hash> | err: <first line or none>
```

If this line equals the previous for **N** iterations → **exit 5**, report stuck.

---

## Mode: `run` (execute with exits)

1. Restate goal; if no exit card, write one (Step 0).  
2. Confirm loop type (default **goal** for measurable work).  
3. Loop:
   - smallest change → cheapest verification (see `/one-shot` cost ladder)  
   - update progress hash  
   - check **all eight** exits after every iteration  
4. On any exit: **stop**, emit **LOOP REPORT** (below). Do not “just one more try”
   after exit 2/3/5/7 without human override.

**Relationship to `/one-shot`:** one-shot **is** a goal-based loop with budgets.
`/agent-loops run` is for when you need an explicit exit card, non-default
caps, multi-phase Finn structure, or audit-grade stop conditions.
Prefer `/one-shot` for standard “green DoD” delivery; use this skill when
designing or hardening the loop itself.

**Relationship to `/investigate`:** bugs need RCA **before** a fix loop.
Investigate → then agent-loops/one-shot to implement.

---

## Mode: `audit`

Given a skill, Makefile target, scheduler job, or prose workflow:

1. Infer loop type (or flag “unclear”).  
2. Score each of 8 exits: **present / weak / missing**.  
3. Flag: only exit 1; no turn/budget; no no-progress; human cannot interrupt.  
4. Recommend minimal patches (numbers, make targets, approval points).  
5. Do **not** expand scope into a rewrite unless asked.

---

## LOOP REPORT template

```text
LOOP REPORT
════════════════════════════════════════
Type:            turn | goal | time | proactive
Goal:            ...
Exit fired:      #N name — detail
Iterations:      k / turn_cap
Progress:        last state hash / why stuck or green
Evidence:        commands + key output
Human gate:      pending | approved | n/a
Next:            (one line — or DONE)
Status:          DONE | STOPPED_EXIT | BLOCKED | NEEDS_HUMAN
════════════════════════════════════════
```

---

## Handoffs (this stack)

| Situation | Next |
|-----------|------|
| Clear DoD + lab, just ship | `/one-shot` |
| Bug / regression | `/investigate` first |
| Architecture pivot | `/adr` |
| Unsettled choice | `/open-questions` |
| Compound learnings after loop | `/hermes-feedback` if installed; else TODO/memory |
| Catalog smoke as goal | `docs/ops/one-shot-example-dods.md` + `make smoke-*` |
| Structural design/coding gate | `make eval-structural` (no LLM) before claiming skill work green |
| Cheap bulk / local **worker** | OpenCode (or LiteLLM client) → Ollama `LOCAL_CODER_MODEL` (e.g. deepseek-coder:6.7b). Grok CLI does **not** auto-switch. |
| Hard design / review / monitor | Grok Build subscription — set DoD, review worker, escalate after 3 fails |
| Product end-user simplicity | Prefer 3 levers: onboard / stage / ship — [product-operator-surface.md](../../../../docs/ops/product-operator-surface.md) |
| Operator batch (not ad hoc) | `docs/ops/human-decision-inventory.md` |
| Review before merge | mattpocock `code-review` |
| Night / recurring | time-based + exit card; prefer cage |

## Do not

- Ship a loop with only “model says done”  
- Infinite retries after turn/error/no-progress exits  
- Burn cloud before local/static checks when profile forbids it  
- Override human interrupt or force-push past gates  
- Install third-party loop frameworks as required runtime  
- Confuse **busy** (many tool calls) with **progress** (state hash changed)  

## Attribution

- Four loop types — public loop-engineering pedagogy (Entry 027)  
- Finn-style spec/build/review + human gate (Entry 024)  
- Rubric eval loop (Entry 032); generate→test→update (Entry 031)  
- Eight exits taxonomy — @hanakoxbt (Entry 068)  
Skill text owned first-party under pfy-deanery (T-0050).
