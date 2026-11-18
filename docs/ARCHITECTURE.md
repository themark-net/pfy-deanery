# Architecture snapshot

**Last updated:** 2026-08-24
**Design authority:** [DESIGN.md](DESIGN.md)
**Decision authority:** [adr/](adr/README.md)

Keep this file short. If layering or boundaries change, accept an ADR and update both this snapshot and DESIGN §4.

## Purpose

Catalog + integration track for local-first LLM tooling. The product door is `./pfy` (G8 / [ADR-0012](adr/0012-simple-harness-agnostic-launch.md)). Local inference is pluggable per **[ADR-0014](adr/0014-pluggable-local-inference-spine.md)** (supersedes ADR-0011 as the inference fabric). Grok is the monitor harness; the local worker is OpenAI-compat.

## Product loop

`setup` → `start` / `up` (= inference + env-stage + active harness) → `stage` → `ship`.

Bare `./pfy start` and `./pfy up` bring up the operator env, not just the engine. Missing grok: print install/login, try the next ready adapter. Stubs stay honest (exit 2 + issue pointer).

## Local inference (ADR-0014)

Detect order (first live wins):

1. **FreeToken** (spine)
2. **llama-swap :9292**
3. **llama-server :8080**
4. **Ollama** (adapter, not deleted)

Shimmy is optional last, not the free-forever candidate. Honest missing/partial. Engines not vendored.

## Data flow (delivered)

```text
sources (X / aggregates / papers)
    → scoring (CATEGORIZATION rubric)
    → TOOLS.md + data/tools.json
    → bootstrap/grok-cli (skills SoT) + bootstrap/opencode (adapter)
    → ./pfy: inference (ADR-0014) → env-stage → active harness (default grok)
```

## Layout map

| Area | Path | Notes |
|------|------|--------|
| Process | `docs/` | Design, ADR, TODO, OQ |
| Catalog | `TOOLS.md`, `data/`, `sources/` | Source of truth for scores |
| Bootstrap Grok | `bootstrap/grok-cli/` | Skills SoT + MCP + config merge |
| Bootstrap OpenCode | `bootstrap/opencode/` | Thin adapter; no forked skills |
| **Simple launch** | `./pfy`, `data/harnesses.json` | G8 / ADR-0012 operator surface |
| Local runtime | `scripts/detect-local-runtime.sh` | ADR-0014 detect |
| Inference recipes | `config/litellm/`, `examples/litellm-ollama/` | Profile routers + cage smoke |
| Harness | `harness/agent-cage/` | Lab + Grok-in-cage |
| Eval | `examples/eval-harness/`, `pipelines/eval/` | Structural + implement lanes |

## Delivered vs not

| Delivered | Not yet |
|-----------|---------|
| Methodology + catalog + Grok bootstrap | Honest harness stubs T-0103-T-0109 |
| LiteLLM profiles + Ollama cage smoke | Ollama adapter complete (T-0101 health/default model) |
| Process docs + structural eval | Automated dashboard from JSON |
| ADR-0014 spine + `./pfy` start/up operator env | Default always-on LiteLLM daemon |
| `./pfy` MVP + harness registry + OpenCode host adapter | OpenCode-in-cage parity (T-0081) |
| Leftover harness ids honest-stub (`./pfy start` exit 2) | Remaining adapter implementations |

## Extension points

- New tool → score → `TOOLS.md` + `data/tools.json` + source log
- New integration package → under `bootstrap/` or `pipelines/` with ADR if it changes stack defaults
- New process rule → ADR + update DESIGN/AGENTS.md

## Forbidden without ADR

- Second parallel decision log outside `docs/adr/`
- Embedding large upstream histories without meeting `SUBTREES.md`
- Putting secrets in catalog or docs
