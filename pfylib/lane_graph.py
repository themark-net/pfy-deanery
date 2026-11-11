"""Lane graph over local Phoenix spans.

Design: docs/design/LANE-GRAPH-IA.md

Reads GET /v1/projects/{name}/spans from a loopback Phoenix. Builds lanes,
parent edges, and retry / eval-loop edges. detail() is the outline beside
the graph. Callers get a dict. This module does not raise for Phoenix
failures.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

DEFAULT_ENDPOINT = "http://127.0.0.1:6006"
DEFAULT_PROJECT = "deanery"
DEFAULT_HOURS = 168
MAX_TIMEOUT = 2.0
PAGE_LIMIT = 100
MAX_PAGES = 10
CAP = 40

DOWN_WHY = "Phoenix is down. Start it with scripts/phoenix_service.sh enable"
LOOPBACK_WHY = (
    "Phoenix endpoint must stay on loopback. Start it with scripts/phoenix_service.sh enable"
)
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_ROUTES = frozenset({"local", "cloud", "mixed", "unknown"})
_LOCAL_PROVIDERS = ("ollama", "local", "freetoken", "llama", "vllm", "shimmy")
_CLOUD_PROVIDERS = ("grok", "xai", "openai", "anthropic", "gemini", "cloud")
_COST_TOTAL_KEYS = ("llm.cost.total", "llm.cost.total_cost", "llm.total_cost")
_COST_PART_KEYS = ("llm.cost.prompt", "llm.cost.completion")
_SECRET_KEY = re.compile(r"(?i)(secret|password|token|api[_-]?key|authorization|credential)")

# Last Phoenix body kept in this process. Not a store and not written to disk.
_last_response: dict = {
    "ok": False,
    "why": "",
    "spans": [],
    "project_id": None,
    "endpoint": None,
    "project": None,
}

_redact_impl = None


def _timeout(value) -> float:
    try:
        timeout = float(2.0 if value is None else value)
    except (TypeError, ValueError):
        return MAX_TIMEOUT
    if timeout <= 0 or timeout > MAX_TIMEOUT:
        return MAX_TIMEOUT
    return timeout


def _origin(url: str) -> str | None:
    """Return scheme://host:port for a loopback URL, else None."""
    try:
        parsed = urllib.parse.urlparse((url or "").strip())
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or host not in _LOOPBACK_HOSTS:
        return None
    if parsed.username or parsed.password:
        return None
    port = parsed.port
    if host == "::1":
        netloc = f"[{host}]" + (f":{port}" if port else "")
    else:
        netloc = host if port is None else f"{host}:{port}"
    return f"{parsed.scheme}://{netloc}"


def _down(why: str = DOWN_WHY) -> dict:
    return {
        "ok": False,
        "why": why,
        "spans": [],
        "project_id": None,
        "endpoint": None,
        "project": None,
    }


def _get_json(url: str, timeout: float) -> tuple[int, object]:
    """Return (status, body). Status 0 means Phoenix did not answer. Never raises."""
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code), None
    except Exception:
        return 0, None
    try:
        return status, json.loads(raw.decode("utf-8"))
    except Exception:
        return status, None


def fetch_spans(endpoint: str | None = None, project: str | None = None, timeout: float | None = None) -> dict:
    """Fetch deanery spans. Loopback only. Timeout at most 2s. Never raises."""
    global _last_response
    try:
        result = _fetch_spans(endpoint, project, timeout)
    except Exception:
        result = _down()
    _last_response = {
        "ok": bool(result.get("ok")),
        "why": result.get("why") or "",
        "spans": list(result.get("spans") or []),
        "project_id": result.get("project_id"),
        "endpoint": result.get("endpoint"),
        "project": result.get("project"),
    }
    return dict(result)


