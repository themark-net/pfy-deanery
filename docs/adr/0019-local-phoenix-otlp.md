# ADR-0019: Local Phoenix OTLP for pipeline spans

- **Date:** 2026-11-11
- **Status:** Accepted
- **Deciders:** Phase 2 tracing lane

## Context

Catalog lanes, local builds, and cloud Grok calls need one span tree a later UI can draw (lane nodes, local vs cloud edges, retries). Phoenix on 127.0.0.1:6006 accepts OTLP/HTTP protobuf at `/v1/traces`. The system Python does not have the OpenTelemetry SDK. Traces must not leave the machine, and a down collector must not stall or fail a lane.

ADR-0017 is already cited for the toolset x harness package and is not this decision. ADR-0018 is reserved for the pfy launcher.

## Decision

- Emit with the OpenTelemetry Python SDK and the OTLP/HTTP protobuf exporter. OpenInference attribute names (`openinference.span.kind`, `llm.*`, `tool.name`, `input.value`, `output.value`). Resource `service.name=deanery` and `openinference.project.name=deanery`.
- Install those wheels into `${PFY_TOOL_CACHE:-$HOME/.cache/pfy}/tools/otel/site-py<major><minor>` via `scripts/otel_setup.sh`. Pins live only in that script. `pfylib.otel` imports with the standard library and prepends the cache dir when it exists.
- Default endpoint `http://127.0.0.1:6006/v1/traces`. Refuse any non-loopback endpoint (no-op, one stderr warning). `PFY_OTEL=0` disables tracing. A failed 200ms TCP probe or a missing SDK latches a process-local no-op. Exporter timeout 2s. Exit flush about 1s. Helpers do not raise.
- One redaction function, `pfylib.redact`, shared with `scripts/grok_trace_export.py`.
- LiteLLM uses its built-in `arize_phoenix` callback. Deanery does not write a second exporter.
- Bash lanes use `scripts/otel_span.sh` and `TRACEPARENT`. The wrapper does not change the command's exit status or stdout/stderr.

## Rationale

Rejected alternatives:

1. **Vendor the SDK in the repo** — the pins move, and the repo stays free of wheels. The tool cache is the same place LiteLLM already lives.
2. **Export to a hosted collector** — pipeline prompts and tool args are local operator data. A non-loopback URL is refused so a mis-set env cannot ship them.
3. **OTLP/JSON or a hand-rolled span format** — Phoenix's HTTP ingest on this port accepts `application/x-protobuf`. The SDK exporter already speaks that.
4. **Block the lane until Phoenix accepts the batch** — a down UI collector would stall eval. The probe-and-latch no-op keeps the pipeline independent of the UI.
5. **A second copy of the Grok log redaction patterns** — the two paths would drift and leak. `pfylib.redact` is the single function.

## Consequences

- Operators run `scripts/otel_setup.sh` once per Python version. Tests must not install into `~/.cache/pfy`.
- LiteLLM needs `opentelemetry-sdk` and `opentelemetry-exporter-otlp-proto-http` in its own venv, then a unit restart. See `config/litellm/README.md` and `docs/ops/tracing.md`.
- `deanery.route=unknown` stays unknown. Loopback is the only URL that forces `local`.

## References

- [docs/ops/tracing.md](../ops/tracing.md)
- [docs/ops/local-cloud-split.md](../ops/local-cloud-split.md)
- ADR-0011 (hybrid surfaces)
