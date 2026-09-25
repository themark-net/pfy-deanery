# Product operator surface (end-user simplicity)

**Status:** Implemented 2026-07-30 (T-0090 MVP) · help split 2026-09-25 · local runtime pluggable 2026-08-24 (ADR-0014 / T-0110)  
**Related:** ADR-0011 · ADR-0014 · [local-cloud-split.md](local-cloud-split.md) · TODO **T-0090** done

## Two audiences

| Audience | Goal | OK complexity |
|----------|------|----------------|
| **End user / product team** | Build *their* product with LLM toolsets | **3 levers** |
| **Platform builders (us)** | Catalog, cage, eval, skills, MCP | Many Make targets OK for now |

MVP iteration may expose many targets. **Ship shape** collapses to the product loop below.

## Absolute minimum levers (target)

**Canonical CLI (G8 / ADR-0012):** `./pfy` — setup · status · start · harness · stage · ship · eval.



```text
1. onboard   — attach this stack to a project (process + skills + profile)
2. stage     — bring up local env (pluggable local runtime + optional cage) green
3. ship      — verify + push product code (not platform code)
```

Suggested final names (implementation: T-0090):

| Lever | Make (eventual) | Does |
|-------|-----------------|------|
| onboard | `make project-onboard DIR=…` | `scripts/product-onboard.sh` — project-process init + `.env` example |
| stage | `make env-stage` | `scripts/env-stage.sh` — env-check + eval-structural; local runtime soft |
| ship | `make product-ship` | structural + golden; push if `PRODUCT_REMOTE` set |

Everything else is **platform development** (`make help-platform`) and stays off the default `make help`.

## Local bulk vs cloud monitor (target behavior)

```text
Worker (local OpenAI-compat coder — llama-swap / llama-server / Shimmy / Ollama)
  → implements, runs tests, cheap loops
Monitor (Grok subscription / strong cloud)
  → sets DoD/exit card, reviews, escalates when worker stuck
```

**Today (honest):**

Loop paints this split: **LOCAL COMPUTE** (engine/status/endpoint ON when a runtime answers) vs **CLOUD ORCHESTRATION** (budget/spent/left; STANDBY vs SPENDING). Task class `bulk` / `interactive` / `hard` is the hedge input. Launch session is the proof.

| Path | Uses local coder (e.g. `deepseek-coder:6.7b`)? |
|------|-----------------------------------------------|
| `make eval-suite` / `eval-auto` | **Yes** (when selected as gate) |
| `make smoke-litellm-ollama` | Yes (Ollama adapter smoke) |
| Grok Build interactive agent | **No** — Grok cloud/subscription (**monitor**) |
| OpenCode pointed at `LOCAL_OPENAI_BASE_URL` | **Yes** if configured (T-0080) |
| Dual session worker/monitor | **`make worker-stage`** + `/worker-monitor` (T-0085) — not a single daemon |
| Voice → same agents (p1) | **`make smoke-voice-stt`** + `examples/voice-stt-edge/` (T-0091) — STT edge, not mobile-voice-stuck |

Pick runtime: `./scripts/detect-local-runtime.sh` / `./pfy status` (ADR-0014). No new product CLI.

## Redeployable workflow (unchanged north star)

1. **Catalog** tools/skills (rubric / lanes)  
2. **Port patterns** into first-party skills + smokes  
3. **Prove** with `eval-structural` + local suite  
4. **Operate** product via minimal levers  
5. **Sync** platform itself with `cage-code-sync` (builders only)

## Makefile complexity budget (T-0090)

| Allowed on product surface | Belongs in platform/docs only |
|----------------------------|-------------------------------|
| onboard / stage / ship | cage-*, smoke-*, eval-*, sync internals |
| `DEPLOY_PROFILE` | 20+ EVAL_* knobs |
| One local model default from `eval-select-models` | Full matrix debugging |

Audit checkpoint (2026-09-25): default `make help` lists three product Make targets (`project-onboard`, `env-stage`, `product-ship`). Cage, smoke, and eval are on `make help-platform`.

## Related TODOs

- **T-0110** — Pluggable local runtime (doing/partial) · [#76](https://github.com/themark-net/pfy-mentat/issues/76)  
- **T-0101** — Ollama adapter complete (kept)  
- **T-0085** — Worker/monitor split: local worker, Grok monitor recipe  
- **T-0080** — OpenCode host smoke (required for real offload)  
- **T-0090** — Collapse product surface; audit Make levers  

## Implemented targets (2026-07-30)

Public product surface:

| Lever | CLI | Make |
|-------|-----|------|
| setup / onboard | `./pfy setup` | `project-onboard` / env-init |
| status | `./pfy status` | — |
| start | `./pfy start` | harness-specific |
| stage | `./pfy stage` | `env-stage` |
| ship | `./pfy ship` | `product-ship` |
| eval | `./pfy eval` | `eval-integration-change` |

Platform remains on `make help-platform`. Harness registry: `data/harnesses.json`.


## Eval gates (product relevance)

| Lever | Typical gate |
|-------|----------------|
| onboard / stage | G1 when changing deploy spine |
| ship (verify) | G0+G1 before claiming ready |
| User “it feels right” | **G2 UAT** — human, after simple deploy |

See [eval-gates-and-ux-uat.md](eval-gates-and-ux-uat.md).
