# Local traces

Pipeline steps emit OpenTelemetry spans to a Phoenix on this machine. A later UI can draw lanes as nodes and tag edges local or cloud. Spans are optional. A missing SDK, a closed port, or `PFY_OTEL=0` leaves the pipeline running.

ADR-0019. Phoenix itself is a separate service. This page is only the client.

## What is traced

| Step | Span | Route |
|------|------|-------|
| Catalog loop tick | `catalog-loop` (CHAIN), plus a short `lane.launch` child per lane | local |
| Eval / integrate lane | `eval-<slug>` / `integrate-<slug>` (CHAIN) | cloud |
| Grok inside those lanes | AGENT span, then child TOOL / file / reasoning spans from the lane log when the log exists | cloud, provider `xai` |
| Catalog-fit Ollama call | CHAIN per slug, LLM child | local, provider `ollama` |
| Local build review and OpenCode | LLM | from the base URL (loopback is local) |
| `./pfy bot` opencode / hermes | LLM | from the base URL |
| Cloud build `grok_call` | AGENT | cloud, provider `xai` |
| LiteLLM proxy | LiteLLM's own `arize_phoenix` callback, not a Deanery exporter | `llm.provider` on those spans |

Not traced here: the sandboxed review poster process (the parent span covers that call), model-lock internals, and any log under `~/.grok`. Ingest reads only the lane's own log file and skips it when the file is absent.

## Attribute contract

Every Deanery span sets these. Empty string means "not known". `deanery.route` is `local`, `cloud`, or `unknown` (never a guess).

| Key | Meaning |
|-----|---------|
| `deanery.job_id` | Tick id or lane job |
| `deanery.lane_id` | `catalog-loop`, `eval-<slug>`, `integrate-<slug>`, `catalog-fit-<slug>`, `build-cloud` |
| `deanery.parent_lane` | Lane that started this one |
| `deanery.task_class` | `catalog-loop`, `eval`, `integrate`, `catalog-fit`, `build` |
| `deanery.route` | `local`, `cloud`, or `unknown` |
| `deanery.iteration` | Loop or retry count, integer |
| `openinference.span.kind` | `CHAIN`, `LLM`, `TOOL`, or `AGENT` |
| `openinference.project.name` | Resource attribute `deanery` (the Phoenix project) |
| `service.name` | Resource attribute `deanery` |
| `deanery.host` | Resource attribute, hostname |
| `llm.model_name` | Set when a model is known |
| `llm.provider` | `ollama`, `xai`, or the provider the call site passed |
| `llm.token_count.prompt` / `.completion` / `.total` | When the response includes counts |
| `tool.name` | Tool or file op |
| `deanery.mcp` | `true` on an MCP tool span, with `deanery.mcp.server` and `deanery.mcp.tool` |
| `deanery.file.path` / `deanery.file.op` | Path and op only. Never file contents |
| `input.value` / `output.value` | Short redacted summaries, not raw prompts or tool output |
| `llm.output_messages.0.message.contents.0.message_content.type` | `reasoning` on a reasoning span, with `.text` holding the short summary |

`TRACEPARENT` is the W3C parent. `child_env()` and `scripts/otel_span.sh` copy it onto the child. Bash emits with `python3 -m pfylib.otel emit`. `python3 -m pfylib.otel traceparent` prints a new parent line.

Route rule: provider `ollama`, `llama.cpp`, `vllm`, and the other local runners in `route_for` are local. `xai`, `grok`, `openai`, `anthropic`, `openrouter`, and the other hosted names are cloud. A loopback base URL is local even when the provider name is a cloud vendor. Anything else is `unknown`.

## Redaction

Every string attribute and event field goes through `pfylib.redact.redact` (the same patterns as `scripts/grok_trace_export.py`). That covers PEM private keys, `xai-` / `sk-` / `ghp_` / `github_pat_` / `AKIA` tokens, Slack-style `xox`, JWTs, `Bearer` headers, URL userinfo, token query parameters, and `KEY=VALUE` when the key is a whole component (`TOKEN`, `SECRET`, `KEY`, `PASSWORD`, `AUTH`, `COOKIE`, `BEARER`, `API_KEY`). A long high-entropy blob is masked. Values are clipped (2000 characters, 500 on `input.value` / `output.value`). Attribute names that look secret-bearing are dropped, except `llm.token_count.*` and `gen_ai.usage.*`. `file_op` drops content, body, diff, and patch fields.

## Off switch and setup

```bash
export PFY_OTEL=0          # no spans, no probe
# default endpoint, loopback only:
export PFY_OTEL_ENDPOINT=http://127.0.0.1:6006/v1/traces
```

A non-loopback endpoint is refused: one stderr line, then a no-op for the process. The first use probes TCP for at most 200ms. Failure latches off. Export uses a batch processor, a 2s exporter timeout, and about 1s of flush at process exit. Public helpers swallow their own errors.

Deps live in the tool cache, not the repo. Pins are only in `scripts/otel_setup.sh`:

```bash
PFY_TOOL_CACHE="${PFY_TOOL_CACHE:-$HOME/.cache/pfy}" ./scripts/otel_setup.sh
```

That installs `opentelemetry-sdk==1.45.2`, `opentelemetry-exporter-otlp-proto-http==1.45.2`, and `openinference-semantic-conventions==0.1.44` for the current Python. LiteLLM's callback needs the SDK and the HTTP exporter in the LiteLLM venv. See [config/litellm/README.md](../../config/litellm/README.md). Restart that unit yourself after installing them.

## Local-only

Phoenix stays on 127.0.0.1. This client will not export to any other host. Do not point `PFY_OTEL_ENDPOINT` or `PHOENIX_COLLECTOR_HTTP_ENDPOINT` at a remote collector.
