"""Lane graph over local Phoenix.

How this fails: a down or non-loopback Phoenix raises or dials out, a second
span page is dropped, a file op leaks contents, a secret reaches the outline,
or the Runs view paints the wrong routes and tabs. Recovery: callers get
ok:false and the one-line start command, pagination is followed, detail
redacts and omits contents, and the view diffs the graph in place.
"""

from __future__ import annotations

import copy
import html as html_lib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
import unittest
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib.lane_graph import (  # noqa: E402
    DOWN_WHY,
    LOOPBACK_WHY,
    build_graph,
    detail,
    fetch_spans,
)

FIXTURE = ROOT / "tests" / "fixtures" / "lane_graph" / "spans.json"
TRACE = "a11ce001a11ce001a11ce001a11ce001"
ENABLE = "scripts/phoenix_service.sh enable"
CHROME = "/usr/bin/google-chrome"
FRONTEND = ROOT / "gui" / "operator" / "frontend"


def _load_board():
    spec = importlib.util.spec_from_file_location("pfy_board_lane_graph", ROOT / "scripts" / "pfy-board.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _spans():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _node(graph, lane_id):
    return next(node for node in graph["nodes"] if node["lane_id"] == lane_id)


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


class GraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = _spans()
        cls.graph = build_graph(
            cls.raw,
            project_id="UHJvamVjdDox",
            endpoint="http://127.0.0.1:6006",
        )

    def test_nodes_edges_and_summaries(self):
        graph = self.graph
        self.assertEqual(
            [node["id"] for node in graph["nodes"]],
            ["catalog-loop", "eval-widget", "catalog-fit", "integrate"],
        )
        by_id = {edge["id"]: edge for edge in graph["edges"]}
        self.assertEqual(by_id["calls:catalog-loop->eval-widget"]["route"], "cloud")
        self.assertEqual(by_id["calls:eval-widget->catalog-fit"]["route"], "local")
        self.assertEqual(by_id["calls:catalog-fit->integrate"]["route"], "mixed")
        loop = by_id["loop:eval-widget->catalog-loop"]
        self.assertEqual(loop["kind"], "loop")
        self.assertEqual(loop["label"], "eval loop 2")
        self.assertEqual(loop["source"], "eval-widget")
        self.assertEqual(loop["target"], "catalog-loop")
        self.assertEqual(sum(1 for edge in graph["edges"] if edge["kind"] == "loop"), 1)

        eval_lane = _node(graph, "eval-widget")
        self.assertEqual(eval_lane["model"], "grok-4.1")
        self.assertEqual(eval_lane["provider"], "xai")
        self.assertEqual(eval_lane["route"], "cloud")
        self.assertEqual(eval_lane["status"], "ok")
        self.assertEqual(eval_lane["duration_ms"], 5000)
        self.assertEqual(eval_lane["iteration"], 2)
        self.assertAlmostEqual(eval_lane["cost"], 0.021)
        self.assertEqual(eval_lane["summary"]["task"], "eval-lane eval-widget")
        self.assertIn("/projects/UHJvamVjdDox/traces/" + TRACE, eval_lane["phoenix_url"])

        fit = _node(graph, "catalog-fit")
        self.assertEqual(fit["model"], "qwen2.5:14b")
        self.assertEqual(fit["provider"], "ollama")
        self.assertEqual(fit["route"], "local")
        self.assertEqual(fit["status"], "ok")
        self.assertEqual(fit["duration_ms"], 2000)
        self.assertIsNone(fit["cost"])

        integrate = _node(graph, "integrate")
        self.assertEqual(integrate["route"], "mixed")
        self.assertEqual(integrate["model"], "grok-4.1")
        self.assertEqual(integrate["duration_ms"], 1500)
        self.assertAlmostEqual(integrate["cost"], 0.013)
        self.assertEqual(graph["traces"][0]["lanes"], ["catalog-loop", "eval-widget", "catalog-fit", "integrate"])

    def test_missing_lane_id_uses_root_name_and_provider_route(self):
        spans = [
            {
                "name": "catalog-loop",
                "context": {"trace_id": "t-root", "span_id": "root"},
                "parent_id": None,
                "span_kind": "CHAIN",
                "start_time": "2026-11-11T12:00:00Z",
                "end_time": "2026-11-11T12:00:01Z",
                "status_code": "OK",
                "attributes": {},
            },
            {
                "name": "fit",
                "context": {"trace_id": "t-root", "span_id": "fit"},
                "parent_id": "root",
                "span_kind": "CHAIN",
                "start_time": "2026-11-11T12:00:01Z",
                "end_time": "2026-11-11T12:00:02Z",
                "status_code": "OK",
                "attributes": {"deanery.lane_id": "catalog-fit", "deanery.parent_lane": "catalog-loop"},
            },
            {
                "name": "llm",
                "context": {"trace_id": "t-root", "span_id": "llm"},
                "parent_id": "fit",
                "span_kind": "LLM",
                "start_time": "2026-11-11T12:00:01.100000Z",
                "end_time": "2026-11-11T12:00:01.400000Z",
                "status_code": "OK",
                "attributes": {"llm.model_name": "qwen2.5:14b", "llm.provider": "ollama"},
            },
        ]
        graph = build_graph(spans)
        self.assertEqual(_node(graph, "catalog-loop")["route"], "unknown")
        self.assertEqual(_node(graph, "catalog-fit")["route"], "local")
        self.assertEqual(_node(graph, "catalog-fit")["model"], "qwen2.5:14b")

    def test_detail_tabs_hide_file_contents_and_mask_a_secret(self):
        outline = detail(TRACE, "eval-widget", spans=self.raw)
        self.assertTrue(outline["ok"])
        tabs = outline["tabs"]
        self.assertIn("retry after rubric miss", tabs["reasoning"][0]["summary"])
        self.assertIn("checked the rubric", tabs["reasoning"][1]["summary"])
        self.assertEqual(tabs["file_ops"], [{"path": "docs/design/LANE-GRAPH-IA.md", "op": "read"}])
        self.assertEqual(set(tabs["file_ops"][0]), {"path", "op"})
        self.assertEqual(tabs["mcp_calls"][0]["server"], "codebase-memory")
        self.assertEqual(tabs["mcp_calls"][0]["tool"], "search")
        self.assertEqual(tabs["mcp_calls"][0]["status"], "ok")
        self.assertEqual(tabs["mcp_calls"][0]["duration_ms"], 600)
        self.assertEqual(tabs["tool_calls"][0]["name"], "pytest")
        blob = json.dumps(outline)
        self.assertNotIn("SHOULD_NOT_APPEAR_FILE_BODY", blob)
        statuses = [step["status"] for step in outline["steps"] if step["name"] == "eval-widget"]
        self.assertEqual(statuses, ["error", "error", "ok"])

        secret = "sk-" + "lane" + "graph" + "secret"
        cloned = copy.deepcopy(self.raw["data"])
        for span in cloned:
            if span["name"] == "reasoning":
                span["attributes"]["deanery.reasoning.summary"] = "note " + secret
        masked = json.dumps(detail(TRACE, "eval-widget", spans=cloned))
        self.assertNotIn(secret, masked)
        self.assertIn("[REDACTED]", masked)

    def test_detail_caps_each_tab(self):
        spans = []
        for index in range(45):
            spans.append(
                {
                    "name": "file_op",
                    "context": {"trace_id": "t-cap", "span_id": f"{index:016d}"},
                    "parent_id": None,
                    "span_kind": "TOOL",
                    "start_time": "2026-11-11T12:00:00Z",
                    "end_time": "2026-11-11T12:00:01Z",
                    "status_code": "OK",
                    "attributes": {
                        "deanery.lane_id": "cap-lane",
                        "deanery.file.path": f"file-{index}.txt",
                        "deanery.file.op": "read",
                    },
                }
            )
        outline = detail("t-cap", "cap-lane", spans=spans)
        self.assertEqual(len(outline["tabs"]["file_ops"]), 40)
        self.assertEqual(len(outline["steps"]), 40)


class TraceCapTests(unittest.TestCase):
    """A busy store (hundreds of unrelated runs) must not pack the graph into one row."""

    def test_only_the_most_recent_traces_are_drawn(self):
        from pfylib.lane_graph import recent_traces

        spans = []
        for i in range(30):
            spans.append({
                "name": "lane-%02d" % i,
                "context": {"trace_id": "%032x" % (i + 1), "span_id": "%016x" % (i + 1)},
                "parent_id": None,
                "start_time": "2026-11-11T20:%02d:00+00:00" % i,
                "end_time": "2026-11-11T20:%02d:01+00:00" % i,
                "attributes": {"deanery.lane_id": "lane-%02d" % i, "deanery.route": "local"},
            })
        kept = recent_traces({"data": spans}, cap=8)
        graph = build_graph(kept)
        self.assertEqual(sorted(n["lane_id"] for n in graph["nodes"]), ["lane-%02d" % i for i in range(22, 30)])
        os.environ["PFY_LANE_GRAPH_TRACES"] = "nonsense"
        try:
            self.assertEqual(len({s["context"]["trace_id"] for s in recent_traces(spans)}), 8)
        finally:
            os.environ.pop("PFY_LANE_GRAPH_TRACES", None)


class PhoenixFailureTests(unittest.TestCase):
    def setUp(self):
        self._env = {
            key: os.environ.get(key)
            for key in ("PFY_PHOENIX_URL", "PFY_PHOENIX_PROJECT", "PFY_LANE_GRAPH_HOURS")
        }

    def tearDown(self):
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_non_loopback_is_refused_without_a_dial(self):
        started = time.perf_counter()
        result = fetch_spans(endpoint="http://10.255.255.1:6006", timeout=2)
        elapsed = time.perf_counter() - started
        self.assertFalse(result["ok"])
        self.assertEqual(result["why"], LOOPBACK_WHY)
        self.assertIn(ENABLE, result["why"])
        self.assertNotIn("\n", result["why"])
        self.assertLess(elapsed, 0.3)
        self.assertEqual(result["spans"], [])

    def test_phoenix_down_is_one_line_and_board_returns_200(self):
        port = _free_port()
        os.environ["PFY_PHOENIX_URL"] = f"http://127.0.0.1:{port}"
        os.environ["PFY_PHOENIX_PROJECT"] = "deanery"
        started = time.perf_counter()
        result = fetch_spans()
        self.assertFalse(result["ok"])
        self.assertEqual(result["why"], DOWN_WHY)
        self.assertIn(ENABLE, result["why"])
        self.assertLess(time.perf_counter() - started, 2.5)

        board = _load_board()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), board.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            started = time.perf_counter()
            with urllib.request.urlopen(
                f"http://127.0.0.1:{httpd.server_address[1]}/lanes",
                timeout=5,
            ) as response:
                body = response.read()
                status = response.status
            elapsed = time.perf_counter() - started
        finally:
            httpd.shutdown()
            httpd.server_close()
        self.assertEqual(status, 200)
        self.assertLess(elapsed, 2.5)
        payload = json.loads(body)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["why"], DOWN_WHY)
        self.assertEqual(payload["nodes"], [])


