# Design & coding assist evaluation (schema extension)

**Status:** Proposed extension to [evaluation-framework.md](../evaluation-framework.md) v1.3  
**Why:** Standard S1-S4 and company C1-C6 miss **process skills** and **structural evals** that assist design/coding without being “tools to install.”

## Problem

| Artifact | Fit of S1-S4 alone |
|----------|-------------------|
| `/agent-loops`, `/investigate`, `/one-shot` | High relevance; “integration” is skill install, not binary smoke |
| Exit-card / DoD quality | Needs **deterministic text scorer**, not only model implement tasks |
| Pattern extracts (Auto-Company, Finn) | Docs-only; S2/S3 inflate poorly |

## Extension: evaluation lanes

| Lane | ID | Requires LLM? | Pass command | What it proves |
|------|-----|---------------|--------------|----------------|
| **Structural** | `S` | **No** | `make eval-structural` | Skills on disk, tools.json schema, text-scorer fixtures |
| **Implement** | `I` | Yes (local) | `make eval-tier1` / `eval-suite` | Model produces code that passes hidden tests |
| **Connectivity** | `C` | Backend only | `make eval-tier0` | LiteLLM→Ollama path alive |
| **Company** | `Co` | Optional | Company rubric | Multi-agent org (existing) |
| **Standard tool** | `T` | Optional | S1-S4 + smoke | Catalog tool (existing) |

## Schema addition (demonstrated)

`data/eval-lanes.json` (versioned inventory of automated gates):

```json
{
  "version": "1.0",
  "lanes": [
    {
      "id": "structural",
      "requires_llm": false,
      "command": "make eval-structural",
      "artifacts": ["pipelines/eval/structural.latest.md"]
    }
  ]
}
```

Optional per-task field under `examples/eval-harness/tasks/<id>/meta.json`:

```json
{
  "task_id": "003-exit-card-checklist",
  "lane": "structural",
  "kind": "text_scorer",
  "assist_domain": ["design", "coding", "loops"]
}
```

**Rejected alternative:** Force every skill through S1-S4 tool scores - collapses process quality into “integration ease” and hides structural regression.

## Design/coding assist priority (what we implement)

1. First-party skills: loops, RCA, one-shot, ADR, docs, OQ, hermes-feedback  
2. Structural eval always green in CI/agent loops  
3. Implement-lane eval when Ollama gate model present (SKIP not FAIL if missing - exit 2)  
4. Catalog tools that **assist** coding (CM, repowise, write-guard, Bumblebee) only after structural green  

## Human decisions

See [human-decision-inventory.md](../ops/human-decision-inventory.md) - branch maps + pending count for automation loops.

## Gates G0-G2 (HD #33)

| Gate | Lane | Agent close? |
|------|------|--------------|
| G0 | structural, golden | yes (docs/schema) |
| G1 | deploy_ready (+ connectivity/implement when relevant) | yes (implement-done) |
| G2 | ux_uat | **human only** |

Full policy: [ops/eval-gates-and-ux-uat.md](../ops/eval-gates-and-ux-uat.md).