def _fetch_spans(endpoint: str | None, project: str | None, timeout: float | None) -> dict:
    limit = _timeout(timeout)
    raw_endpoint = endpoint if endpoint is not None else os.environ.get("PFY_PHOENIX_URL", DEFAULT_ENDPOINT)
    origin = _origin(str(raw_endpoint))
    if origin is None:
        refused = _down(LOOPBACK_WHY)
        refused["endpoint"] = str(raw_endpoint or "")
        return refused
    name = project if project is not None else os.environ.get("PFY_PHOENIX_PROJECT", DEFAULT_PROJECT)
    name = str(name or DEFAULT_PROJECT).strip() or DEFAULT_PROJECT
    hours = _hours()
    code, body = _get_json(
        origin + "/v1/projects/" + urllib.parse.quote(name, safe=""),
        limit,
    )
    if code == 0:
        failed = _down()
        failed["endpoint"] = origin
        failed["project"] = name
        return failed
    project_id = None
    if code == 200 and isinstance(body, dict) and isinstance(body.get("data"), dict):
        project_id = body["data"].get("id") or None
    spans, span_code = _collect_spans(origin, name, hours, limit)
    if span_code == 0:
        failed = _down()
        failed["endpoint"] = origin
        failed["project"] = name
        failed["project_id"] = project_id
        return failed
    return {
        "ok": True,
        "why": "",
        "spans": spans,
        "project_id": project_id,
        "endpoint": origin,
        "project": name,
    }


def _hours() -> int:
    raw = os.environ.get("PFY_LANE_GRAPH_HOURS", str(DEFAULT_HOURS))
    try:
        return max(0, int(raw))
    except (TypeError, ValueError):
        return DEFAULT_HOURS


def _collect_spans(origin: str, project: str, hours: int, timeout: float) -> tuple[list, int]:
    spans: list = []
    cursor = None
    seen: set[str] = set()
    now = datetime.now(timezone.utc)
    query_base: dict[str, str] = {
        "limit": str(PAGE_LIMIT),
        "sort": "start_time",
        "order": "desc",
    }
    if hours > 0:
        query_base["start_time"] = _iso(now - timedelta(hours=hours))
        query_base["end_time"] = _iso(now + timedelta(minutes=5))
    path = origin + "/v1/projects/" + urllib.parse.quote(project, safe="") + "/spans"
    for _ in range(MAX_PAGES):
        query = dict(query_base)
        if cursor:
            query["cursor"] = cursor
        url = path + "?" + urllib.parse.urlencode(query)
        code, body = _get_json(url, timeout)
        if code == 0:
            return [], 0
        if code == 404:
            return [], 404
        if code != 200 or body is None:
            return [], 0
        if isinstance(body, list):
            page = body
            nxt = None
        elif isinstance(body, dict):
            page = body.get("data") or []
            nxt = body.get("next_cursor")
        else:
            return [], 0
        if not isinstance(page, list):
            return [], 0
        spans.extend(item for item in page if isinstance(item, dict))
        if not nxt or nxt in seen:
            break
        seen.add(str(nxt))
        cursor = str(nxt)
    return spans, 200


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _span_list(spans) -> list:
    if isinstance(spans, dict):
        data = spans.get("data")
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        nested = spans.get("spans")
        if isinstance(nested, list):
            return [item for item in nested if isinstance(item, dict)]
        return []
    if isinstance(spans, list):
        return [item for item in spans if isinstance(item, dict)]
    return []


def _attrs(span: dict) -> dict:
    raw = span.get("attributes")
    return raw if isinstance(raw, dict) else {}


def _attr(span: dict, key: str, default=None):
    return _from_map(_attrs(span), key, default)


def _from_map(attrs: dict, key: str, default=None):
    if key in attrs:
        return attrs[key]
    current = attrs
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return default
    return current


def _text_attr(span: dict, key: str) -> str:
    value = _attr(span, key, "")
    if value is None:
        return ""
    return str(value).strip()


def _span_id(span: dict) -> str:
    context = span.get("context") if isinstance(span.get("context"), dict) else {}
    return str(context.get("span_id") or span.get("span_id") or span.get("id") or "")


def _trace_id(span: dict) -> str:
    context = span.get("context") if isinstance(span.get("context"), dict) else {}
    return str(context.get("trace_id") or span.get("trace_id") or "")


def _parent_id(span: dict) -> str:
    value = span.get("parent_id")
    if value is None:
        value = span.get("parent_span_id")
    return str(value or "")


def _kind(span: dict) -> str:
    raw = span.get("span_kind") or _attr(span, "openinference.span.kind") or ""
    return str(raw).upper()


def _parse_time(value) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if number > 1e12:
            return number / 1e9
        return number
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


