"""The version probe writes a receipt only after HTTP 200 on origin/main.

Failure leaves the destination bytes alone and does not open a second URL.
Recovery is a nonzero exit and no receipt file.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "ollama" / "run-on-main.sh"
LOCK = ROOT / "scripts" / "model_lock.sh"
PROBE = "http://127.0.0.1:11434/api/version"


def git(repo: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout or "git failed")


def init_main_repo(repo: Path) -> None:
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main", str(repo)],
        check=True,
        capture_output=True,
        text=True,
    )
    git(repo, "config", "user.email", "lane@example.com")
    git(repo, "config", "user.name", "Lane")
    git(repo, "commit", "--allow-empty", "-m", "base")
    bare = repo.parent / "origin.git"
    subprocess.run(
        ["git", "init", "--bare", "-b", "main", str(bare)],
        check=True,
        capture_output=True,
        text=True,
    )
    git(repo, "remote", "add", "origin", str(bare))
    git(repo, "push", "-u", "origin", "main")


def install_probe(repo: Path, url: str) -> Path:
    text = SCRIPT.read_text(encoding="utf-8")
    if PROBE not in text:
        raise AssertionError("probe URL missing from run-on-main.sh")
    text = text.replace(PROBE, url)
    if "11434" in text:
        raise AssertionError("fixture script still names port 11434")
    dest = repo / "eval" / "integrate" / "ollama" / "run-on-main.sh"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    dest.chmod(0o755)
    lock = repo / "scripts" / "model_lock.sh"
    lock.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(LOCK, lock)
    lock.chmod(0o755)
    return dest


def run_probe(script: Path, repo: Path, dest: Path, lock: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PFY_MODEL_LOCK"] = str(lock)
    env.pop("PFY_MODEL_LOCK_HELD", None)
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        ["bash", str(script), str(dest)],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=12,
    )


class _Quiet(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        return


def serve(handler: type[BaseHTTPRequestHandler]) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def stop(server: ThreadingHTTPServer) -> None:
    server.shutdown()
    server.server_close()


class OllamaRunOnMainFailTest(unittest.TestCase):
    def test_this_worktree_is_not_a_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            dest = td / "receipt.json"
            dest.write_text("keep\n", encoding="utf-8")
            lock = td / "model.lock"
            proc = run_probe(SCRIPT, ROOT, dest, lock)
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            self.assertIn("not an ancestor", proc.stderr)
            self.assertEqual(dest.read_text(encoding="utf-8"), "keep\n")
            self.assertFalse(lock.exists(), proc.stderr)

    def test_usage_exits_2(self) -> None:
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_ancestor_http_200_writes_one_line_version(self) -> None:
        body = b'{"version":"0.30.8\\nsekret","token":"sekret"}\n'
        hits: list[str] = []

        class Handler(_Quiet):
            def do_GET(self) -> None:
                hits.append(self.path)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = serve(Handler)
        self.addCleanup(stop, server)
        port = server.server_address[1]
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = td / "repo"
            init_main_repo(repo)
            script = install_probe(repo, "http://127.0.0.1:%s/api/version" % port)
            dest = td / "receipt.json"
            proc = run_probe(script, repo, dest, td / "model.lock")
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertEqual(hits, ["/api/version"])
            got = json.loads(dest.read_text(encoding="utf-8"))
            head = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
            ).strip()
            self.assertEqual(got["slug"], "ollama")
            self.assertEqual(got["run_kind"], "pipeline")
            self.assertEqual(got["main_sha"], head)
            self.assertEqual(len(got["main_sha"]), 40)
            self.assertEqual(got["outcome"], "ok")
            self.assertEqual(got["tool_version"], "0.30.8")
            self.assertTrue(got["run_id"])
            self.assertTrue(got["started"])
            self.assertTrue(got["finished"])
            self.assertIn("HTTP 200", got["did"])
            self.assertNotIn("sekret", dest.read_text(encoding="utf-8"))
            self.assertTrue((td / "model.lock").exists())

    def test_empty_version_still_records_http_200(self) -> None:
        class Handler(_Quiet):
            def do_GET(self) -> None:
                raw = b'{"version":""}'
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        server = serve(Handler)
        self.addCleanup(stop, server)
        port = server.server_address[1]
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = td / "repo"
            init_main_repo(repo)
            script = install_probe(repo, "http://127.0.0.1:%s/api/version" % port)
            dest = td / "receipt.json"
            proc = run_probe(script, repo, dest, td / "model.lock")
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            got = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(got["tool_version"], "unknown")

    def test_ahead_of_main_does_not_connect(self) -> None:
        hits: list[str] = []

        class Handler(_Quiet):
            def do_GET(self) -> None:
                hits.append(self.path)
                self.send_response(200)
                self.end_headers()

        server = serve(Handler)
        self.addCleanup(stop, server)
        port = server.server_address[1]
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = td / "repo"
            init_main_repo(repo)
            git(repo, "commit", "--allow-empty", "-m", "ahead")
            script = install_probe(repo, "http://127.0.0.1:%s/api/version" % port)
            dest = td / "receipt.json"
            dest.write_text("keep\n", encoding="utf-8")
            proc = run_probe(script, repo, dest, td / "model.lock")
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            self.assertEqual(dest.read_text(encoding="utf-8"), "keep\n")
            self.assertEqual(hits, [])
            self.assertFalse((td / "model.lock").exists())

    def test_refused_http_error_and_redirect_write_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = td / "repo"
            init_main_repo(repo)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                closed = sock.getsockname()[1]
            script = install_probe(repo, "http://127.0.0.1:%s/api/version" % closed)
            dest = td / "receipt.json"
            dest.write_text("keep\n", encoding="utf-8")
            proc = run_probe(script, repo, dest, td / "refused.lock")
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            self.assertEqual(dest.read_text(encoding="utf-8"), "keep\n")

        class Denied(_Quiet):
            def do_GET(self) -> None:
                self.send_response(500)
                self.end_headers()

        denied = serve(Denied)
        self.addCleanup(stop, denied)
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = td / "repo"
            init_main_repo(repo)
            script = install_probe(
                repo, "http://127.0.0.1:%s/api/version" % denied.server_address[1]
            )
            dest = td / "receipt.json"
            proc = run_probe(script, repo, dest, td / "denied.lock")
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            self.assertFalse(dest.exists())

        second_hits: list[str] = []

        class Second(_Quiet):
            def do_GET(self) -> None:
                second_hits.append(self.path)
                raw = b'{"version":"9.9.9"}'
                self.send_response(200)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

        second = serve(Second)
        self.addCleanup(stop, second)
        target = "http://127.0.0.1:%s/api/version" % second.server_address[1]

        class Redirect(_Quiet):
            def do_GET(self) -> None:
                self.send_response(302)
                self.send_header("Location", target)
                self.end_headers()

        first = serve(Redirect)
        self.addCleanup(stop, first)
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = td / "repo"
            init_main_repo(repo)
            script = install_probe(
                repo, "http://127.0.0.1:%s/api/version" % first.server_address[1]
            )
            dest = td / "receipt.json"
            proc = run_probe(script, repo, dest, td / "redirect.lock")
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            self.assertFalse(dest.exists())
            self.assertEqual(second_hits, [])

    def test_timeout_is_not_a_pass(self) -> None:
        class Hang(_Quiet):
            def do_GET(self) -> None:
                time.sleep(20)

        server = serve(Hang)
        self.addCleanup(stop, server)
        port = server.server_address[1]
        with tempfile.TemporaryDirectory() as raw:
            td = Path(raw)
            repo = td / "repo"
            init_main_repo(repo)
            script = install_probe(repo, "http://127.0.0.1:%s/api/version" % port)
            dest = td / "receipt.json"
            started = time.monotonic()
            proc = run_probe(script, repo, dest, td / "model.lock")
            elapsed = time.monotonic() - started
            self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
            self.assertFalse(dest.exists())
            self.assertGreater(elapsed, 3)
            self.assertLess(elapsed, 12)


if __name__ == "__main__":
    unittest.main()
