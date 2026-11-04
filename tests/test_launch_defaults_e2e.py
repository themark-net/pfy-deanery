"""One-command ./pfy launch fills wizard defaults. Real CLI, temp HOME.

Does not open a window, touch ~/.pfy-mentat, or the host Ollama on
127.0.0.1:11434. DISPLAY is unset so the terminal step FAILs; the
review state is what must be complete.
"""
from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import textwrap
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "pfy"
INSTALL_HINT = "curl -fsSL https://x.ai/cli/install.sh | bash"
HOST_PORTS = (11434, 11435, 1919, 8080, 9292)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b'{"data":[{"id":"tiny-test"}]}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


def _closed_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    path.chmod(0o755)


def _last_json(text: str) -> dict:
    for line in reversed((text or "").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            return json.loads(line)
    raise AssertionError("no JSON in output:\n" + text)


class LaunchDefaultsE2E(unittest.TestCase):
    def setUp(self):
        self.home = Path(self._tmp())
        self.state = self.home / "state"
        self.state.mkdir()
        self.bindir = self.home / "bin"
        self.realbin = self.home / "real"
        self.realbin.mkdir()
        self.block_log = self.home / "curl-blocked"
        self._server = None
        self.addCleanup(self._stop_server)
        # Host PATH may contain grok, claude, codex, or an engine. Mirror
        # /bin and /usr/bin without those so "ready" means the fake binaries.
        hidden = {
            "ollama",
            "ft",
            "freetoken",
            "llama-server",
            "llama-swap",
            "shimmy",
            "grok",
            "opencode",
            "opencode-cli",
            "hermes",
            "hermes-agent",
            "claude",
            "codex",
            "gemini",
            "gemini-cli",
            "exo.sh",
            "gab",
        }
        for base in ("/bin", "/usr/bin"):
            if not os.path.isdir(base):
                continue
            for name in os.listdir(base):
                if name in hidden or (self.realbin / name).exists():
                    continue
                src = os.path.join(base, name)
                if os.path.isfile(src) and os.access(src, os.X_OK):
                    os.symlink(src, self.realbin / name)
        _exe(
            self.bindir / "curl",
            f"""\
            #!/bin/bash
            url=""
            for a in "$@"; do
              case "$a" in
                http://*|https://*) url="$a" ;;
              esac
            done
            case "$url" in
              *127.0.0.1:11434*|*localhost:11434*|*127.0.0.1:11435*|*127.0.0.1:1919*|*127.0.0.1:8080*|*127.0.0.1:9292*)
                printf '%s\\n' "$url" >> "{self.block_log}"
                exit 1
                ;;
            esac
            exec /usr/bin/curl "$@"
            """,
        )

    def _tmp(self) -> str:
        import tempfile

        parent = ROOT / "tmp"
        parent.mkdir(parents=True, exist_ok=True)
        path = tempfile.mkdtemp(prefix="pfy-launch-", dir=str(parent))
        self.addCleanup(self._rm, path)
        return path

    @staticmethod
    def _rm(path: str) -> None:
        import shutil

        shutil.rmtree(path, ignore_errors=True)

    def _stop_server(self):
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()

    def _serve(self) -> str:
        srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._server = srv
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return "http://127.0.0.1:%d" % srv.server_address[1]

    def _env(self, **extra) -> dict:
        env = os.environ.copy()
        for key in (
            "PFY_START_ENGINE",
            "PFY_START_ENGINE_FLAG",
            "PFY_LOCAL_RUNTIME",
            "DISPLAY",
            "WAYLAND_DISPLAY",
            "XAI_API_KEY",
        ):
            env.pop(key, None)
        env.update(
            {
                "HOME": str(self.home),
                "PFY_STATE_DIR": str(self.state),
                "PATH": "%s:%s" % (self.bindir, self.realbin),
                "TMPDIR": str(ROOT / "tmp"),
                "PFY_SKIP_WINDOW": "1",
                "PFY_SKIP_STAGE": "1",
                "PFY_DETECT_SKIP_HOST": "1",
                "PFY_OLLAMA_BASE": "http://127.0.0.1:%d" % _closed_port(),
            }
        )
        env.update(extra)
        return env

    def _run(self, args, env=None):
        proc = subprocess.Popen(
            [str(PFY), *args],
            cwd=str(ROOT),
            env=env or self._env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            start_new_session=True,
        )
        try:
            out, err = proc.communicate(timeout=60)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                out, err = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                out, err = proc.communicate()
            raise subprocess.TimeoutExpired(proc.args, 60, output=out, stderr=err)
        return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)

    def _harness(self, name: str) -> None:
        _exe(self.bindir / name, "#!/bin/sh\nexit 0\n")

    def _assert_no_host_ollama(self):
        if not self.block_log.is_file():
            return
        text = self.block_log.read_text(encoding="utf-8")
        for port in HOST_PORTS:
            self.assertNotIn(":%d" % port, text, text)

    def test_fresh_launch_fills_defaults_and_review_matches(self):
        base = self._serve()
        self._harness("grok")
        env = self._env(LOCAL_OPENAI_BASE_URL=base)
        launched = self._run(["launch"], env)
        self._assert_no_host_ollama()
        blob = launched.stdout + launched.stderr
        self.assertIn("defaults: lane local, toolsets bare, harness grok", blob)
        self.assertEqual(launched.returncode, 2, blob)
        state = json.loads((self.state / "launch-wizard.json").read_text(encoding="utf-8"))
        self.assertEqual(state["lane"], "local")
        self.assertEqual(state["toolsets"], "bare")
        self.assertEqual(state["harness"], "grok")
        self.assertIn("ready", state["runtime"])
        reviewed = self._run(["launch", "review"], env)
        self.assertEqual(reviewed.returncode, 0, reviewed.stdout + reviewed.stderr)
        launch_doc = _last_json(launched.stdout)
        review_doc = _last_json(reviewed.stdout)
        self.assertEqual(launch_doc.get("review"), review_doc.get("review"))
        review = review_doc["review"]
        self.assertIn("lane local", review)
        self.assertIn("toolsets bare", review)
        self.assertIn("harness grok", review)
        self.assertIn(state["runtime"], review)

    def test_explicit_harness_is_kept(self):
        base = self._serve()
        self._harness("grok")
        self._harness("opencode")
        env = self._env(LOCAL_OPENAI_BASE_URL=base)
        for args in (
            ["launch", "lane", "local"],
            ["launch", "toolset", "bare"],
            ["launch", "harness", "opencode"],
        ):
            proc = self._run(args, env)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        launched = self._run(["launch"], env)
        self._assert_no_host_ollama()
        blob = launched.stdout + launched.stderr
        self.assertNotIn("harness grok", blob)
        reviewed = self._run(["launch", "review"], env)
        self.assertEqual(reviewed.returncode, 0, reviewed.stdout + reviewed.stderr)
        review = _last_json(reviewed.stdout)["review"]
        self.assertIn("lane local", review)
        self.assertIn("toolsets bare", review)
        self.assertIn("harness opencode", review)
        state = json.loads((self.state / "launch-wizard.json").read_text(encoding="utf-8"))
        self.assertEqual(state["harness"], "opencode")

    def test_no_ready_engine_exits_2_with_next_step(self):
        closed = "http://127.0.0.1:%d" % _closed_port()
        self._harness("grok")
        env = self._env(LOCAL_OPENAI_BASE_URL=closed)
        proc = self._run(["launch"], env)
        self._assert_no_host_ollama()
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 2, blob)
        doc = _last_json(proc.stdout)
        self.assertTrue(doc.get("next_step"), blob)
        self.assertIn("next", blob.lower())
        state_path = self.state / "launch-wizard.json"
        if state_path.is_file():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertFalse(str(state.get("harness") or "").strip(), state)

    def test_no_ready_harness_fails_with_install_hint(self):
        base = self._serve()
        env = self._env(LOCAL_OPENAI_BASE_URL=base)
        proc = self._run(["launch"], env)
        self._assert_no_host_ollama()
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 2, blob)
        self.assertIn(INSTALL_HINT, blob)
        state_path = self.state / "launch-wizard.json"
        if state_path.is_file():
            state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertFalse(str(state.get("harness") or "").strip(), state)

    def test_active_ready_harness_beats_grok(self):
        base = self._serve()
        self._harness("grok")
        self._harness("opencode")
        (self.state / "active-harness").write_text("opencode\n", encoding="utf-8")
        env = self._env(LOCAL_OPENAI_BASE_URL=base)
        launched = self._run(["launch"], env)
        blob = launched.stdout + launched.stderr
        self.assertIn("defaults: lane local, toolsets bare, harness opencode", blob)
        self.assertNotIn("harness grok", blob)
        state = json.loads((self.state / "launch-wizard.json").read_text(encoding="utf-8"))
        self.assertEqual(state["harness"], "opencode")

    def test_active_missing_falls_through_to_grok(self):
        base = self._serve()
        self._harness("grok")
        (self.state / "active-harness").write_text("hermes\n", encoding="utf-8")
        env = self._env(LOCAL_OPENAI_BASE_URL=base)
        launched = self._run(["launch"], env)
        blob = launched.stdout + launched.stderr
        self.assertIn("defaults: lane local, toolsets bare, harness grok", blob)
        state = json.loads((self.state / "launch-wizard.json").read_text(encoding="utf-8"))
        self.assertEqual(state["harness"], "grok")

    def test_first_ready_harness_when_grok_is_missing(self):
        base = self._serve()
        self._harness("opencode")
        env = self._env(LOCAL_OPENAI_BASE_URL=base)
        launched = self._run(["launch"], env)
        blob = launched.stdout + launched.stderr
        self.assertIn("defaults: lane local, toolsets bare, harness opencode", blob)
        self.assertNotIn(INSTALL_HINT, blob)
        state = json.loads((self.state / "launch-wizard.json").read_text(encoding="utf-8"))
        self.assertEqual(state["harness"], "opencode")


if __name__ == "__main__":
    unittest.main()
