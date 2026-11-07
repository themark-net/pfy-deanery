"""The Strata catch-up bench exits 0 only when every run is valid.

A loopback stub stands in for the engine. One empty stream must fail the
process. One short completion must pass. No model and no network.
"""
from __future__ import annotations

import json
import subprocess
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "eval/catchup-1107/strata/bench.py"


def _sse(events):
    chunks = []
    for event in events:
        chunks.append("data: %s\n\n" % json.dumps(event))
    chunks.append("data: [DONE]\n\n")
    return "".join(chunks).encode("utf-8")


class _Handler(BaseHTTPRequestHandler):
    bodies: list[bytes] = []
    sent = 0

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or "0")
        if length:
            self.rfile.read(length)
        body = self.bodies[type(self).sent]
        type(self).sent += 1
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


class StrataBenchExitTest(unittest.TestCase):
    def _serve(self, bodies):
        _Handler.bodies = list(bodies)
        _Handler.sent = 0
        server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def _stop():
            server.shutdown()
            server.server_close()

        self.addCleanup(_stop)
        return "http://127.0.0.1:%s" % server.server_address[1]

    def _run(self, base, out, runs):
        return subprocess.run(
            [
                sys.executable,
                str(BENCH),
                "--base",
                base,
                "--model",
                "stub",
                "--engine",
                "stub",
                "--out",
                str(out),
                "--runs",
                str(runs),
                "--only",
                "chat-2",
                "--timeout",
                "5",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_one_empty_run_exits_1(self):
        good = _sse(
            [
                {"choices": [{"delta": {"content": "red, blue, yellow"}}]},
                {"usage": {"prompt_tokens": 8, "completion_tokens": 4}},
            ]
        )
        empty = _sse([{"choices": [{"delta": {}}]}])
        base = self._serve([good, empty])
        out = Path("/tmp") / ("strata-bench-mixed-%s.json" % threading.get_ident())
        proc = self._run(base, out, 2)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        saved = json.loads(out.read_text())
        self.assertEqual(saved["summary"]["valid_runs"], 1)
        self.assertEqual(saved["summary"]["runs"], 2)
        out.unlink(missing_ok=True)

    def test_short_completion_exits_0(self):
        good = _sse(
            [
                {"choices": [{"delta": {"content": "red, blue, yellow"}}]},
                {"usage": {"prompt_tokens": 8, "completion_tokens": 4}},
            ]
        )
        base = self._serve([good])
        out = Path("/tmp") / ("strata-bench-ok-%s.json" % threading.get_ident())
        proc = self._run(base, out, 1)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        saved = json.loads(out.read_text())
        self.assertEqual(saved["summary"]["valid_runs"], 1)
        self.assertEqual(saved["summary"]["runs"], 1)
        out.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