class FakePhoenix:
    def __init__(self, page1, page2):
        self.page1 = page1
        self.page2 = page2
        self.paths = []
        parent = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                parent.paths.append(parsed.path)
                if parsed.path == "/v1/projects/deanery":
                    body = {"data": {"id": "UHJvamVjdDox", "name": "deanery", "description": None}}
                elif parsed.path == "/v1/projects/deanery/spans":
                    cursor = (parse_qs(parsed.query).get("cursor") or [None])[0]
                    if cursor == "page-2":
                        body = {"next_cursor": None, "data": parent.page2}
                    else:
                        body = {"next_cursor": "page-2", "data": parent.page1}
                else:
                    self.send_error(404)
                    return
                raw = json.dumps(body).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, fmt, *args):
                return

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class BoardEndToEndTests(unittest.TestCase):
    def setUp(self):
        raw = _spans()["data"]
        page1 = [span for span in raw if str(span["context"]["span_id"]).startswith(("aaaa", "bbbb"))]
        page2 = [span for span in raw if span not in page1]
        self.assertGreater(len(page1), 0)
        self.assertGreater(len(page2), 0)
        self.fake = FakePhoenix(page1, page2)
        self._env = {
            key: os.environ.get(key)
            for key in ("PFY_PHOENIX_URL", "PFY_PHOENIX_PROJECT", "PFY_LANE_GRAPH_HOURS")
        }
        os.environ["PFY_PHOENIX_URL"] = self.fake.url
        os.environ["PFY_PHOENIX_PROJECT"] = "deanery"
        os.environ["PFY_LANE_GRAPH_HOURS"] = "168"

    def tearDown(self):
        self.fake.close()
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_board_lanes_follows_phoenix_pages(self):
        board = _load_board()
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), board.Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{httpd.server_address[1]}/lanes",
                timeout=5,
            ) as response:
                self.assertEqual(response.status, 200)
                payload = json.loads(response.read())
            query = urlencode({"trace": TRACE, "lane": "eval-widget"})
            with urllib.request.urlopen(
                f"http://127.0.0.1:{httpd.server_address[1]}/lanes/detail?{query}",
                timeout=5,
            ) as response:
                outline = json.loads(response.read())
        finally:
            httpd.shutdown()
            httpd.server_close()
        self.assertTrue(payload["ok"], payload.get("why"))
        self.assertEqual(
            [node["id"] for node in payload["nodes"]],
            ["catalog-loop", "eval-widget", "catalog-fit", "integrate"],
        )
        self.assertIn("/v1/projects/deanery/spans", self.fake.paths)
        self.assertIn("/v1/projects/deanery", self.fake.paths)
        self.assertTrue(outline["ok"])
        self.assertEqual(outline["tabs"]["mcp_calls"][0]["tool"], "search")
        self.assertIn("UHJvamVjdDox", outline["phoenix_url"])

        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "pfy-board.py"), "--lane-detail", TRACE, "catalog-fit"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(ROOT),
            env=os.environ.copy(),
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        cli = json.loads(proc.stdout)
        self.assertTrue(cli["ok"])
        self.assertEqual(cli["lane_id"], "catalog-fit")
        self.assertTrue(any(step["kind"] == "LLM" for step in cli["steps"]))


