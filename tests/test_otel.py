"""Behavior of local Phoenix spans: redaction, no-op when tracing cannot run, and a protobuf tree when the SDK is installed.

No network except 127.0.0.1. Secrets in this file are built at runtime.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "otel_span.sh"
SDK_SITE = ROOT / "tmp" / "toolcache" / "tools" / "otel" / ("site-py%d%d" % sys.version_info[:2])

sys.path.insert(0, str(ROOT))

import pfylib.otel as otel  # noqa: E402
from pfylib.redact import redact  # noqa: E402


def _sentinel() -> str:
    return "Zz" + "9secret" + "Qq"


def _quiet_env(**extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PFY_OTEL"] = "0"
    env.pop("PFY_OTEL_ENDPOINT", None)
    env.update(extra)
    return env


class RedactionTests(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["PFY_OTEL"] = "0"
        otel._reset()
        self.mark = _sentinel()

    def tearDown(self) -> None:
        otel._reset()

    def test_span_attributes_and_events_mask_secrets_and_drop_secret_keys(self) -> None:
        mark = self.mark
        samples = {
            "xai": "xai-" + "AbCdEfGh" + mark,
            "sk": "sk-" + "AbCdEfGh" + mark,
            "ghp": "ghp_" + ("a" * 20) + mark,
            "pat": "github_pat_" + ("a" * 22) + mark,
            "akia": "AKIA" + ("0" * 16),
            "bearer": "Bearer " + mark,
            "env": "API_KEY=" + mark,
            "query": "https://example.com/cb?token=" + mark + "&x=1",
            "userinfo": "https://" + "user:" + mark + "@example.com/a",
            "pem": (
                "-----BEGIN "
                + "RSA PRIVATE KEY-----\n"
                + mark
                + "\n-----END "
                + "RSA PRIVATE KEY-----"
            ),
            "vars": "XAI_API_KEY=" + mark + "\nCOOKIE=" + mark,
            "auth": '{"access_token":"' + mark + '","password":"' + mark + '"}',
            "blob": "aA1" + ("bB2cC3dD4eE5fF6gG7hH8" * 3),
        }
        with otel.span("lane") as handle:
            for key, value in samples.items():
                handle.set("note." + key, value)
            handle.set("api_key", mark)
            handle.set("Authorization", "Bearer " + mark)
            handle.set("llm.token_count.prompt", 3)
            handle.event("http", header="Authorization: Bearer " + mark, query=samples["query"])
        dumped = json.dumps({"attributes": handle.attributes, "events": handle.events})
        self.assertNotIn(mark, dumped)
        self.assertNotIn(samples["akia"], dumped)
        self.assertNotIn(samples["blob"], dumped)
        self.assertNotIn("api_key", handle.attributes)
        self.assertNotIn("Authorization", handle.attributes)
        self.assertEqual(handle.attributes["llm.token_count.prompt"], 3)
        self.assertIn("[REDACTED]", dumped)
        self.assertIn("deanery.route", handle.attributes)
        self.assertEqual(handle.attributes["deanery.iteration"], 0)

    def test_ordinary_words_and_file_paths_stay(self) -> None:
        mark = self.mark
        text = redact("monkey=" + mark + " target_file=same.py")
        self.assertIn(mark, text)
        self.assertIn("target_file=same.py", text)
        self.assertEqual(redact("A" * 80), "A" * 80)
        clipped = redact("B" * 3000, limit=2000)
        self.assertTrue(clipped.endswith("...[truncated]"))
        self.assertLess(len(clipped), 2020)

    def test_file_op_keeps_path_and_op_and_drops_contents(self) -> None:
        mark = self.mark
        with otel.file_op("/tmp/a.py", "write", contents=mark, body=mark, diff=mark) as handle:
            handle.set("content", mark)
            handle.set("text", mark)
            handle.event("edit", patch=mark)
        dumped = json.dumps({"attributes": handle.attributes, "events": handle.events})
        self.assertNotIn(mark, dumped)
        self.assertEqual(handle.attributes["deanery.file.path"], "/tmp/a.py")
        self.assertEqual(handle.attributes["deanery.file.op"], "write")
        self.assertNotIn("content", handle.attributes)
        self.assertNotIn("contents", handle.attributes)
        self.assertEqual(handle.events[0]["attributes"], {})


class NoopTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("PFY_OTEL", None)
        os.environ.pop("PFY_OTEL_ENDPOINT", None)
        os.environ.pop("PFY_TOOL_CACHE", None)
        otel._reset()

    def test_closed_port_span_is_silent_and_records_locally(self) -> None:
        os.environ.pop("PFY_OTEL", None)
        os.environ["PFY_OTEL_ENDPOINT"] = "http://127.0.0.1:1/v1/traces"
        os.environ["PFY_TOOL_CACHE"] = str(ROOT / "tmp" / "toolcache")
        otel._reset()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with otel.span("quiet", kind="CHAIN") as handle:
                handle.set("deanery.lane_id", "eval-x")
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(handle.attributes["deanery.lane_id"], "eval-x")
        self.assertEqual(otel._mode, "off")

    def test_non_loopback_warns_once_and_does_not_raise(self) -> None:
        os.environ.pop("PFY_OTEL", None)
        os.environ["PFY_OTEL_ENDPOINT"] = "http://example.com/v1/traces"
        otel._reset()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with otel.span("nope"):
                pass
            with otel.span("again"):
                pass
        text = err.getvalue()
        self.assertEqual(text.count("refusing"), 1)
        self.assertIn("example.com", text)
        self.assertEqual(otel._mode, "off")

    def test_missing_sdk_is_a_silent_noop(self) -> None:
        os.environ.pop("PFY_OTEL", None)
        os.environ["PFY_OTEL_ENDPOINT"] = "http://127.0.0.1:9/v1/traces"
        os.environ["PFY_TOOL_CACHE"] = str(ROOT / "tmp" / "otel-empty-cache")
        otel._reset()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with otel.span("missing") as handle:
                handle.set("k", "v")
        self.assertEqual(err.getvalue(), "")
        self.assertEqual(handle.attributes["k"], "v")
        self.assertEqual(otel._mode, "off")

    def test_user_exception_still_propagates(self) -> None:
        os.environ["PFY_OTEL"] = "0"
        otel._reset()
        with self.assertRaises(RuntimeError):
            with otel.span("boom") as handle:
                raise RuntimeError("boom")
        self.assertEqual(handle.status, "error")

    def test_wrapper_preserves_exit_and_output_on_a_closed_port(self) -> None:
        env = os.environ.copy()
        env.pop("PFY_OTEL", None)
        env["PFY_OTEL_ENDPOINT"] = "http://127.0.0.1:1/v1/traces"
        env["PFY_TOOL_CACHE"] = str(ROOT / "tmp" / "toolcache")
        cases = [
            (0, ["true"], b"", b""),
            (1, ["false"], b"", b""),
            (7, ["bash", "-c", "exit 7"], b"", b""),
            (0, ["bash", "-c", "printf out; printf err >&2"], b"out", b"err"),
        ]
        for code, cmd, out, err in cases:
            started = time.monotonic()
            proc = subprocess.run(
                [str(WRAPPER), "probe", "--", *cmd],
                cwd=ROOT,
                env=env,
                capture_output=True,
                timeout=5,
            )
            elapsed = time.monotonic() - started
            self.assertEqual(proc.returncode, code, proc.stderr)
            self.assertEqual(proc.stdout, out)
            self.assertEqual(proc.stderr, err)
            if cmd == ["true"]:
                self.assertLess(elapsed, 1.0)

    def test_wrapper_forwards_sigterm(self) -> None:
        env = os.environ.copy()
        env.pop("PFY_OTEL", None)
        env["PFY_OTEL_ENDPOINT"] = "http://127.0.0.1:1/v1/traces"
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            pidfile = Path(tmp) / "child.pid"
            proc = subprocess.Popen(
                [
                    str(WRAPPER),
                    "sleep-span",
                    "--",
                    "bash",
                    "-c",
                    'printf %s "$$" > "$1"; sleep 30',
                    "bash",
                    str(pidfile),
                ],
                cwd=ROOT,
                env=env,
                start_new_session=True,
            )
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline and not pidfile.exists():
                if proc.poll() is not None:
                    break
                time.sleep(0.05)
            self.assertTrue(pidfile.is_file(), "child did not start")
            child = int(pidfile.read_text(encoding="utf-8").strip())
            os.kill(proc.pid, signal.SIGTERM)
            code = proc.wait(timeout=5)
            self.assertEqual(code, 128 + signal.SIGTERM)
            time.sleep(0.2)
            alive = True
            try:
                os.kill(child, 0)
            except OSError:
                alive = False
            if alive:
                os.kill(child, signal.SIGKILL)
            self.assertFalse(alive, "wrapped child survived SIGTERM to the wrapper")

    def test_sourced_non_loopback_does_not_abort_under_set_e(self) -> None:
        env = os.environ.copy()
        env.pop("PFY_OTEL", None)
        env["PFY_OTEL_ENDPOINT"] = "http://example.com/v1/traces"
        script = (
            "set -euo pipefail\n"
            ". scripts/otel_span.sh\n"
            "otel_span_begin demo deanery.route=cloud\n"
            "printf ok\n"
            "otel_span_end 0\n"
        )
        proc = subprocess.run(
            ["bash", "-c", script],
            cwd=ROOT,
            env=env,
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"ok")
        self.assertEqual(proc.stderr.count(b"refusing"), 1)

    def test_wrapper_non_loopback_warns_and_still_runs(self) -> None:
        env = os.environ.copy()
        env.pop("PFY_OTEL", None)
        env["PFY_OTEL_ENDPOINT"] = "http://example.com/v1/traces"
        proc = subprocess.run(
            [str(WRAPPER), "remote", "--", "printf", "hi"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, b"hi")
        self.assertEqual(proc.stderr.count(b"refusing"), 1)

    def test_traceparent_and_emit_noop_safely(self) -> None:
        env = _quiet_env()
        minted = subprocess.run(
            [sys.executable, "-m", "pfylib.otel", "traceparent"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(minted.returncode, 0)
        self.assertEqual(minted.stdout, "")
        env.pop("PFY_OTEL")
        env["PFY_OTEL_ENDPOINT"] = "http://127.0.0.1:1/v1/traces"
        parent = "00-" + ("ab" * 16) + "-" + ("cd" * 8) + "-01"
        env["TRACEPARENT"] = parent
        again = subprocess.run(
            [sys.executable, "-m", "pfylib.otel", "traceparent"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(again.returncode, 0)
        line = again.stdout.strip()
        self.assertTrue(line.startswith("00-" + ("ab" * 16) + "-"))
        self.assertNotEqual(line, parent)
        emitted = subprocess.run(
            [
                sys.executable,
                "-m",
                "pfylib.otel",
                "emit",
                "--name",
                "n",
                "--start-ns",
                "1",
                "--end-ns",
                "2",
                "--status",
                "ok",
                "--attr",
                "k=v",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(emitted.returncode, 0)
        self.assertEqual(emitted.stdout, "")
        self.assertEqual(emitted.stderr, "")


class RouteTests(unittest.TestCase):
    def test_route_table(self) -> None:
        self.assertEqual(otel.route_for("ollama", ""), "local")
        self.assertEqual(otel.route_for("vllm", "http://10.1.2.3:8000"), "local")
        self.assertEqual(otel.route_for("", "http://127.0.0.1:11434"), "local")
        self.assertEqual(otel.route_for("localhost", ""), "unknown")
        self.assertEqual(otel.route_for("", "http://localhost:11434/v1"), "local")
        self.assertEqual(otel.route_for("xai", ""), "cloud")
        self.assertEqual(otel.route_for("grok", "https://api.x.ai"), "cloud")
        self.assertEqual(otel.route_for("openai", "http://127.0.0.1:11434/v1"), "local")
        self.assertEqual(otel.route_for("openai-compatible", "http://example.com/v1"), "unknown")
        self.assertEqual(otel.route_for("", ""), "unknown")
        self.assertEqual(otel.route_for("vendor/model", "http://10.0.0.8"), "unknown")


def _sdk_ready() -> bool:
    return (SDK_SITE / "opentelemetry").is_dir()


def _any_value(value) -> object:
    kind = value.WhichOneof("value")
    if kind is None:
        return ""
    return getattr(value, kind)


def _decode(blobs: list[bytes]) -> list[dict]:
    site = str(SDK_SITE)
    if site not in sys.path:
        sys.path.insert(0, site)
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )

    found = []
    for blob in blobs:
        message = ExportTraceServiceRequest()
        message.ParseFromString(blob)
        for resource in message.resource_spans:
            resource_attrs = {item.key: _any_value(item.value) for item in resource.resource.attributes}
            for scope in resource.scope_spans:
                for span in scope.spans:
                    found.append(
                        {
                            "name": span.name,
                            "trace_id": span.trace_id.hex(),
                            "span_id": span.span_id.hex(),
                            "parent": span.parent_span_id.hex(),
                            "attrs": {item.key: _any_value(item.value) for item in span.attributes},
                            "resource": resource_attrs,
                        }
                    )
    return found


class _Collector(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or "0")
        body = self.rfile.read(length)
        if self.headers.get("Content-Encoding") == "gzip":
            import gzip

            body = gzip.decompress(body)
        self.server.posts.append(body)  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "application/x-protobuf")
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        return


@unittest.skipUnless(_sdk_ready(), "otel SDK is not in ./tmp/toolcache")
class ProtobufTreeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), _Collector)
        self.server.posts = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_address[1]
        os.environ.pop("PFY_OTEL", None)
        os.environ["PFY_OTEL_ENDPOINT"] = "http://127.0.0.1:%d/v1/traces" % self.port
        os.environ["PFY_TOOL_CACHE"] = str(ROOT / "tmp" / "toolcache")
        otel._reset()

    def tearDown(self) -> None:
        otel._reset()
        self.server.shutdown()
        self.server.server_close()
        os.environ.pop("PFY_OTEL_ENDPOINT", None)
        os.environ.pop("PFY_TOOL_CACHE", None)

    def _wait_spans(self) -> list[dict]:
        deadline = time.monotonic() + 5
        found: list[dict] = []
        while time.monotonic() < deadline:
            found = _decode(list(self.server.posts))
            names = {item["name"] for item in found}
            if {"wrap", "lane", "fit-llm", "grep", "file.read"} <= names:
                return found
            time.sleep(0.05)
        return found

    def test_bash_traceparent_parents_the_python_tree(self) -> None:
        mark = _sentinel()
        child = (
            "import os\n"
            "from pfylib.otel import file_op, flush, llm_call, span, tool_call\n"
            "with span('lane', kind='CHAIN', **{'deanery.lane_id': 'eval-demo', 'deanery.route': 'local'}):\n"
            "    with llm_call('demo-model', 'ollama', 'local', name='fit-llm'):\n"
            "        pass\n"
            "    with tool_call('grep'):\n"
            "        pass\n"
            "    with file_op('src/a.py', 'read', contents=%r):\n"
            "        pass\n"
            "    span_handle = None\n"
            "flush()\n"
            "print('CHILD_OK')\n"
        ) % mark
        # The secret is planted on the lane span from inside the child.
        child = child.replace(
            "with span('lane', kind='CHAIN', **{'deanery.lane_id': 'eval-demo', 'deanery.route': 'local'}):\n",
            "with span('lane', kind='CHAIN', **{'deanery.lane_id': 'eval-demo', 'deanery.route': 'local', 'note': %r}):\n"
            % ("sk-" + "AbCdEfGh" + mark),
        )
        env = os.environ.copy()
        env.pop("PFY_OTEL", None)
        env["PFY_OTEL_ENDPOINT"] = "http://127.0.0.1:%d/v1/traces" % self.port
        env["PFY_TOOL_CACHE"] = str(ROOT / "tmp" / "toolcache")
        proc = subprocess.run(
            [str(WRAPPER), "wrap", "--", sys.executable, "-c", child],
            cwd=ROOT,
            env=env,
            capture_output=True,
            timeout=15,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, b"CHILD_OK\n")
        self.assertNotIn(mark.encode(), proc.stdout)
        self.assertNotIn(mark.encode(), proc.stderr)
        spans = self._wait_spans()
        names = {item["name"] for item in spans}
        self.assertIn("wrap", names, spans)
        self.assertIn("lane", names, spans)
        by_name = {item["name"]: item for item in spans}
        wrap = by_name["wrap"]
        lane = by_name["lane"]
        llm = by_name["fit-llm"]
        tool = by_name["grep"]
        file_span = by_name["file.read"]
        self.assertEqual(lane["trace_id"], wrap["trace_id"])
        self.assertEqual(llm["trace_id"], wrap["trace_id"])
        self.assertEqual(lane["parent"], wrap["span_id"])
        self.assertEqual(llm["parent"], lane["span_id"])
        self.assertEqual(tool["parent"], lane["span_id"])
        self.assertEqual(file_span["parent"], lane["span_id"])
        self.assertEqual(llm["attrs"].get("deanery.route"), "local")
        self.assertEqual(llm["attrs"].get("llm.model_name"), "demo-model")
        self.assertEqual(llm["attrs"].get("openinference.span.kind"), "LLM")
        self.assertEqual(tool["attrs"].get("tool.name"), "grep")
        self.assertEqual(tool["attrs"].get("openinference.span.kind"), "TOOL")
        self.assertEqual(file_span["attrs"].get("deanery.file.path"), "src/a.py")
        self.assertEqual(file_span["attrs"].get("deanery.file.op"), "read")
        self.assertNotIn("contents", file_span["attrs"])
        raw = b"".join(self.server.posts)
        self.assertNotIn(mark.encode(), raw)
        self.assertEqual(lane["resource"].get("service.name"), "deanery")
        self.assertEqual(lane["resource"].get("openinference.project.name"), "deanery")

    def test_open_socket_without_sdk_stays_silent(self) -> None:
        # The class skip requires the SDK. This case points the cache at an empty dir
        # while a loopback port accepts the probe, and checks the shell still no-ops.
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        port = sock.getsockname()[1]
        env = os.environ.copy()
        env.pop("PFY_OTEL", None)
        env["PFY_OTEL_ENDPOINT"] = "http://127.0.0.1:%d/v1/traces" % port
        env["PFY_TOOL_CACHE"] = str(ROOT / "tmp" / "otel-empty-cache")
        try:
            proc = subprocess.run(
                [str(WRAPPER), "nosdk", "--", "printf", "ok"],
                cwd=ROOT,
                env=env,
                capture_output=True,
                timeout=5,
            )
        finally:
            sock.close()
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout, b"ok")
        self.assertEqual(proc.stderr, b"")


if __name__ == "__main__":
    unittest.main()
