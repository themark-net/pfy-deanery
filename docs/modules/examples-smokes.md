# Module: examples/ + pipelines/smoke/

**Purpose:** **Idempotent in-cage integration smokes** for catalog tools. Host checks alone do not prove isolation.

## Operator: how to run

Cage agent must be running (`make cage-up-mcp` or `make local-ollama-up`).

| Target | What it proves |
|--------|----------------|
| `make smoke-write-guard` | write-guard policy audit/enforce |
| `make smoke-codebase-memory` | codebase-memory-mcp index + search |
| `make smoke-repowise` | repowise health (zero LLM) |
| `make smoke-context-tools` | both context tools + compare note |
| `make smoke-kolibri1` | Kolibri-1 EN/DE/tool-call via patched llama.cpp or any OpenAI-compatible URL; FAILs without backend (Entry 085) |
| `make smoke-litellm-ollama` | LiteLLM → host Ollama via gateway :11435 |
| `make smoke-opencode-ollama` | Host OpenCode + Ollama worker (T-0080) |
| `make smoke-voice-stt` | Host STT edge → Grok/OpenCode handoff (T-0091 p1; no mic) |
| `make eval-tier0` / `eval-tier1` / `eval-mvp` | OQ-0002 opt5: connectivity + scored coding task. tier1 resolves eval-suite with `--probe-tags` (no pull). A local 404 on the committed default retries the fallback once |
| `make eval-suite` / `eval-matrix` / `eval-v02` | T-0041: multi-task suite + multi-model matrix. A public base quotes the sum and does not open a socket until the same yes rules pass |

| Layout | Role |
|--------|------|
| `examples/<tool>/` | README, pins.env, run-in-cage.sh, fixtures |
| `pipelines/smoke/<tool>/` | Short pointer + results.latest.md |
| `pipelines/smoke/context-tools-compare.md` | T-0013 complement note |

One-shot paste DoDs: [docs/ops/one-shot-example-dods.md](../ops/one-shot-example-dods.md)

## Where variables live

| Variable | Smoke |
|----------|--------|
| `LITELLM_SMOKE_MODEL` | litellm-ollama (default `deepseek-coder:latest`) |
| `REPOWISE_PIP_SPEC` | repowise (default `repowise==0.30.0`) |
| `OLLAMA_GATEWAY_PORT` | host gateway (default `11435`) |
| `WRITE_GUARD_*` | write-guard |
| `VOICE_STT_*` / `OPENAI_API_KEY` | voice-stt-edge (optional real Whisper) |

## Agent map

| Concern | Detail |
|---------|--------|
| **Invariants** | Exit 0 pass, 1 fail; prefer cage; pin deps (ADR-0003) |
| **Do not** | Claim integration green from host-only pip install |
| **Framework** | [harness-integration-framework.md](../ops/harness-integration-framework.md) |

## Verify

```bash
make smoke-write-guard
make smoke-context-tools
# optional if Ollama up:
./examples/litellm-ollama/host-ollama-gateway.sh start && make smoke-litellm-ollama
```
