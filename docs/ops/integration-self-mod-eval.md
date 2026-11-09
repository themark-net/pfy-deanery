# Integration self-mod eval (Exo-inspired)

**Purpose:** Before we treat a catalog/skill/smoke change as “ingested,” run a **self-change evaluation loop** — the portable part of Exo’s §8 without full RSI.

**When to run:** after adding a tool, skill pack, Make target, or eval lane; or when an agent proposes self-mod of process docs/skills.

## Rubric (pass = all hard gates green)

| ID | Gate | Hard? | Command / check |
|----|------|:-----:|-----------------|
| **S0** | Intent recorded | soft | reason string in receipt |
| **S1** | Structural G0 | **hard** | `run_structural.py` |
| **S2** | Golden cards | **hard** | `run_golden.py` / validate |
| **S3** | Catalog schema | **hard** | tools.json + `integration_stage` |
| **S4** | Triple-write S-tier | soft* | S-tier names in TOOLS.md |
| **S5** | Smoke contract | soft | known examples have smoke/run-in-cage |
| **S6** | Size / stage policy | **hard** | no I4 without ADR; no weights; skill body warnings |
| **S7** | Paths pack integrity | soft | if skills-external changed, SKILL.md count/shape |
| **S8** | Diff blast radius | soft | changed path classes labeled |

\*S4 hard if any **new S-tier** tool added.

### Outcome labels (Exo-style adopt/rollback)

| Label | Meaning |
|-------|---------|
| **adopt** | All hard gates pass; soft notes optional |
| **hold** | Soft failures only — usable but needs follow-up issue |
| **rollback** | Any hard gate fail — do not merge/promote |

Receipt: `pipelines/eval/integration-change.latest.md` (+ JSON).

## Agent protocol (named tools, auditable)

Mirrors Exo mutation principles:

1. **Propose** — state reason (what integration, why).  
2. **Snapshot** — work on a branch / list files to touch.  
3. **Mutate** — only catalog, skills-external, examples smokes, docs/ops (not sealed kernel without ADR).  
4. **Evaluate** — `make eval-integration-change`.  
5. **Adopt or rollback** — commit only on adopt/hold; hard fail → restore.  
6. **Remember** — leave receipt under `pipelines/eval/`; optional golden card for high-signal.

### Sealed (do not self-mod without ADR)

- ADR-0002 Grok primary  
- agent-cage as primary lab (not replace with Exo)  
- write-guard defaults  
- no weights in git  

## Relation to G0/G1/G2

| Gate | Maps to |
|------|---------|
| S1–S2 | **G0** structural |
| smoke soft | **G1** deploy-ready (partial) |
| human UX | **G2** unchanged — still human UAT |

## CLI

`./pfy eval` runs this target and writes `pipelines/eval`. It does not call Grok and does not push `main`. Catalog verdicts are `scripts/eval_lane.sh`.

```bash
# evaluate current tree (default). Same gate as ./pfy eval.
make eval-integration-change

# attach a reason for the receipt
REASON="ingest exo patterns" make eval-integration-change
```
