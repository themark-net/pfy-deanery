# Eval gates, deploy readiness, and UX UAT (HD #33)

**Status:** Accepted 2026-07-30 · **Source:** [issue #33](https://github.com/themark-net/pfy-deanery/issues/33)  
**Related:** [data/eval-lanes.json](../../data/eval-lanes.json) · [product-operator-surface.md](product-operator-surface.md) · [design-coding-assist-rubric.md](../evaluation/design-coding-assist-rubric.md)

## Decision (not “docs vs host-proof”)

Do **not** treat “agent closed the issue” as “humans accepted the product.”  
Create **separate gates**:

| Gate | Who | Bar | Closes agent work? |
|------|-----|-----|--------------------|
| **G0 Structural** | Agent/CI | `make eval-structural` (+ golden validate) | Yes for docs/skills schema |
| **G1 Deploy-ready** | Agent/CI | **Build green + smoke** on a deploy that matches publish standards | Yes for runtime features |
| **G2 UX / UAT** | **Human** | User acceptance tests against a real simple deploy (client + our env) | **No** — agents refine DoD until humans pass |

**Build green + smoke is sufficient** for agents to mark implementation **done-for-merge**.  
**Human testing always reveals UX design issues** — that is expected, not a process failure.

## Why another gate (not “always need human before close”)

1. Blocking every issue on human lab wastes human attention on framework wiring.  
2. Shipping only “frameworks that test frameworks” without **deploying those tests** to the same standard as product leaves a false green.  
3. UAT without a **simple, equivalent deploy** on both sides is not real UX testing.

## G1 — Deploy-ready (agent close bar for runtime)

A change is deploy-ready when:

1. **Structural** green (always).  
2. **Relevant smoke(s)** green *or* explicit soft-SKIP with reason (missing optional backend).  
3. **Deploy path is simple and dual-sided:**
   - **Our environment** (platform/catalog lab): documented one-liner / Make lever that brings the test env up.  
   - **Client / product side:** same class of simplicity (`project-onboard` → `env-stage` → exercise feature).  
4. The **tests themselves** are part of that deployable surface — not a one-off script that only runs in the author’s shell state.

### Publishing standards for the *development environment we sell*

Because this repo **is** a development environment product:

| Standard | Meaning |
|----------|---------|
| **Simple deploy** | Prefer ≤3 product levers; no 20-knob ritual for a smoke |
| **Reproducible** | Documented command; exit codes; artifact under `pipelines/` when useful |
| **Symmetric** | Client path and our lab path are the same shape |
| **No infinite meta** | New eval harness pieces must themselves pass G0/G1; do not accumulate unshippable test frameworks |

`make env-stage` / `make product-ship` (verify) are the product-facing deploy spine; platform smokes remain advanced but must still be **callable** and **documented**.

## G2 — UX eval stage (human only)

UX is an **eval stage**, not a Make checkbox that agents fake.

### Process

```text
1. Author DoD (one-shot / issue acceptance) including UX acceptance tests (UAT bullets)
2. Implement until G0 + G1 green
3. Deploy test env to UX standard (simple dual-sided deploy)
4. Human runs UAT checklist
5. Failures → UX design issues (not “agent forgot smoke”) → refine DoD + implement → re-G1 → re-UAT
6. Pass → mark UAT passed (issue label / note); only then “user accepted”
```

### Threshold: DoD may not request human testing until deploy is UX-grade

A DoD is **not eligible for G2** until:

- [ ] Deploy is **simple** on our side and client side (product levers or equivalent)  
- [ ] Smokes that gate the feature are on that deploy path  
- [ ] UAT steps are written as **observable human actions** (click/run/see), not “run internal Python module X”  
- [ ] Framework-only work is either productized (docs + Make) or dropped  

If those fail, **keep iterating G1** — do not page a human.

### UAT artifact shape (recommended)

```markdown
## UAT (human)
Environment: [how staged — e.g. make env-stage]
1. [action] → expect [observable]
2. …
Result: pass | fail + notes
```

Store under `pipelines/uat/` or issue comment when run.

## Mapping old “host lab proof” options

| Old option | Mapping |
|------------|---------|
| docs+SKIP only | G0 only — OK for pure docs |
| must green on host | G1 when runtime — smoke on deploy path |
| always human first | **Wrong** — human is G2 after G1 |

## Agent rules (closing issues)

1. **Docs / schema / patterns** → G0 green → close.  
2. **Runtime / smoke / product levers** → G0+G1 → close as **implement done**; open or leave **UAT** checklist if UX-facing.  
3. **Never** claim “user accepted” without G2 note.  
4. New test frameworks → must be **deploy-ready** (documented Make/smoke + simple path) or they fail our own publishing standard.  
5. Prefer extending `eval-structural` / smokes over orphan scripts.

## Make / lanes

| Lane id | Gate | Command |
|---------|------|---------|
| `structural` | G0 | `make eval-structural` |
| `golden_replay` | G0 | `make eval-golden` |
| `deploy_ready` | G1 | `make eval-deploy-ready` (structural + declared smokes) |
| `ux_uat` | G2 | **human** — no agent auto-pass |

## Related issues unblocked by this policy

- Runtime issues may close on G1 without waiting for human.  
- UX polish tracks (#2 voice, product surface) keep explicit UAT steps.  
- Large model labs still need pool policy; G1 = smoke after deploy, G2 = human feel/latency if productized.
