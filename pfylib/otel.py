"""Local Phoenix spans for the Deanery pipeline.

Importing this module needs only the standard library. The OpenTelemetry SDK
is loaded on first use from the tool cache (scripts/otel_setup.sh). If the
SDK is missing, Phoenix is down, or the endpoint is not loopback, every
public function stays a no-op. Tracing never raises into the caller.

A user exception raised inside span() still propagates.
"""

from __future__ import annotations

import atexit
import contextlib
import contextvars
import importlib.util
import ipaddress
import json
import os
import secrets
import socket
import sys
import threading
import time
import urllib.parse
from pathlib import Path

from pfylib.redact import redact, secret_attr_key

DEFAULT_ENDPOINT = "http://127.0.0.1:6006/v1/traces"
_VALUE_LIMIT = 2000
_SHORT_LIMIT = 500
_KINDS = {"CHAIN", "LLM", "TOOL", "AGENT"}
_ROUTES = {"local", "cloud", "unknown"}
_LOCAL_PROVIDERS = {
    "ollama",
    "llama.cpp",
    "llama-cpp",
    "llamacpp",
    "vllm",
    "llama-server",
    "llamaserver",
    "freetoken",
    "shimmy",
    "llama-swap",
}
_CLOUD_PROVIDERS = {
    "xai",
    "grok",
    "openai",
    "anthropic",
    "openrouter",
    "claude",
    "gemini",
    "google",
    "azure",
    "mistral",
    "groq",
    "together",
    "fireworks",
    "deepseek",
}
_CONTENT_KEYS = {
    "content",
    "contents",
    "body",
    "data",
    "text",
    "diff",
    "patch",
    "input",
    "output",
    "input.value",
    "output.value",
}
_FILE_OPS = {
    "read_file": "read",
    "read": "read",
    "write": "write",
    "write_file": "write",
    "search_replace": "edit",
    "strreplace": "edit",
    "edit": "edit",
    "edit_file": "edit",
    "apply_patch": "edit",
    "delete_file": "delete",
    "delete": "delete",
}
_SHORT_KEYS = {
    "input.value",
    "output.value",
    "llm.output_messages.0.message.contents.0.message_content.text",
}

_mode = "unknown"  # unknown | off | live
_warned = False
_processor = None
_provider = None
_tracer = None
_resource = None
_endpoint = DEFAULT_ENDPOINT
_attached = None
_sdk = None


class _Bound:
    __slots__ = (
        "job_id",
        "lane_id",
        "parent_lane",
        "task_class",
        "route",
        "iteration",
        "model",
        "provider",
    )

    def __init__(self) -> None:
        self.job_id = None
        self.lane_id = None
        self.parent_lane = None
        self.task_class = None
        self.route = None
        self.iteration = None
        self.model = None
        self.provider = None


_bound_var: contextvars.ContextVar[_Bound | None] = contextvars.ContextVar(
    "deanery_otel_bound", default=None
)
_stack_var: contextvars.ContextVar[tuple] = contextvars.ContextVar(
    "deanery_otel_stack", default=()
)


def _site_dir() -> Path | None:
    cache = os.environ.get("PFY_TOOL_CACHE") or str(Path.home() / ".cache" / "pfy")
    version = "%d%d" % (sys.version_info[0], sys.version_info[1])
    path = Path(cache) / "tools" / "otel" / ("site-py" + version)
    if path.is_dir() and (path / "opentelemetry").is_dir():
        return path
    return None


def _loopback_host(host: str) -> bool:
    name = (host or "").strip().strip("[]").lower()
    if name == "localhost":
        return True
    try:
        return ipaddress.ip_address(name).is_loopback
    except ValueError:
        return False


def _split_endpoint(url: str) -> tuple[str, int] | None:
    raw = (url or "").strip()
    if "://" not in raw:
        raw = "http://" + raw
    parsed = urllib.parse.urlparse(raw)
    if parsed.scheme not in ("http", "https"):
        return None
    host = parsed.hostname or ""
    if not host or not _loopback_host(host):
        return None
    if parsed.port is not None:
        port = parsed.port
    else:
        port = 443 if parsed.scheme == "https" else 80
    return host, port