class FrontendRenderTests(unittest.TestCase):
    def test_headless_chrome_paints_nodes_edges_and_tabs(self):
        chrome = CHROME if Path(CHROME).is_file() else shutil.which("google-chrome")
        if not chrome:
            self.skipTest("google-chrome missing")
        graph = build_graph(self_raw(), project_id="UHJvamVjdDox", endpoint="http://127.0.0.1:6006")
        outline = detail(TRACE, "eval-widget", spans=_spans())
        page = {
            "graph": graph,
            "detail": outline,
            "lane": "eval-widget",
            "tab": "file_ops",
        }
        html = """<!DOCTYPE html><html><head><meta charset="utf-8"><title>lane</title>
<style>#lane-cy{width:900px;height:520px}</style></head>
<body data-lane-test="1"><div id="lane-cy"></div><pre id="lane-graph-summary"></pre>
<script src="/vendor/cytoscape.min.js"></script>
<script src="/lane-graph.js"></script>
<script>LaneGraph.renderForTest(%s);</script>
</body></html>""" % json.dumps(page)
        served = {"html": html.encode("utf-8")}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                path = urlparse(self.path).path
                if path == "/harness.html":
                    body = served["html"]
                    ctype = "text/html; charset=utf-8"
                else:
                    rel = path.lstrip("/")
                    fp = (FRONTEND / rel).resolve()
                    try:
                        fp.relative_to(FRONTEND.resolve())
                    except ValueError:
                        self.send_error(404)
                        return
                    if not fp.is_file():
                        self.send_error(404)
                        return
                    body = fp.read_bytes()
                    ctype = "application/javascript; charset=utf-8"
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                return

        httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        url = f"http://127.0.0.1:{httpd.server_address[1]}/harness.html"
        try:
            proc = subprocess.run(
                [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-sandbox",
                    "--virtual-time-budget=8000",
                    "--dump-dom",
                    url,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
        finally:
            httpd.shutdown()
            httpd.server_close()
        self.assertEqual(proc.returncode, 0, proc.stderr[-500:])
        dom = proc.stdout
        start = dom.find('<pre id="lane-graph-summary">')
        self.assertGreater(start, -1, dom[-800:])
        start = dom.find(">", start) + 1
        end = dom.find("</pre>", start)
        summary = json.loads(html_lib.unescape(dom[start:end]))
        self.assertNotIn("error", summary, summary)
        self.assertEqual(summary["nodes"], ["catalog-loop", "eval-widget", "catalog-fit", "integrate"])
        classes = {edge["id"]: edge["classes"] for edge in summary["edges"]}
        self.assertIn("route-cloud", classes["calls:catalog-loop->eval-widget"])
        self.assertIn("route-local", classes["calls:eval-widget->catalog-fit"])
        self.assertIn("route-mixed", classes["calls:catalog-fit->integrate"])
        self.assertIn("loop:eval-widget->catalog-loop", summary["loops"])
        self.assertIn("loop", classes["loop:eval-widget->catalog-loop"])
        self.assertEqual(summary["tabs"], ["Reasoning", "File ops", "MCP calls", "Tool calls"])
        self.assertTrue(summary["legend"])
        self.assertTrue(summary["detail_open"])
        self.assertIn("docs/design/LANE-GRAPH-IA.md", summary["tab_body"])
        self.assertNotIn("SHOULD_NOT_APPEAR_FILE_BODY", dom)
        # The eval lane's outline links to its model-choice row on Loop.
        self.assertEqual(summary["model_lever"], "eval-lane")


def self_raw():
    return _spans()


if __name__ == "__main__":
    unittest.main()
