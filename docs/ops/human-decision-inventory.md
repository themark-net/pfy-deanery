# Human decision inventory (minimize per-item questions)

**Purpose:** Map branching decisions so agents **batch** operator input and build automation loops instead of asking one question at a time.  
**Rule:** Prefer defaults + reversible experiments. Only escalate when blast radius is high or OQ is P0/P1.

## When to open an OQ (vs catalog / TODO only)

| Open an **OQ** (may block work) when… | Do **not** open an OQ when… |
|--------------------------------------|-----------------------------|
| No safe reversible default | Safe default exists (e.g. skip install, pin only, LiteLLM) |
| Blast radius high (weights disk, primary runtime, security default) | Optional catalog tool / niche desktop app |
| Architecture fork (ADR-class) | Priority/scheduling only (“do this later”) |
| Operator must choose among mutually exclusive product paths | Evaluation pipeline can hold I1 notes forever |
| P0/P1 critical path cannot proceed | P2/P3 “nice to eval someday” |

**Antigravity lesson (OQ-0007, 2026-07-30):** “Do we need multi-account relay?” had a safe default (**no / LiteLLM**). It belonged in the **evaluation rubric + I1 catalog** (low priority), not a blocked OQ + blocked TODO. Process gap was **over-promotion of optional tool adopt to OQ**.

**Fix agents must apply:**

1. Optional tool → **I1 staged evaluation** (uses / features / potential / non-goals) + catalog tier.  
2. Default = **no runtime install** unless smoke path is cheap and already green.  
3. TODO may exist at **P3** (“eval if pain appears”); **do not** set Status=`blocked` on an OQ that is only preference.  
4. OQ only if install/weights/embed would change disk, security, or primary stack - or operator explicitly escalates pain.

Related: [integration-stages.md](integration-stages.md) · [evaluation-framework.md](../evaluation-framework.md) Phase 3.

## Pending decisions (estimate)

| Bucket | Count | Automation loop (instead of N chats) |
|--------|------:|--------------------------------------|
| **Blocked OQs (P2)** | **0** | Batch done 2026-07-30 |
| **Optional tool adopt** | defaults below | **I1 + skip install**; lower priority in eval pipeline - **not** OQ |
| **Cage/env polish** | **0 for this track** | Parked |
| **Product forks needing ADR** | **0 open P1** | None until architecture pivot |
| **Hybrid surfaces (ADR-0011)** | **0** | Defaults set |
| **Voice channel (OQ-0010)** | **0** | ADR-0012 |
| **Total decisions needed from you** | **0-1** | Only colibri weights if you care |

**Bottom line:** Design/coding track needs **no** human input. Optional tools stay in catalog eval at appropriate priority. Do not recreate Antigravity-style blocking OQs.

---

## Branch maps

### B1 - Optional catalog tool (coding assist)

```text
Phase0 gate: open-source + local + coding/design assist?
  NO → catalog C/awareness only; stop
  YES → Record I1 (uses, features, potential, non-goals)
         Structural lane green? (make eval-structural)
          NO → fix structural; stop
          YES → Fits existing skill/smoke path?
                  YES → implement skill or smoke; no human
                  NO → Default: docs/pattern extract + tier; priority by opportunity
                       Need runtime install/weights/subtree with HIGH blast radius?
                         YES → add OQ row (batch later); do not ask ad hoc
                         NO → P3 TODO or catalog note only; **no OQ**; no blocked TODO
```

**Human decisions if high-blast runtime needed:** 1 (allow install/weights?) - OQ batch, not chat.  
**Not a human decision:** “should we maybe eval this later?” → lower priority in pipeline.

### B2 - New process skill (design/coding)

```text
Complex procedure ≥ threshold?
  NO → hermes memory / TODO only
  YES → first-party skill under bootstrap + manifest + eval-structural
        Pass? ship. Fail? fix until green. No human.
```

### B3 - Implement-lane model eval (needs Ollama)

```text
Ollama + gate model present?
  NO → record SKIP (exit 2); structural still PASS; no human
  YES → make eval-suite; fail → model/prompt fix loop (agent); no human unless infra missing on purpose
```

### B4 - OQ batch (historical + remaining)

| ID | Question | Status 2026-07-30 | Default if unanswered |
|----|----------|-------------------|----------------------|
| OQ-0003 | First subtree? | **answered** wait + integration stages | No subtree |
| OQ-0004 | ATG relationship? | **answered** submodule later | Catalog / I1 |
| OQ-0007 | Antigravity? | **answered** skip; stay low-pri eval | No |
| OQ-0008 | Colibri weights? | open | No download |

```text
OQ-BATCH: 0003=wait 0004=submodule-later 0007=skip 0008=?
```

---

## Defaults (agent may apply without asking)

| Topic | Default |
|-------|---------|
| Primary code memory | codebase-memory-mcp |
| Graphify / LEANN / Memvid | docs/reference until smoke |
| MUE-X | pattern extract only; no evolve in lab without pin+safety note |
| Laguna | catalog + DoD only; no weights in-repo |
| Bumblebee | design note; optional smoke when Go binary easy |
| **Antigravity-Manager** | **skip install**; catalog I1 low priority; LiteLLM + keys |
| AgenC | stay demoted (ADR-0010) |
| Write-guard mode | audit (OQ-0009 answered) |
| Eval without Ollama | structural PASS required; implement SKIP |
| Optional tool with safe default | **no OQ**; I1 + P3 TODO max |

---

## Automation loops to build next

1. **`make eval-structural`** in every design/coding PR (this repo).  
2. **OQ-BATCH parser** - one message closes N OQs.  
3. **Eval SKIP vs FAIL policy** - missing model = 2, not 1 (already for matrix cells).  
4. **Night-shift TODO** - only pick rows with Open questions = `-`.  
5. **`make cage-code-sync PUSH=1`** on host after any cage agent session (import commits + rsync).  
6. **OQ gate check** - before creating OQ, confirm no safe default and blast radius real (see table above).

## HD #33 - Host-lab / close policy (answered 2026-07-30)

**Not** docs-vs-host binary. Use **G0 structural · G1 deploy-ready (build+smoke) · G2 UX UAT (human)**.

- Agent closes runtime on **G1**.
- Human UAT only after **simple dual-sided deploy** meets UX standards.
- Tests/frameworks must themselves be deployable to publishing standards.

Canonical: [eval-gates-and-ux-uat.md](eval-gates-and-ux-uat.md) · `make eval-deploy-ready`