def _probe(host: str, port: int) -> bool:
    try:
        sock = socket.create_connection((host, port), 0.2)
    except OSError:
        return False
    try:
        sock.close()
    except OSError:
        pass
    return True


def _warn_once(url: str) -> None:
    global _warned
    if _warned:
        return
    _warned = True
    try:
        shown = redact(url, limit=200)
    except Exception:
        shown = "[endpoint]"
    try:
        sys.stderr.write("otel: refusing non-loopback endpoint %s\n" % shown)
    except Exception:
        return


def _silence_loggers() -> None:
    import logging

    for name in (
        "opentelemetry",
        "opentelemetry.sdk",
        "opentelemetry.sdk.trace",
        "opentelemetry.sdk.trace.export",
        "opentelemetry.exporter",
        "opentelemetry.exporter.otlp",
        "opentelemetry.exporter.otlp.proto.http",
        "opentelemetry.exporter.otlp.proto.http.trace_exporter",
    ):
        logging.getLogger(name).setLevel(logging.CRITICAL)


def _install_sdk(site: Path, endpoint: str) -> bool:
    global _processor, _provider, _tracer, _resource, _sdk, _attached
    path = str(site)
    if path not in sys.path:
        sys.path.insert(0, path)
    _silence_loggers()
    from opentelemetry import context as otel_context
    from opentelemetry import trace as trace_api
    from opentelemetry.exporter.otlp.proto.http import Compression
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

    resource = Resource.create(
        {
            "service.name": "deanery",
            "openinference.project.name": "deanery",
            "deanery.host": socket.gethostname(),
        }
    )
    exporter = OTLPSpanExporter(endpoint=endpoint, timeout=2, compression=Compression.NoCompression)
    processor = BatchSpanProcessor(
        exporter,
        schedule_delay_millis=200,
        export_timeout_millis=2000,
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(processor)
    trace_api.set_tracer_provider(provider)
    _processor = processor
    _provider = provider
    _tracer = provider.get_tracer("deanery.otel")
    _resource = resource
    _sdk = {
        "trace": trace_api,
        "context": otel_context,
        "propagator": TraceContextTextMapPropagator(),
    }
    parent = os.environ.get("TRACEPARENT") or ""
    if parent.strip():
        extracted = _sdk["propagator"].extract({"traceparent": parent.strip()})
        _attached = otel_context.attach(extracted)
    return True


def ensure() -> bool:
    """Turn tracing on, or latch a permanent no-op. Never raises."""
    global _mode, _endpoint
    if _mode == "live":
        return True
    if _mode == "off":
        return False
    try:
        if os.environ.get("PFY_OTEL", "") == "0":
            _mode = "off"
            return False
        endpoint = (os.environ.get("PFY_OTEL_ENDPOINT") or DEFAULT_ENDPOINT).strip()
        _endpoint = endpoint
        target = _split_endpoint(endpoint)
        if target is None:
            _warn_once(endpoint)
            _mode = "off"
            return False
        site = _site_dir()
        if site is None:
            _mode = "off"
            return False
        if not _probe(target[0], target[1]):
            _mode = "off"
            return False
        if not _install_sdk(site, endpoint):
            _mode = "off"
            return False
        _mode = "live"
        return True
    except Exception:
        _mode = "off"
        return False


def _content_key(key: str) -> bool:
    name = (key or "").lower()
    if name in _CONTENT_KEYS:
        return True
    tail = name.rsplit(".", 1)[-1]
    return tail in {"content", "contents", "body", "diff", "patch"}


def _coerce(key: str, value):
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
        return value
    if key == "deanery.iteration" or key.startswith("llm.token_count") or key.startswith("gen_ai.usage"):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0
    if key == "deanery.mcp":
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes"}
        return bool(value)
    return value


def _clean_value(key: str, value):
    value = _coerce(key, value)
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
        return value
    if value is None:
        return ""
    limit = _SHORT_LIMIT if key in _SHORT_KEYS else _VALUE_LIMIT
    return redact(str(value), limit=limit)


def _defaults() -> dict:
    bound = _bound_var.get()
    def pick(field: str, env: str, fallback=""):
        if bound is not None and getattr(bound, field) is not None:
            return getattr(bound, field)
        return os.environ.get(env, fallback)

    raw_iter = pick("iteration", "DEANERY_ITERATION", None)
    if raw_iter is None or raw_iter == "":
        iteration = 0
    else:
        try:
            iteration = int(raw_iter)
        except (TypeError, ValueError):
            iteration = 0
    route = str(pick("route", "DEANERY_ROUTE", "") or "unknown")
    if route not in _ROUTES:
        route = "unknown"
    attrs = {
        "deanery.job_id": str(pick("job_id", "DEANERY_JOB_ID", "") or ""),
        "deanery.lane_id": str(pick("lane_id", "DEANERY_LANE_ID", "") or ""),
        "deanery.parent_lane": str(pick("parent_lane", "DEANERY_PARENT_LANE", "") or ""),
        "deanery.task_class": str(pick("task_class", "DEANERY_TASK_CLASS", "") or ""),
        "deanery.route": route,
        "deanery.iteration": iteration,
    }
    model = pick("model", "", None)
    provider = pick("provider", "", None)
    if model:
        attrs["llm.model_name"] = str(model)
    if provider:
        attrs["llm.provider"] = str(provider)
    return attrs


def sanitize(attrs: dict, *, kind: str = "CHAIN", file_only: bool = False) -> dict:
    """Redact values and drop secret-named keys. Safe to call with no SDK."""
    merged = _defaults()
    merged["openinference.span.kind"] = (kind or "CHAIN").upper()
    for key, value in attrs.items():
        merged[str(key)] = value
    if "openinference.span.kind" in attrs:
        merged["openinference.span.kind"] = str(attrs["openinference.span.kind"]).upper()
    clean = {}
    for key, value in merged.items():
        if secret_attr_key(key):
            continue
        if file_only and _content_key(key):
            continue
        try:
            clean[key] = _clean_value(key, value)
        except Exception:
            continue
    return clean


def _provider_key(provider: str) -> str:
    text = (provider or "").strip().lower()
    if "/" in text:
        text = text.split("/", 1)[0]
    return text


def _host_of(url: str) -> str:
    raw = (url or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "http://" + raw
    return urllib.parse.urlparse(raw).hostname or ""


def route_for(provider: str = "", base_url: str = "") -> str:
    """local, cloud, or unknown. Loopback wins. Never labels an unknown host local."""
    try:
        host = _host_of(base_url)
        if host and _loopback_host(host):
            return "local"
        key = _provider_key(provider)
        if key in _LOCAL_PROVIDERS:
            return "local"
        if key in _CLOUD_PROVIDERS:
            return "cloud"
        return "unknown"
    except Exception:
        return "unknown"


def _parse_tp(value: str) -> tuple[int, int] | None:
    parts = (value or "").strip().split("-")
    if len(parts) != 4:
        return None
    if len(parts[1]) != 32 or len(parts[2]) != 16:
        return None
    try:
        trace_id = int(parts[1], 16)
        span_id = int(parts[2], 16)
    except ValueError:
        return None
    if trace_id <= 0 or span_id <= 0:
        return None
    return trace_id, span_id


def _format_tp(trace_id: int, span_id: int) -> str:
    return "00-%032x-%016x-01" % (trace_id, span_id)


def _new_id(bits: int) -> int:
    value = secrets.randbits(bits)
    return value or 1


class Handle:
    """In-memory span. Export is best-effort and silent."""

    def __init__(self, name: str, kind: str = "CHAIN") -> None:
        self.name = redact(str(name or "span"), limit=200) or "span"
        self.kind = (kind or "CHAIN").upper()
        if self.kind not in _KINDS:
            self.kind = "CHAIN"
        self.attributes: dict = {}
        self.events: list = []
        self.children: list = []
        self.status = "ok"
        self.file_only = False
        self.trace_id = ""
        self.span_id = ""
        self.parent_span_id = ""
        self._pushed = False
        self._stack_token = None
        self._otel = None
        self._otel_token = None

    def open(self, attrs: dict) -> None:
        parent = _stack_var.get()
        if parent:
            parent[-1].children.append(self)
            self.trace_id = parent[-1].trace_id
            self.parent_span_id = parent[-1].span_id
        else:
            parsed = _parse_tp(os.environ.get("TRACEPARENT") or "")
            if parsed:
                self.trace_id = "%032x" % parsed[0]
                self.parent_span_id = "%016x" % parsed[1]
            else:
                self.trace_id = "%032x" % _new_id(128)
        self.span_id = "%016x" % _new_id(64)
        self.attributes = sanitize(attrs, kind=self.kind, file_only=self.file_only)
        kind_attr = str(self.attributes.get("openinference.span.kind") or self.kind).upper()
        if kind_attr in _KINDS:
            self.kind = kind_attr
        self._stack_token = _stack_var.set(_stack_var.get() + (self,))
        self._pushed = True
        self._start_export()

    def close(self) -> None:
        try:
            self._end_export()
        finally:
            if self._pushed:
                try:
                    _stack_var.reset(self._stack_token)
                except ValueError:
                    pass
                self._pushed = False

    def mark_error(self, exc: BaseException) -> None:
        self.status = "error"
        self.set("exception.type", type(exc).__name__)
        self.event("exception", **{"exception.type": type(exc).__name__, "exception.message": str(exc)})

    def set(self, key, value) -> None:
        try:
            if secret_attr_key(str(key)):
                return
            if self.file_only and _content_key(str(key)):
                return
            clean = _clean_value(str(key), value)
            self.attributes[str(key)] = clean
            if self._otel is not None:
                self._otel.set_attribute(str(key), clean)
        except Exception:
            return

    def event(self, name, **attrs) -> None:
        try:
            clean = {}
            for key, value in attrs.items():
                if secret_attr_key(str(key)):
                    continue
                if self.file_only and _content_key(str(key)):
                    continue
                clean[str(key)] = _clean_value(str(key), value)
            self.events.append({"name": redact(str(name), limit=200) or "event", "attributes": clean})
            if self._otel is not None:
                self._otel.add_event(self.events[-1]["name"], clean)
        except Exception:
            return

    def child(self, name, kind="CHAIN", **attrs):
        return span(name, kind=kind, **attrs)

    def _start_export(self) -> None:
        if not ensure() or _tracer is None or _sdk is None:
            return
        trace_api = _sdk["trace"]
        otel_context = _sdk["context"]
        otel_kind = trace_api.SpanKind.CLIENT if self.kind in {"LLM", "TOOL"} else trace_api.SpanKind.INTERNAL
        self._otel = _tracer.start_span(self.name, kind=otel_kind, attributes=self.attributes)
        ctx = self._otel.get_span_context()
        self.trace_id = "%032x" % ctx.trace_id
        self.span_id = "%016x" % ctx.span_id
        self._otel_token = otel_context.attach(trace_api.set_span_in_context(self._otel))

    def _end_export(self) -> None:
        if self._otel is None or _sdk is None:
            return
        try:
            trace_api = _sdk["trace"]
            code = trace_api.StatusCode.ERROR if self.status == "error" else trace_api.StatusCode.OK
            self._otel.set_status(trace_api.Status(code))
            self._otel.end()
        except Exception:
            pass
        if self._otel_token is not None:
            try:
                _sdk["context"].detach(self._otel_token)
            except Exception:
                pass
        self._otel = None
        self._otel_token = None


@contextlib.contextmanager
def span(name, kind="CHAIN", **attrs):
    handle = Handle(name, kind)
    try:
        handle.open(attrs)
    except Exception:
        pass
    try:
        yield handle
    except BaseException as exc:
        try:
            handle.mark_error(exc)
        except Exception:
            pass
        raise
    finally:
        try:
            handle.close()
        except Exception:
            pass


@contextlib.contextmanager
def bind(**kwargs):
    """Set deanery.* defaults for spans opened inside the block."""
    current = _bound_var.get()
    nxt = _Bound()
    if current is not None:
        for field in _Bound.__slots__:
            setattr(nxt, field, getattr(current, field))
    for key, value in kwargs.items():
        if key in _Bound.__slots__:
            setattr(nxt, key, value)
    token = _bound_var.set(nxt)
    try:
        yield nxt
    finally:
        try:
            _bound_var.reset(token)
        except ValueError:
            pass


@contextlib.contextmanager
def llm_call(model, provider, route=None, **attrs):
    base = str(attrs.pop("base_url", None) or attrs.pop("url", None) or "")
    if route not in _ROUTES:
        route = route_for(str(provider or ""), base)
    name = str(attrs.pop("name", None) or "llm")
    prompt_tokens = attrs.pop("prompt_tokens", None)
    completion_tokens = attrs.pop("completion_tokens", None)
    total_tokens = attrs.pop("total_tokens", None)
    input_summary = attrs.pop("input_summary", None)
    output_summary = attrs.pop("output_summary", None)
    attrs["llm.model_name"] = "" if model is None else str(model)
    attrs["llm.provider"] = "" if provider is None else str(provider)
    attrs["deanery.route"] = route
    if prompt_tokens is not None:
        attrs["llm.token_count.prompt"] = prompt_tokens
    if completion_tokens is not None:
        attrs["llm.token_count.completion"] = completion_tokens
    if total_tokens is not None:
        attrs["llm.token_count.total"] = total_tokens
    elif prompt_tokens is not None and completion_tokens is not None:
        try:
            attrs["llm.token_count.total"] = int(prompt_tokens) + int(completion_tokens)
        except (TypeError, ValueError):
            pass
    if input_summary is not None:
        attrs["input.value"] = input_summary
    if output_summary is not None:
        attrs["output.value"] = output_summary
    with span(name, kind="LLM", **attrs) as handle:
        yield handle


@contextlib.contextmanager
def tool_call(name, **attrs):
    attrs["tool.name"] = "" if name is None else str(name)
    with span(name or "tool", kind="TOOL", **attrs) as handle:
        yield handle


@contextlib.contextmanager
def mcp_call(server, tool, **attrs):
    attrs["deanery.mcp"] = True
    attrs["tool.name"] = "" if tool is None else str(tool)
    attrs["deanery.mcp.server"] = "" if server is None else str(server)
    attrs["deanery.mcp.tool"] = "" if tool is None else str(tool)
    label = "mcp.%s.%s" % (server or "mcp", tool or "tool")
    with span(label, kind="TOOL", **attrs) as handle:
        yield handle


@contextlib.contextmanager
def file_op(path, op, **attrs):
    kept = {key: value for key, value in attrs.items() if not _content_key(str(key))}
    kept["tool.name"] = "" if op is None else str(op)
    kept["deanery.file.path"] = "" if path is None else str(path)
    kept["deanery.file.op"] = "" if op is None else str(op)
    with span("file.%s" % (op or "op"), kind="TOOL", **kept) as handle:
        handle.file_only = True
        yield handle


@contextlib.contextmanager
def reasoning(summary, **attrs):
    short = redact(str(summary or ""), limit=_SHORT_LIMIT)
    attrs["output.value"] = short
    attrs["llm.output_messages.0.message.contents.0.message_content.type"] = "reasoning"
    attrs["llm.output_messages.0.message.contents.0.message_content.text"] = short
    with span("reasoning", kind="CHAIN", **attrs) as handle:
        yield handle


def _current_traceparent() -> str:
    try:
        if _mode == "live" and _sdk is not None:
            carrier: dict[str, str] = {}
            _sdk["propagator"].inject(carrier)
            found = carrier.get("traceparent") or ""
            if found:
                return found
    except Exception:
        pass
    stack = _stack_var.get()
    if stack:
        current = stack[-1]
        if current.trace_id and current.span_id:
            return "00-%s-%s-01" % (current.trace_id, current.span_id)
    return os.environ.get("TRACEPARENT") or ""


def child_env(base: dict | None = None) -> dict:
    """Copy base (or os.environ) and set TRACEPARENT for a child process."""
    try:
        env = dict(os.environ if base is None else base)
    except Exception:
        return {}
    try:
        tp = _current_traceparent()
        if tp:
            env["TRACEPARENT"] = tp
        defaults = _defaults()
        for key, value in defaults.items():
            env_key = key.replace(".", "_").upper()
            if key.startswith("deanery."):
                env[env_key] = str(value)
        if defaults.get("llm.model_name"):
            env["DEANERY_MODEL"] = str(defaults["llm.model_name"])
        if defaults.get("llm.provider"):
            env["DEANERY_PROVIDER"] = str(defaults["llm.provider"])
    except Exception:
        return env
    return env


def flush(timeout_ms: int = 1000) -> None:
    try:
        proc = _processor
        if proc is not None:
            proc.force_flush(timeout_millis=int(timeout_ms))
    except Exception:
        return


def _flush_at_exit() -> None:
    worker = threading.Thread(target=lambda: flush(1000), daemon=True)
    worker.start()
    worker.join(1.0)


atexit.register(_flush_at_exit)


def _reset() -> None:
    """Test hook. Drops the latched no-op and shuts a live exporter down."""
    global _mode, _warned, _processor, _provider, _tracer, _resource, _sdk, _attached
    proc = _processor
    _processor = None
    _provider = None
    _tracer = None
    _resource = None
    _mode = "unknown"
    _warned = False
    if _attached is not None and _sdk is not None:
        try:
            _sdk["context"].detach(_attached)
        except Exception:
            pass
    _attached = None
    _sdk = None
    if proc is not None:
        try:
            proc.force_flush(timeout_millis=200)
        except Exception:
            pass
        try:
            proc.shutdown()
        except Exception:
            pass


def _mint_traceparent() -> str:
    parent = _parse_tp(os.environ.get("TRACEPARENT") or "")
    trace_id = parent[0] if parent else _new_id(128)
    return _format_tp(trace_id, _new_id(64))


def _cmd_traceparent() -> int:
    if os.environ.get("PFY_OTEL", "") == "0":
        return 0
    try:
        sys.stdout.write(_mint_traceparent() + "\n")
    except Exception:
        return 0
    return 0


def _cmd_emit(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="pfylib.otel emit", add_help=False)
    parser.add_argument("--name", default="span")
    parser.add_argument("--start-ns", type=int, default=0)
    parser.add_argument("--end-ns", type=int, default=0)
    parser.add_argument("--status", default="ok")
    parser.add_argument("--attr", action="append", default=[])
    parser.add_argument("--traceparent", default="")
    parser.add_argument("--parent", default="")
    parser.add_argument("--kind", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    if not ensure():
        return 0
    try:
        attrs = {}
        kind = (args.kind or "CHAIN").upper()
        for item in args.attr:
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            if key == "kind" and not args.kind:
                kind = value.upper()
                continue
            attrs[key] = value
        if kind not in _KINDS:
            kind = "CHAIN"
        clean = sanitize(attrs, kind=kind)
        _emit_readable(
            args.name,
            kind,
            clean,
            args.traceparent,
            args.parent,
            args.start_ns,
            args.end_ns,
            args.status,
        )
        flush(1000)
    except Exception:
        return 0
    return 0


def _emit_readable(name, kind, attrs, traceparent, parent, start_ns, end_ns, status) -> None:
    if _sdk is None or _processor is None:
        return
    trace_api = _sdk["trace"]
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.sdk.util.instrumentation import InstrumentationScope

    own = _parse_tp(traceparent) or (_new_id(128), _new_id(64))
    flags = trace_api.TraceFlags(trace_api.TraceFlags.SAMPLED)
    context = trace_api.SpanContext(own[0], own[1], False, flags)
    parent_ctx = None
    parsed_parent = _parse_tp(parent)
    if parsed_parent:
        parent_ctx = trace_api.SpanContext(parsed_parent[0], parsed_parent[1], True, flags)
    otel_kind = trace_api.SpanKind.CLIENT if kind in {"LLM", "TOOL"} else trace_api.SpanKind.INTERNAL
    code = trace_api.StatusCode.ERROR if str(status).lower() == "error" else trace_api.StatusCode.OK
    now = time.time_ns()
    start = int(start_ns or now)
    end = int(end_ns or now)
    if end < start:
        end = start
    span_obj = ReadableSpan(
        name=redact(str(name), limit=200) or "span",
        context=context,
        parent=parent_ctx,
        resource=_resource,
        attributes=attrs,
        events=(),
        links=(),
        kind=otel_kind,
        status=trace_api.Status(code),
        start_time=start,
        end_time=end,
        instrumentation_scope=InstrumentationScope("deanery.otel"),
    )
    _processor.on_end(span_obj)


def _load_exporter():
    path = Path(__file__).resolve().parents[1] / "scripts" / "grok_trace_export.py"
    spec = importlib.util.spec_from_file_location("grok_trace_export_otel", path)
    if spec is None or spec.loader is None:
        raise ImportError("grok_trace_export")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_path(blob: str) -> str:
    import re

    match = re.search(r'"(?:target_file|file_path|filepath|path)"\s*:\s*"([^"]+)"', blob or "")
    if match:
        return match.group(1)
    match = re.search(r"(?:target_file|file_path|filepath|path)=(\S+)", blob or "")
    if match:
        return match.group(1)
    return ""


def _mcp_parts(name: str) -> tuple[str, str] | None:
    if not name.startswith("mcp__"):
        return None
    parts = name.split("__")
    server = parts[1] if len(parts) > 1 else ""
    tool = "__".join(parts[2:]) if len(parts) > 2 else name
    return server, tool


def _one_child(child: dict) -> None:
    kind = str(child.get("kind") or "").upper()
    name = str(child.get("tool_name") or child.get("name") or "tool")
    failed = str(child.get("status") or "").upper().startswith("ERR")
    mcp = _mcp_parts(name)
    if mcp and kind == "TOOL":
        with mcp_call(mcp[0], mcp[1]) as handle:
            if failed:
                handle.status = "error"
        return
    op = _FILE_OPS.get(name)
    if op and kind == "TOOL":
        with file_op(_extract_path(str(child.get("input") or "")), op) as handle:
            if failed:
                handle.status = "error"
        return
    if kind == "LLM":
        with llm_call(
            child.get("model") or "grok",
            "xai",
            "cloud",
            name=str(child.get("name") or "assistant"),
            output_summary=str(child.get("output") or ""),
        ) as handle:
            if failed:
                handle.status = "error"
        return
    if kind == "TOOL":
        with tool_call(name) as handle:
            summary = child.get("input")
            if summary:
                handle.set("input.value", summary)
            if failed:
                handle.status = "error"


def _reasoning_bits(text: str) -> list[str]:
    found = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue
        if raw.lower().startswith("reasoning"):
            rest = raw.split(None, 1)[1] if " " in raw else ""
            if rest:
                found.append(rest)
            continue
        if not raw.startswith("{"):
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("type") == "reasoning":
            content = row.get("content") or row.get("text") or ""
            if isinstance(content, str) and content.strip():
                found.append(content)
    return found


def _ingest_log(path: Path) -> None:
    module = _load_exporter()
    doc = module.convert(path)
    children = list(doc.get("children") or []) if isinstance(doc, dict) else []
    text = path.read_text(encoding="utf-8", errors="replace")
    emitted = 0
    for child in children:
        if emitted >= 32:
            return
        if isinstance(child, dict):
            _one_child(child)
            emitted += 1
    for summary in _reasoning_bits(text):
        if emitted >= 32:
            return
        with reasoning(summary):
            pass
        emitted += 1


def _cmd_ingest(argv: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="pfylib.otel ingest", add_help=False)
    parser.add_argument("--log", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    if not args.log or not ensure():
        return 0
    try:
        path = Path(args.log)
        if not path.is_file():
            return 0
        _ingest_log(path)
        flush(1000)
    except Exception:
        return 0
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if not args or args[0] in {"-h", "--help"}:
            sys.stderr.write("usage: python3 -m pfylib.otel emit|traceparent|ingest\n")
            return 0 if args else 2
        cmd = args[0]
        if cmd == "traceparent":
            return _cmd_traceparent()
        if cmd == "emit":
            return _cmd_emit(args[1:])
        if cmd == "ingest":
            return _cmd_ingest(args[1:])
        return 2
    except Exception:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