def _iteration(span: dict) -> int:
    value = _attr(span, "deanery.iteration", 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _span_status(span: dict) -> str:
    code = str(span.get("status_code") or "").upper()
    if code == "ERROR":
        return "error"
    if span.get("end_time") in (None, ""):
        return "running"
    return "ok"


def _duration_ms(span: dict) -> int | None:
    start = _parse_time(span.get("start_time"))
    end = _parse_time(span.get("end_time"))
    if start is None or end is None:
        return None
    return max(0, int(round((end - start) * 1000)))


def _number(value) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _span_cost(span: dict) -> float | None:
    for key in _COST_TOTAL_KEYS:
        found = _number(_attr(span, key))
        if found is not None:
            return found
    parts = []
    for key in _COST_PART_KEYS:
        found = _number(_attr(span, key))
        if found is not None:
            parts.append(found)
    if parts:
        return float(sum(parts))
    return None


def _route_from_provider(provider: str) -> str:
    text = (provider or "").lower()
    if not text:
        return "unknown"
    if any(mark in text for mark in _LOCAL_PROVIDERS):
        return "local"
    if any(mark in text for mark in _CLOUD_PROVIDERS):
        return "cloud"
    return "unknown"


def _call_route(span: dict) -> str:
    raw = _text_attr(span, "deanery.route").lower()
    if raw in _ROUTES:
        return raw
    return _route_from_provider(_text_attr(span, "llm.provider"))


def _merge_routes(routes) -> str:
    kinds = {route for route in routes if route in ("local", "cloud", "mixed")}
    if "mixed" in kinds or {"local", "cloud"} <= kinds:
        return "mixed"
    if "local" in kinds:
        return "local"
    if "cloud" in kinds:
        return "cloud"
    return "unknown"


def _is_llm(span: dict) -> bool:
    if _kind(span) == "LLM":
        return True
    return bool(_text_attr(span, "llm.model_name"))


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes")
    return False


def _prepare(spans):
    """Index spans and assign each one a lane id. Tolerates missing keys."""
    items = _span_list(spans)
    by_sid: dict[str, dict] = {}
    for span in items:
        sid = _span_id(span)
        if sid and sid not in by_sid:
            by_sid[sid] = span

    def lane_of(span: dict, seen: set[str] | None = None) -> str:
        seen = set() if seen is None else seen
        sid = _span_id(span)
        if sid and sid in seen:
            return ""
        if sid:
            seen.add(sid)
        explicit = _text_attr(span, "deanery.lane_id")
        if explicit:
            return explicit
        parent = by_sid.get(_parent_id(span))
        if parent is not None and parent is not span:
            found = lane_of(parent, seen)
            if found:
                return found
        if not _parent_id(span):
            return str(span.get("name") or "").strip() or "lane"
        return ""

    def is_header(span: dict, lane: str) -> bool:
        parent = by_sid.get(_parent_id(span))
        if parent is None:
            return True
        return lane_of(parent) != lane

    records = []
    for span in items:
        lane = lane_of(span) or "lane"
        records.append(
            {
                "span": span,
                "lane": lane,
                "trace": _trace_id(span) or "trace",
                "header": is_header(span, lane),
            }
        )
    return by_sid, records


def _task_label(task_class: str, name: str) -> str:
    short = (name or "").strip()
    if len(short) > 48:
        short = short[:45] + "..."
    task_class = (task_class or "").strip()
    if task_class and short and task_class != short:
        return task_class + " " + short
    return task_class or short or "lane"


def _phoenix_url(endpoint: str | None, project_id, trace_id: str) -> str | None:
    if not endpoint or not project_id or not trace_id:
        return None
    base = str(endpoint).rstrip("/")
    project = urllib.parse.quote(str(project_id), safe="")
    trace = urllib.parse.quote(str(trace_id), safe="")
    return f"{base}/projects/{project}/traces/{trace}"


def _loop_label(lane_id: str, task_class: str, name: str, count: int) -> str:
    blob = " ".join((lane_id, task_class, name)).lower()
    if "eval" in blob:
        return f"eval loop {count}"
    return f"retry {count}"


def build_graph(spans, *, project_id=None, endpoint=None) -> dict:
    """Pure graph. spans is a Phoenix REST body or a list of span dicts."""
    _by_sid, records = _prepare(spans)
    groups: dict[tuple[str, str], list] = {}
    for record in records:
        groups.setdefault((record["trace"], record["lane"]), []).append(record)

    nodes = []
    for (trace_id, lane_id), group in groups.items():
        spans_in = [record["span"] for record in group]
        headers = [record["span"] for record in group if record["header"]] or spans_in[:1]

        def _when(span: dict):
            return (_iteration(span), _parse_time(span.get("start_time")) or 0.0)

        latest = max(headers, key=_when)
        earliest_header = min(headers, key=_when)
        task_class = ""
        name = ""
        for header in sorted(headers, key=_when):
            if not task_class:
                task_class = _text_attr(header, "deanery.task_class")
            if not name:
                name = str(header.get("name") or "").strip()
        llms = [span for span in spans_in if _is_llm(span)]
        if llms:
            route = _merge_routes(_call_route(span) for span in llms)
            latest_llm = max(llms, key=lambda span: _parse_time(span.get("start_time")) or 0.0)
            model = _text_attr(latest_llm, "llm.model_name") or None
            provider = _text_attr(latest_llm, "llm.provider") or None
        else:
            declared = []
            for span in spans_in:
                raw = _text_attr(span, "deanery.route").lower()
                if raw in _ROUTES:
                    declared.append(raw)
            if declared:
                route = _merge_routes(declared)
            else:
                route = _merge_routes(
                    _route_from_provider(_text_attr(span, "llm.provider"))
                    for span in spans_in
                    if _text_attr(span, "llm.provider")
                )
            model = None
            provider = None
        cost = None
        for span in spans_in:
            part = _span_cost(span)
            if part is None:
                continue
            cost = part if cost is None else cost + part
        starts = [moment for moment in (_parse_time(span.get("start_time")) for span in spans_in) if moment is not None]
        ends = [moment for moment in (_parse_time(span.get("end_time")) for span in spans_in) if moment is not None]
        duration_ms = None
        if starts and ends:
            duration_ms = max(0, int(round((max(ends) - min(starts)) * 1000)))
        iteration = max(_iteration(span) for span in spans_in)
        parent_lane = ""
        for header in sorted(headers, key=_when, reverse=True):
            parent_lane = _text_attr(header, "deanery.parent_lane")
            if parent_lane:
                break
        if not parent_lane:
            for header in sorted(headers, key=_when, reverse=True):
                parent = _by_sid.get(_parent_id(header))
                if parent is None:
                    continue
                other = ""
                for record in records:
                    if record["span"] is parent:
                        other = record["lane"]
                        break
                if other and other != lane_id:
                    parent_lane = other
                    break
        task = _task_label(task_class, name or lane_id)
        summary = {
            "task": task,
            "model": model,
            "provider": provider,
            "route": route,
            "status": _span_status(latest),
            "duration_ms": duration_ms,
            "cost": cost,
            "iteration": iteration,
        }
        nodes.append(
            {
                "id": lane_id,
                "lane_id": lane_id,
                "trace_id": trace_id,
                "task": task,
                "task_class": task_class,
                "name": name or lane_id,
                "model": model,
                "provider": provider,
                "route": route,
                "status": summary["status"],
                "duration_ms": duration_ms,
                "cost": cost,
                "iteration": iteration,
                "runs": len(headers),
                "phoenix_url": _phoenix_url(endpoint, project_id, trace_id),
                "summary": summary,
                "_parent": parent_lane,
                "_start": _parse_time(earliest_header.get("start_time")) or 0.0,
            }
        )

    counts: dict[str, int] = {}
    for node in nodes:
        counts[node["lane_id"]] = counts.get(node["lane_id"], 0) + 1
    for node in nodes:
        if counts[node["lane_id"]] > 1:
            node["id"] = node["lane_id"] + "@" + node["trace_id"][:8]

    by_key = {(node["trace_id"], node["lane_id"]): node for node in nodes}
    edges = []
    for node in nodes:
        parent_id = node.get("_parent") or ""
        parent = by_key.get((node["trace_id"], parent_id))
        if parent is None or parent["id"] == node["id"]:
            continue
        edges.append(
            {
                "id": f"calls:{parent['id']}->{node['id']}",
                "source": parent["id"],
                "target": node["id"],
                "route": node["route"],
                "kind": "calls",
                "label": "",
            }
        )
        count = node["iteration"] if node["iteration"] > 0 else node["runs"] - 1
        if node["iteration"] > 0 or node["runs"] > 1:
            if count > 0:
                edges.append(
                    {
                        "id": f"loop:{node['id']}->{parent['id']}",
                        "source": node["id"],
                        "target": parent["id"],
                        "route": node["route"],
                        "kind": "loop",
                        "label": _loop_label(node["lane_id"], node["task_class"], node["name"], count),
                    }
                )

    nodes.sort(key=lambda node: (node["_start"], node["id"]))
    for node in nodes:
        node.pop("_parent", None)
        node.pop("_start", None)
        node.pop("runs", None)
    edges.sort(key=lambda edge: edge["id"])

    traces_map: dict[str, dict] = {}
    for node in nodes:
        bucket = traces_map.setdefault(
            node["trace_id"],
            {
                "trace_id": node["trace_id"],
                "phoenix_url": _phoenix_url(endpoint, project_id, node["trace_id"]),
                "lanes": [],
            },
        )
        bucket["lanes"].append(node["lane_id"])
    return {"nodes": nodes, "edges": edges, "traces": list(traces_map.values())}


def _load_grok_redact():
    path = Path(__file__).resolve().parents[1] / "scripts" / "grok_trace_export.py"
    spec = importlib.util.spec_from_file_location("pfy_grok_trace_export_redact", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "redact", None)


def _redactor():
    global _redact_impl
    if _redact_impl is not None:
        return _redact_impl
    primary = None
    secret_key = None
    try:
        from pfylib.redact import redact as primary
        from pfylib.redact import secret_attr_key as secret_key
    except ImportError:
        primary = None
        secret_key = None
    if primary is None:
        try:
            primary = _load_grok_redact()
        except Exception:
            primary = None
    otel = None
    try:
        from pfylib.otel import redact as otel
    except ImportError:
        otel = None

    def apply(text: str, key: str | None = None) -> str:
        raw = "" if text is None else str(text)
        if key:
            try:
                if secret_key is not None and secret_key(key):
                    return "[REDACTED]"
            except Exception:
                pass
            if secret_key is None and _SECRET_KEY.search(key):
                return "[REDACTED]"
        out = raw
        if primary is not None:
            try:
                out = primary(out)
            except TypeError:
                try:
                    out = primary(out, None)
                except Exception:
                    out = raw
            except Exception:
                out = raw
        if otel is not None and otel is not primary:
            try:
                out = otel(out)
            except TypeError:
                try:
                    out = otel(out, None)
                except Exception:
                    pass
            except Exception:
                pass
        return out

    _redact_impl = apply
    return apply


def _shown(value, key: str | None = None) -> str:
    return _redactor()("" if value is None else str(value), key)


def _empty_tabs() -> dict:
    return {"reasoning": [], "file_ops": [], "mcp_calls": [], "tool_calls": []}


def detail(trace_id: str, lane_id: str, spans=None) -> dict:
    """Outline for one lane. Tabs are capped and redacted. Never raises."""
    try:
        return _detail(trace_id, lane_id, spans)
    except Exception:
        return {
            "ok": False,
            "why": DOWN_WHY,
            "trace_id": trace_id,
            "lane_id": lane_id,
            "steps": [],
            "tabs": _empty_tabs(),
            "phoenix_url": None,
        }


def _detail(trace_id: str, lane_id: str, spans) -> dict:
    if spans is None:
        if not _last_response.get("ok"):
            return {
                "ok": False,
                "why": _last_response.get("why") or DOWN_WHY,
                "trace_id": trace_id,
                "lane_id": lane_id,
                "steps": [],
                "tabs": _empty_tabs(),
                "phoenix_url": None,
            }
        spans = _last_response.get("spans") or []
        endpoint = _last_response.get("endpoint")
        project_id = _last_response.get("project_id")
    else:
        endpoint = None
        project_id = None
    _by_sid, records = _prepare(spans)
    chosen = [
        record["span"]
        for record in records
        if record["trace"] == trace_id and record["lane"] == lane_id
    ]
    chosen.sort(key=lambda span: (_parse_time(span.get("start_time")) or 0.0, _span_id(span)))
    steps = []
    reasoning = []
    file_ops = []
    mcp_calls = []
    tool_calls = []
    for span in chosen:
        name = str(span.get("name") or "")
        name_l = name.lower()
        status = _span_status(span)
        duration = _duration_ms(span)
        steps.append(
            {
                "span_id": _span_id(span),
                "name": _shown(name),
                "kind": _kind(span) or "UNKNOWN",
                "status": status,
                "duration_ms": duration,
            }
        )
        for event in span.get("events") or []:
            if not isinstance(event, dict):
                continue
            event_name = str(event.get("name") or "")
            attrs = event.get("attributes") if isinstance(event.get("attributes"), dict) else {}
            summary = _from_map(attrs, "deanery.reasoning.summary", None)
            if summary not in (None, ""):
                reasoning.append({"summary": _shown(summary, "deanery.reasoning.summary")})
        summary_attr = _attr(span, "deanery.reasoning.summary", None)
        if name_l == "reasoning" and summary_attr not in (None, ""):
            reasoning.append({"summary": _shown(summary_attr, "deanery.reasoning.summary")})
        file_path = _attr(span, "deanery.file.path", None)
        file_op = _attr(span, "deanery.file.op", None)
        if name_l == "file_op" or file_path not in (None, "") or file_op not in (None, ""):
            file_ops.append(
                {
                    "path": _shown(file_path or "", "deanery.file.path"),
                    "op": _shown(file_op or "", "deanery.file.op"),
                }
            )
            continue
        if _truthy(_attr(span, "deanery.mcp")):
            mcp_calls.append(
                {
                    "server": _shown(_attr(span, "deanery.mcp.server", ""), "deanery.mcp.server"),
                    "tool": _shown(
                        _attr(span, "deanery.mcp.tool", "") or _attr(span, "tool.name", ""),
                        "deanery.mcp.tool",
                    ),
                    "status": status,
                    "duration_ms": duration,
                }
            )
            continue
        if _kind(span) == "TOOL" and name_l != "reasoning":
            tool_calls.append(
                {
                    "name": _shown(_attr(span, "tool.name", "") or name, "tool.name"),
                    "status": status,
                    "duration_ms": duration,
                }
            )
    return {
        "ok": True,
        "why": "",
        "trace_id": trace_id,
        "lane_id": lane_id,
        "steps": steps[:CAP],
        "tabs": {
            "reasoning": reasoning[:CAP],
            "file_ops": file_ops[:CAP],
            "mcp_calls": mcp_calls[:CAP],
            "tool_calls": tool_calls[:CAP],
        },
        "phoenix_url": _phoenix_url(endpoint, project_id, trace_id),
    }


def lanes_document() -> dict:
    """Payload for GET /lanes. HTTP layer always returns this with status 200."""
    fetched = fetch_spans()
    if not fetched.get("ok"):
        return {
            "ok": False,
            "why": fetched.get("why") or DOWN_WHY,
            "nodes": [],
            "edges": [],
            "traces": [],
            "window_hours": _hours(),
        }
    graph = build_graph(
        fetched.get("spans") or [],
        project_id=fetched.get("project_id"),
        endpoint=fetched.get("endpoint"),
    )
    graph["ok"] = True
    graph["why"] = ""
    graph["window_hours"] = _hours()
    return graph


def lane_detail_document(trace: str, lane: str) -> dict:
    """Payload for GET /lanes/detail. Never raises."""
    trace = str(trace or "")
    lane = str(lane or "")
    if not trace or not lane:
        return {
            "ok": False,
            "why": "missing trace or lane",
            "trace_id": trace,
            "lane_id": lane,
            "steps": [],
            "tabs": _empty_tabs(),
            "phoenix_url": None,
        }
    fetched = fetch_spans()
    if not fetched.get("ok"):
        return {
            "ok": False,
            "why": fetched.get("why") or DOWN_WHY,
            "trace_id": trace,
            "lane_id": lane,
            "steps": [],
            "tabs": _empty_tabs(),
            "phoenix_url": None,
        }
    outline = detail(trace, lane, spans=fetched.get("spans") or [])
    outline["phoenix_url"] = _phoenix_url(fetched.get("endpoint"), fetched.get("project_id"), trace)
    return outline
