#!/usr/bin/env python3
"""Post one deanery span to loopback Phoenix and read it back.

Does not call systemctl and does not run scripts/phoenix_service.sh enable
or disable. A down collector is exit 2. Exit 0 only when the same trace id
is returned by the UI's getTraceByOtelId query, by the REST span list, and
by pfylib.lane_graph.

Stdout is one JSON object. It has no home paths.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib.lane_graph import build_graph, fetch_spans  # noqa: E402

ENDPOINT = "http://127.0.0.1:6006"
PROJECT = "deanery"
SPAN_NAME = "eval-arize-phoenix"
LANE_ID = "eval-arize-phoenix"
PIN_FILE = ROOT / "config" / "phoenix" / "version.txt"
THRESHOLD = 1
POLL_S = 12.0
HOME_RE = re.compile(r"/home/[^/\s\"']+")


def _public(value):
    if isinstance(value, str):
        return HOME_RE.sub("/home/<user>", value)
    if isinstance(value, list):
        return [_public(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _public(item) for key, item in value.items()}
    return value


def _emit_json(payload: dict) -> None:
    sys.stdout.write(json.dumps(_public(payload), indent=2, sort_keys=True) + "\n")


def _opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _get(url: str, timeout: float = 5.0) -> tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"Accept": "*/*"})
    try:
        with _opener().open(request, timeout=timeout) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()
    except Exception:
        return 0, b""


def _graphql(query: str, variables: dict | None = None) -> dict:
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT + "/graphql",
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    with _opener().open(request, timeout=8) as response:
        body = json.loads(response.read().decode("utf-8"))
    if body.get("errors"):
        raise RuntimeError("graphql errors")
    data_obj = body.get("data")
    if not isinstance(data_obj, dict):
        raise RuntimeError("graphql data missing")
    return data_obj


def _pin() -> str:
    return PIN_FILE.read_text(encoding="utf-8").strip()


def _venv_python() -> Path | None:
    cache = os.environ.get("PFY_TOOL_CACHE") or str(Path.home() / ".cache" / "pfy")
    path = Path(cache) / "tools" / "phoenix" / "venv" / "bin" / "python"
    if path.is_file() and os.access(path, os.X_OK):
        return path
    return None


def _installed_version() -> str | None:
    python = _venv_python()
    if python is None:
        return None
    proc = subprocess.run(
        [
            str(python),
            "-c",
            "import importlib.metadata as m; print(m.version('arize-phoenix'))",
        ],
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _venv_bytes() -> int | None:
    python = _venv_python()
    if python is None:
        return None
    venv = python.parents[1]
    proc = subprocess.run(
        ["du", "-sb", str(venv)],
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )
    if proc.returncode != 0:
        return None
    token = proc.stdout.split()
    if not token or not token[0].isdigit():
        return None
    return int(token[0])


def _child_env() -> dict:
    """Own trace. A lane TRACEPARENT would attach this span to the parent trace."""
    env = dict(os.environ)
    env.pop("PFY_OTEL", None)
    env.pop("TRACEPARENT", None)
    env["PFY_OTEL_ENDPOINT"] = ENDPOINT + "/v1/traces"
    return env


def _run_otel(args: list[str], env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pfylib.otel", *args],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
        check=False,
    )


def _trace_of(line: str) -> tuple[str, str] | None:
    parts = line.strip().split("-")
    if len(parts) != 4 or parts[0] != "00":
        return None
    trace_id, span_id, flags = parts[1], parts[2], parts[3]
    if len(trace_id) != 32 or len(span_id) != 16 or flags != "01":
        return None
    if any(ch not in "0123456789abcdef" for ch in trace_id + span_id):
        return None
    return trace_id, span_id


def _ui_bundle_has_query() -> bool:
    code, raw = _get(ENDPOINT + "/", timeout=5)
    if code != 200:
        return False
    html = raw.decode("utf-8", "replace")
    match = re.search(r'src="(/assets/index-[^"]+\.js)"', html)
    if not match:
        return False
    code, bundle = _get(ENDPOINT + match.group(1), timeout=20)
    if code != 200:
        return False
    return b"getTraceByOtelId" in bundle


def _read_trace(trace_id: str) -> dict | None:
    query = """
    query ($id: String!) {
      getTraceByOtelId(traceId: $id) {
        traceId
        numSpans
        project { name id }
        rootSpan { name spanKind }
      }
    }
    """
    try:
        data = _graphql(query, {"id": trace_id})
    except Exception:
        return None
    found = data.get("getTraceByOtelId")
    if not isinstance(found, dict):
        return None
    if found.get("traceId") != trace_id:
        return None
    return found


def _rest_span(trace_id: str) -> dict | None:
    url = ENDPOINT + "/v1/projects/" + PROJECT + "/spans?limit=50&sort=start_time&order=desc"
    code, raw = _get(url, timeout=5)
    if code != 200:
        return None
    try:
        body = json.loads(raw.decode("utf-8"))
    except Exception:
        return None
    rows = body.get("data") if isinstance(body, dict) else None
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        context = row.get("context") if isinstance(row.get("context"), dict) else {}
        if str(context.get("trace_id") or "") != trace_id:
            continue
        attrs = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
        return {
            "found": True,
            "name": row.get("name"),
            "lane_id": attrs.get("deanery.lane_id"),
            "route": attrs.get("deanery.route"),
            "task_class": attrs.get("deanery.task_class"),
        }
    return None


def _lane_node(trace_id: str) -> dict | None:
    fetched = fetch_spans(ENDPOINT, PROJECT, timeout=2)
    if not fetched.get("ok"):
        return None
    graph = build_graph(
        fetched.get("spans") or [],
        project_id=fetched.get("project_id"),
        endpoint=fetched.get("endpoint"),
    )
    for node in graph.get("nodes") or []:
        if node.get("trace_id") == trace_id and node.get("lane_id") == LANE_ID:
            return {
                "ok": True,
                "lane_id": node.get("lane_id"),
                "route": node.get("route"),
                "task_class": node.get("task_class"),
                "name": node.get("name"),
                "phoenix_url": node.get("phoenix_url"),
            }
    return None


def main() -> int:
    started = time.monotonic()
    pin = _pin()
    installed = _installed_version()
    base = {
        "metric": "span_roundtrip",
        "threshold": THRESHOLD,
        "pin": pin,
        "installed_version": installed,
        "endpoint": ENDPOINT,
        "project": PROJECT,
        "span_name": SPAN_NAME,
        "unit_touched": False,
        "download_bytes": 0,
        "venv_bytes": _venv_bytes(),
    }
    code, health = _get(ENDPOINT + "/healthz", timeout=2)
    if code != 200 or health.strip() != b"OK":
        _emit_json({**base, "ok": False, "value": 0, "why": "phoenix down", "elapsed_s": round(time.monotonic() - started, 4)})
        return 2
    if installed != pin:
        _emit_json({
            **base,
            "ok": False,
            "value": 0,
            "why": "installed version does not match pin",
            "elapsed_s": round(time.monotonic() - started, 4),
        })
        return 1

    env = _child_env()
    minted = _run_otel(["traceparent"], env)
    parsed = _trace_of(minted.stdout)
    if minted.returncode != 0 or parsed is None:
        _emit_json({**base, "ok": False, "value": 0, "why": "traceparent failed", "elapsed_s": round(time.monotonic() - started, 4)})
        return 1
    trace_id, span_id = parsed
    emit = _run_otel(
        [
            "emit",
            "--name", SPAN_NAME,
            "--kind", "CHAIN",
            "--status", "ok",
            "--traceparent", minted.stdout.strip(),
            "--attr", "deanery.lane_id=" + LANE_ID,
            "--attr", "deanery.job_id=span-roundtrip",
            "--attr", "deanery.task_class=eval",
            "--attr", "deanery.route=local",
            "--attr", "deanery.iteration=1",
            "--attr", "input.value=span-roundtrip",
            "--attr", "output.value=loopback-ok",
        ],
        env,
    )
    if emit.stderr:
        sys.stderr.write(emit.stderr)
    found = None
    rest = None
    deadline = time.monotonic() + POLL_S
    while time.monotonic() < deadline:
        found = _read_trace(trace_id)
        rest = _rest_span(trace_id)
        if found and rest:
            break
        time.sleep(0.4)

    ui_title = ""
    ui_code, ui_raw = _get(ENDPOINT + "/", timeout=5)
    if ui_code == 200:
        match = re.search(br"<title>([^<]*)</title>", ui_raw)
        if match:
            ui_title = match.group(1).decode("utf-8", "replace")
    bundle_ok = _ui_bundle_has_query()
    lane = _lane_node(trace_id) if found else None
    project = found.get("project") if isinstance(found, dict) else None
    project_id = project.get("id") if isinstance(project, dict) else None
    root_span = found.get("rootSpan") if isinstance(found, dict) else None
    phoenix_url = None
    if isinstance(lane, dict):
        phoenix_url = lane.get("phoenix_url")
    ui_trace_http = 0
    if isinstance(phoenix_url, str) and phoenix_url.startswith(ENDPOINT + "/"):
        ui_trace_http, trace_page = _get(phoenix_url, timeout=5)
        if b"<title>Phoenix</title>" not in trace_page:
            ui_trace_http = 0

    graphql_ok = (
        isinstance(found, dict)
        and found.get("numSpans") == 1
        and isinstance(root_span, dict)
        and root_span.get("name") == SPAN_NAME
        and isinstance(project, dict)
        and project.get("name") == PROJECT
    )
    rest_ok = (
        isinstance(rest, dict)
        and rest.get("name") == SPAN_NAME
        and rest.get("lane_id") == LANE_ID
        and rest.get("route") == "local"
        and rest.get("task_class") == "eval"
    )
    lane_ok = (
        isinstance(lane, dict)
        and lane.get("route") == "local"
        and lane.get("task_class") == "eval"
        and lane.get("name") == SPAN_NAME
        and isinstance(phoenix_url, str)
        and phoenix_url.startswith(ENDPOINT + "/projects/")
        and trace_id in phoenix_url
    )
    value = 1 if graphql_ok and rest_ok and lane_ok and bundle_ok and ui_title == "Phoenix" and ui_trace_http == 200 else 0
    payload = {
        **base,
        "ok": value == 1,
        "value": value,
        "trace_id": trace_id,
        "span_id": span_id,
        "emit_exit": emit.returncode,
        "healthz": "OK",
        "ui_title": ui_title,
        "ui_bundle_has_getTraceByOtelId": bundle_ok,
        "ui_trace_http": ui_trace_http,
        "project_id": project_id,
        "graphql": {
            "trace_id": found.get("traceId") if isinstance(found, dict) else None,
            "num_spans": found.get("numSpans") if isinstance(found, dict) else None,
            "span_name": root_span.get("name") if isinstance(root_span, dict) else None,
            "project": project.get("name") if isinstance(project, dict) else None,
        },
        "rest": rest,
        "lane_graph": lane,
        "elapsed_s": round(time.monotonic() - started, 4),
    }
    _emit_json(payload)
    return 0 if value == 1 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        _emit_json({"ok": False, "value": 0, "why": type(exc).__name__})
        raise SystemExit(1)
