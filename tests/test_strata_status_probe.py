import json
import os
import pathlib
import subprocess
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "strata" / "run-on-main.sh"
SENTINEL = "strata-status-test-key"
DECOY = "prompt-tail-should-stay-on-server"


class StrataStatusProbeTest(unittest.TestCase):
    def test_status_request_does_not_start_or_download(self):
        text = SCRIPT.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("PFY_STRATA_BASE", text)
        self.assertIn("status", lowered)
        self.assertNotIn("ollama pull", lowered)
        self.assertNotIn("systemctl", lowered)
        for banned in ("strata serve", "download weights", "wget ", "curl -o"):
            self.assertNotIn(banned, lowered)

    def test_timeout_is_not_a_pass_and_generate_is_locked(self):
        text = SCRIPT.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("timeout", lowered)
        generate_at = lowered.find("generate")
        if generate_at >= 0:
            window = lowered[max(0, generate_at - 400): generate_at + 80]
            self.assertIn("model_lock.sh", window)

    def test_default_base_is_the_host_port(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("PFY_STRATA_BASE:-http://127.0.0.1:18158", text)
        self.assertNotIn("8080", text)

    def test_closed_port_and_foreign_host_write_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = _ancestor_repo(pathlib.Path(raw))
            receipt = repo / "receipt.json"
            closed = _run(
                repo,
                receipt,
                _env(repo, PFY_STRATA_BASE="http://127.0.0.1:1", PFY_STRATA_TIMEOUT="2"),
            )
            self.assertNotEqual(closed.returncode, 0, closed.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("no receipt", closed.stderr)
            try:
                foreign = _run(
                    repo,
                    receipt,
                    _env(repo, PFY_STRATA_BASE="http://192.0.2.1:9", PFY_STRATA_TIMEOUT="5"),
                    timeout=3,
                )
            except subprocess.TimeoutExpired:
                self.fail("non-loopback status probe did not fail closed")
            self.assertNotEqual(foreign.returncode, 0, foreign.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("no receipt", foreign.stderr)

    def test_timeout_redirect_and_other_service_write_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = _ancestor_repo(pathlib.Path(raw))
            receipt = repo / "receipt.json"
            with _listening(hang=True) as (port, _seen):
                timed = _run(
                    repo,
                    receipt,
                    _env(
                        repo,
                        PFY_STRATA_BASE=f"http://127.0.0.1:{port}",
                        PFY_STRATA_TIMEOUT="1",
                    ),
                    timeout=8,
                )
            self.assertNotEqual(timed.returncode, 0, timed.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("no receipt", timed.stderr)
            with _listening(location="http://192.0.2.1/v1/status") as (port, _seen):
                try:
                    bounced = _run(
                        repo,
                        receipt,
                        _env(
                            repo,
                            PFY_STRATA_BASE=f"http://127.0.0.1:{port}",
                            PFY_STRATA_TIMEOUT="5",
                            PFY_STRATA_API_KEY=SENTINEL,
                        ),
                        timeout=3,
                    )
                except subprocess.TimeoutExpired:
                    self.fail("redirect was followed")
            self.assertNotEqual(bounced.returncode, 0, bounced.stderr)
            self.assertFalse(receipt.exists())
            body = json.dumps(
                {"service": "other", "loaded": True, "engine": "0.1.58", "secret": DECOY}
            ).encode()
            with _listening(body=body) as (port, seen):
                other = _run(
                    repo,
                    receipt,
                    _env(repo, PFY_STRATA_BASE=f"http://127.0.0.1:{port}/v1"),
                )
            self.assertNotEqual(other.returncode, 0, other.stderr)
            self.assertFalse(receipt.exists())
            self.assertEqual(seen.get("method"), "GET")
            self.assertEqual(seen.get("path"), "/v1/status")
            self.assertEqual(list(receipt.parent.glob(".receipt.*")), [])

    def test_status_receipt_keeps_the_key_and_the_body_out(self):
        body = json.dumps(
            {
                "service": "strata",
                "loaded": True,
                "engine": "0.1.58",
                "secret": DECOY,
            }
        ).encode()
        with tempfile.TemporaryDirectory() as raw:
            repo = _ancestor_repo(pathlib.Path(raw))
            receipt = repo / "receipt.json"
            with _listening(body=body) as (port, seen):
                proc = _run(
                    repo,
                    receipt,
                    _env(
                        repo,
                        PFY_STRATA_BASE=f"http://127.0.0.1:{port}/v1",
                        PFY_STRATA_API_KEY=SENTINEL,
                    ),
                )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            text = receipt.read_text(encoding="utf-8")
            doc = json.loads(text)
            sha = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            self.assertEqual(doc["slug"], "strata")
            self.assertEqual(doc["run_kind"], "pipeline")
            self.assertEqual(doc["outcome"], "ok")
            self.assertEqual(doc["main_sha"], sha)
            self.assertRegex(doc["main_sha"], r"^[0-9a-f]{40}$")
            self.assertTrue(doc["run_id"])
            self.assertTrue(doc["started"])
            self.assertTrue(doc["finished"])
            self.assertEqual(doc["tool_version"], "0.1.58")
            self.assertIn("loaded=true", doc["did"])
            self.assertNotIn(SENTINEL, text)
            self.assertNotIn(DECOY, text)
            self.assertEqual(seen.get("method"), "GET")
            self.assertEqual(seen.get("path"), "/v1/status")
            self.assertEqual(seen.get("auth"), "Bearer " + SENTINEL)
            self.assertEqual(list(receipt.parent.glob(".receipt.*")), [])

            echoed = json.dumps(
                {"service": "strata", "loaded": False, "engine": SENTINEL}
            ).encode()
            echoed_path = repo / "echoed.json"
            with _listening(body=echoed) as (port, _seen):
                again = _run(
                    repo,
                    echoed_path,
                    _env(
                        repo,
                        PFY_STRATA_BASE=f"http://127.0.0.1:{port}",
                        PFY_STRATA_API_KEY=SENTINEL,
                    ),
                )
            self.assertEqual(again.returncode, 0, again.stderr)
            echoed_text = echoed_path.read_text(encoding="utf-8")
            echoed_doc = json.loads(echoed_text)
            self.assertEqual(echoed_doc["tool_version"], "strata")
            self.assertIn("loaded=false", echoed_doc["did"])
            self.assertNotIn(SENTINEL, echoed_text)


def _git(repo, *args):
    subprocess.check_call(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=lane@example.com",
            "-c",
            "user.name=lane",
            "-c",
            "commit.gpgsign=false",
            *args,
        ],
        stdout=subprocess.DEVNULL,
    )


def _ancestor_repo(tmp):
    repo = tmp / "repo"
    dest = repo / "eval" / "integrate" / "strata"
    dest.mkdir(parents=True)
    (dest / "run-on-main.sh").write_bytes(SCRIPT.read_bytes())
    (repo / "README").write_text("fixture\n", encoding="utf-8")
    subprocess.check_call(["git", "init", "-q"], cwd=repo)
    _git(repo, "add", "README")
    _git(repo, "commit", "-qm", "fixture")
    subprocess.check_call(
        ["git", "-C", str(repo), "update-ref", "refs/remotes/origin/main", "HEAD"]
    )
    return repo


def _env(repo, **extra):
    env = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "PFY_STRATA_BASE",
        "PFY_STRATA_TIMEOUT",
        "PFY_STRATA_API_KEY",
        "STRATA_API_KEY",
        "PFY_STRATA_LANE_MARKER",
        "PFY_STRATA_STATUS_URL",
    ):
        env.pop(key, None)
    env["PFY_STRATA_LANE_MARKER"] = str(repo / "missing-marker")
    env.update(extra)
    return env


def _run(repo, receipt, env, timeout=10):
    script = repo / "eval" / "integrate" / "strata" / "run-on-main.sh"
    return subprocess.run(
        ["bash", str(script), str(receipt)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@contextmanager
def _listening(body=None, location=None, hang=False):
    seen = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            seen["path"] = self.path.split("?", 1)[0]
            seen["method"] = "GET"
            seen["auth"] = self.headers.get("Authorization")
            if hang:
                time.sleep(30)
                return
            if location:
                self.send_response(302)
                self.send_header("Location", location)
                self.end_headers()
                return
            if seen["path"] != "/v1/status":
                self.send_response(404)
                self.end_headers()
                return
            payload = body if body is not None else b"{}"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self):
            seen["method"] = "POST"
            self.send_response(405)
            self.end_headers()

        def log_message(self, fmt, *args):
            return

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield httpd.server_address[1], seen
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    unittest.main()
