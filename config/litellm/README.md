# LiteLLM configs by DEPLOY_PROFILE (T-0012)

| Profile | File | Intent |
|---------|------|--------|
| `local-only` | [local-only.yaml](local-only.yaml) | Ollama only; no cloud keys |
| `balanced` | [balanced.yaml](balanced.yaml) | Local bulk + cloud for hard tasks |
| `max-performance` | [max-performance.yaml](max-performance.yaml) | Cloud-first; local fallback |

## Env vars

| Variable | Profiles | Example |
|----------|----------|---------|
| `DEPLOY_PROFILE` | all | `balanced` |
| `LITELLM_CONFIG` | all | `config/litellm/balanced.yaml` |
| `OLLAMA_API_BASE` | local / balanced / max fallback | Host: `http://127.0.0.1:11434` · Cage: `http://host.docker.internal:11435` |
| `OLLAMA_HOST` | docs / older clients | Same host as Ollama HTTP (no `/v1`) |
| `LITELLM_CLOUD_MODEL` | balanced, max | `xai/grok-3` (override if your LiteLLM/xAI ID differs) |
| `XAI_API_KEY` | balanced, max | From console; not required if only using local aliases |
| `LITELLM_MASTER_KEY` | optional proxy | Only if exposing a shared LiteLLM proxy |
| `LITELLM_SMOKE_MODEL` | cage smoke | `deepseek-coder:latest` (local OpenAI-compat path) |
| `PHOENIX_COLLECTOR_HTTP_ENDPOINT` | all | `http://127.0.0.1:6006/v1/traces` (local Phoenix only) |
| `PHOENIX_PROJECT_NAME` | all | `deanery` |

`litellm_settings.callbacks` is `["arize_phoenix"]` (LiteLLM 1.108.3's built-in callback; this repo does not ship its own exporter). The callback reads `PHOENIX_COLLECTOR_HTTP_ENDPOINT` as the OTLP/HTTP URL when that value already contains `/v1/traces`. `PHOENIX_API_KEY` is not required for a loopback collector. `PHOENIX_COLLECTOR_ENDPOINT` is the gRPC alternative and is unused here.

The LiteLLM venv at `~/.cache/pfy/tools/litellm/venv` has `opentelemetry-api` only. The operator installs these into that venv before the callback can export (do not install them from a test run):

```bash
# into the LiteLLM venv, matching the API pin already there
opentelemetry-sdk==1.45.2
opentelemetry-exporter-otlp-proto-http==1.45.2
```

LiteLLM's import error names `opentelemetry-exporter-otlp`. The module it imports is `opentelemetry.exporter.otlp.proto.http.trace_exporter`. Restart the LiteLLM unit after the config and packages change so the process reloads the callback. This repo does not restart it. Route (local vs cloud) is read later from `llm.provider` on the spans LiteLLM emits.

Copy non-secrets from `config/profiles/<name>.env`; put secrets only in root `.env` (gitignored).

## Quick use

```bash
# local-only (cage smoke path — proven)
export DEPLOY_PROFILE=local-only
export OLLAMA_API_BASE=http://127.0.0.1:11434
# litellm --config config/litellm/local-only.yaml   # if using proxy CLI

# balanced
export DEPLOY_PROFILE=balanced
export LITELLM_CONFIG=config/litellm/balanced.yaml
export OLLAMA_API_BASE=http://127.0.0.1:11434
export LITELLM_CLOUD_MODEL=xai/grok-3
# XAI_API_KEY in .env

# max-performance
export DEPLOY_PROFILE=max-performance
export LITELLM_CONFIG=config/litellm/max-performance.yaml
export LITELLM_CLOUD_MODEL=xai/grok-3
# XAI_API_KEY in .env; OLLAMA optional for fallbacks
```

## Model aliases

| Alias | Role |
|-------|------|
| `local-coder` / `local-default` | Cheap / coding via Ollama |
| `cloud-hard` / `cloud-default` | Strong cloud model (xAI by default) |

In-cage completion smoke still exercises **local** path only (no cloud key required):  
`make smoke-litellm-ollama` — see [examples/litellm-ollama/](../../examples/litellm-ollama/).

## Design notes

- Secrets never in YAML files committed to git; use `os.environ/...` LiteLLM syntax.
- Cage needs host Ollama gateway + policy — [overlays/local-ollama](../../harness/agent-cage/overlays/local-ollama/).
- Profiles: [docs/ops/deployment-profiles.md](../../docs/ops/deployment-profiles.md) · ADR-0006.
