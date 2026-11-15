"""--local reviews with Ollama at $0 and does not start grok.

Fail: the command has no local choice, so a review is grok or nothing.
Recover: --local writes the report from a local generate endpoint, the
fake grok log stays empty, and a non-local endpoint does not connect.
Omit --local to return to the priced grok gate.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "egm_review.py"

FAKE = textwrap.dedent(
    """\
    #!/usr/bin/env python3
    import os, sys
    log = os.environ.get("EGM_FAKE_LOG")
    if log:
        open(log, "a", encoding="utf-8").write("called\\n")
    sys.stderr.write("fake grok should not run\\n")
    raise SystemExit(9)
    """
)


class _Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n).decode("utf-8"))
        prompt = body.get("prompt") or ""
        self.server.models.append(body.get("model"))
        if "You are the Elephant" in prompt:
            payload = {"spec": "Problem\n\nELEPHANT_SPEC_MARKER\n", "unstated": ["directory mode"]}
        else:
            persona = "readiness" if "Persona: readiness" in prompt else "critic"
            payload = {
                "findings": [{
                    "severity": "Major",
                    "scope": persona,
                    "finding": "mode is not stated",
                }]
            }
        raw = json.dumps({"response": json.dumps(payload)}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, fmt: str, *args) -> None:
        return


class EgmLocalChoiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="egm-local-"))
        self.fake = self.root / "fake-grok.py"
        self.fake.write_text(FAKE, encoding="utf-8")
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IEXEC)
        self.log = self.root / "calls.txt"
        self.ticket = self.root / "ticket.md"
        self.cited = self.root / "cited.md"
        self.out = self.root / "report.json"
        self.scratch = self.root / "scratch"
        self.ticket.write_text("Do the ticket.\n", encoding="utf-8")
        self.cited.write_text("cited line\n", encoding="utf-8")
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.httpd.models = []
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.httpd.server_address
        self.local_url = "http://%s:%s/api/generate" % (host, port)

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        import shutil

        shutil.rmtree(self.root, ignore_errors=True)

    def run_review(self, extra=None, env_extra=None, timeout=20):
        env = os.environ.copy()
        env["PFY_GROK_BIN"] = str(self.fake)
        env["EGM_FAKE_LOG"] = str(self.log)
        env["PFY_EGM_LOCAL_URL"] = self.local_url
        if env_extra:
            env.update(env_extra)
        argv = [
            sys.executable,
            str(SCRIPT),
            "--ticket",
            str(self.ticket),
            "--cited",
            str(self.cited),
            "--out",
            str(self.out),
            "--scratch",
            str(self.scratch),
            "--personas",
            "readiness,critic",
        ]
        if extra:
            argv.extend(extra)
        return subprocess.run(
            argv,
            cwd=self.root,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def test_local_flag_reviews_at_zero_and_does_not_start_grok(self) -> None:
        proc = self.run_review(extra=["--local"])
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertFalse(self.log.exists(), blob)
        self.assertIn("$0", blob)
        self.assertIn("qwen3.6:35b", blob)
        self.assertIn("grok-4.7", blob)
        self.assertNotIn("fake grok should not run", blob)
        report = json.loads(self.out.read_text(encoding="utf-8"))
        self.assertTrue(report["ok"], report)
        self.assertIn("ELEPHANT_SPEC_MARKER", report["elephant"]["spec"])
        self.assertEqual([row["persona"] for row in report["goldfish"]], ["readiness", "critic"])
        self.assertEqual(self.httpd.models, ["qwen3.6:35b", "qwen3.6:35b", "qwen3.6:35b"])

        if self.out.exists():
            self.out.unlink()
        down = self.run_review(
            extra=["--local"],
            env_extra={"PFY_EGM_LOCAL_URL": "http://127.0.0.1:9/api/generate"},
        )
        blob = down.stdout + down.stderr
        self.assertEqual(down.returncode, 2, blob)
        self.assertFalse(self.log.exists(), blob)
        self.assertIn("grok was not started", blob)
        self.assertIn("next step:", blob)

        if self.out.exists():
            self.out.unlink()
        public = self.run_review(
            extra=["--local"],
            env_extra={"PFY_EGM_LOCAL_URL": "http://203.0.113.9/api/generate"},
            timeout=10,
        )
        blob = public.stdout + public.stderr
        self.assertEqual(public.returncode, 2, blob)
        self.assertFalse(self.log.exists(), blob)
        self.assertIn("not a local host", blob)
        self.assertIn("No model was called", blob)
        self.assertEqual(len(self.httpd.models), 3)


if __name__ == "__main__":
    unittest.main()
