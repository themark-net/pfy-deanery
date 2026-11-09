# Eval harness (OQ-0002 option 5 + v0.2)

**Status:** T-0003 MVP + **T-0041 v0.2** + golden validate (#31) + ADR/OQ scorers (T-0075)  
**Decision:** OQ-0002 — **option 5**

| Tier / mode | Meaning | Command |
|-------------|---------|---------|
| **Structural** | Design/coding gates, **no LLM** | `make eval-structural` |
| **Golden** | Golden-task card validate, **no LLM** | `make eval-golden` |
| **Deploy-ready (G1)** | Structural + golden + soft smokes | `make eval-deploy-ready` |
| **UX UAT (G2)** | Human acceptance after simple deploy | human — `pipelines/uat/` |
| **0** | Connectivity smoke | `make eval-tier0` → `smoke-litellm-ollama` |
| **1** | One scored coding task | `make eval-tier1` (`EVAL_TASK`) |
| **MVP** | tier0 + tier1 | `make eval-mvp` |
| **Suite (v0.2)** | All implement tasks, one gate model | `make eval-suite` |
| **Matrix (v0.2)** | Tasks × models | `make eval-matrix` |
| **v0.2 ladder** | tier0 + suite | `make eval-v02` |
| **Later** | DSPy + MCP; LLM golden replay | Deferred |

Gates: [eval-gates-and-ux-uat.md](../../docs/ops/eval-gates-and-ux-uat.md) (HD #33). Lanes schema: [`data/eval-lanes.json`](../../data/eval-lanes.json) · [design-coding-assist-rubric.md](../../docs/evaluation/design-coding-assist-rubric.md) · [local-model-storage-and-eval.md](../../docs/ops/local-model-storage-and-eval.md)

## Tasks

| ID | Type | What |
|----|------|------|
| `001-is-palindrome` | implement | `is_palindrome(s)` exact reverse, case-sensitive |
| `002-fix-sum-evens` | fix | Correct bug: sum **even** numbers, not odds |
| `003-exit-card-checklist` | text/checklist | Eight-exit card keywords (T-0060) |
| `004-investigate-report` | text | Investigate report shape |
| `005-one-shot-dod` | text | One-shot DoD checklist |
| `006-adr-shape` | text | Multi-file ADR shape (T-0075) |
| `007-oq-shape` | text | OQ detail file shape (T-0075) |

Hidden tests score **pass/fail**. Path: LiteLLM → host Ollama (same as litellm smoke).

## Golden tasks

Cards live in [`data/golden-tasks/`](../../data/golden-tasks/). Deterministic validate:

```bash
make eval-golden                 # validate + pipelines/eval/golden.latest.md
# also run from eval-structural (golden_tasks check)
```

## Models

| Knob | Default | Role |
|------|---------|------|
| `LITELLM_SMOKE_MODEL` | `deepseek-coder:latest` | Tier-0 connectivity only (tiny OK) |
| `EVAL_MODEL` / `EVAL_GATE_MODEL` | from **fit selection** or `qwen2.5:14b` | Must pass for suite/matrix exit 0 |
| `EVAL_MODELS` | fit selection or pins.env list | Matrix columns; missing → **SKIP** cell |
| `MODEL_POOL_MAX_GB` (policy) | 250 | See local-model-storage-and-eval.md |

**Fit selection (preferred):** does **not** limit to already-pulled models. Ranks a curated coding catalog by quality subject to **RAM + disk budgets**, then optionally `ollama pull`s the gate.

```bash
make eval-select-models          # report + exports; pulls gate if needed
make eval-auto                   # structural + select + pull-gate + eval-v02
EVAL_PULL_GATE=0 make eval-select-models
```

Script: `select_ollama_models.py` · env `EVAL_RAM_BUDGET_GB`, `EVAL_DISK_BUDGET_GB`, `EVAL_ALLOW_PULL=0`.

## Run

```bash
export PATH="$HOME/.local/bin:$PATH"
./examples/litellm-ollama/host-ollama-gateway.sh start

make eval-structural          # no LLM (includes golden validate)
make eval-golden              # golden cards only
make smoke-litellm-ollama     # tier0 path
make eval-auto                # fit models + pull gate + eval-v02
```

## Layout

```
examples/eval-harness/
  README.md
  run_structural.py / run_golden.py / validate_golden_tasks.py
  run_scored_task.py / run_suite.py
  tasks/001-… / 006-adr-shape / 007-oq-shape
data/golden-tasks/
pipelines/eval/
  structural.latest.md / golden.latest.md / results.latest.md
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Pass |
| 1 | Fail (score or tool error) |
| 2 | Skip (e.g. gate model missing on Ollama) |

## Non-goals

- DSPy optimizers  
- Cloud-required scoring (local Ollama only)  
- Auto catalog write into `TOOLS.md` (manual re-score still)  
- Full LLM multi-agent golden replay (queued after deterministic cards)  
