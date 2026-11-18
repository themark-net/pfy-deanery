"""Live exec for pfy launch: local sources, exit passthrough, paid refusals.

Temp HOME, fake claude/ollama/grok binaries on PATH, loopback HTTP only.
No public network, no paid keys, no auto-pull, no real cloud calls.
Does not import test_pfy_launcher_p2 (that would double-count under discover).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import socket
import stat
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "pfy"


def _sha(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_exe(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _TagsHandler(BaseHTTPRequestHandler):
    models: ClassVar[list[str]] = []
    posts: ClassVar[list[str]] = []

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/api/tags":
            body = json.dumps({"models": [{"name": n} for n in self.models]}).encode()
        elif path in ("/v1/models", "/models"):
            body = json.dumps({"data": [{"id": n} for n in self.models]}).encode()
        elif path == "/health":
            body = b'{"status":"ok"}'
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        _TagsHandler.posts.append(path + " " + raw.decode("utf-8", "replace")[:200])
        self.send_response(200)
        body = b'{"error":"tests must not pull or generate"}'
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


FAKE_HARNESS = """#!/usr/bin/env python3
import os
import signal
import sys

args = sys.argv[1:]
if "--exit" in args:
    raise SystemExit(int(args[args.index("--exit") + 1]))
if "--signal" in args:
    os.kill(os.getpid(), int(args[args.index("--signal") + 1]))
if "--read-stdin" in args:
    line = sys.stdin.readline()
    sys.stdout.write("STDIN:" + line)
    raise SystemExit(0)
sys.stdout.write("ARGV:" + json_dump(args) + "\\n")
raise SystemExit(0)
""".replace(
    "json_dump(args)",
    "__import__('json').dumps(args)",
)

FAKE_OLLAMA = """#!/usr/bin/env python3
import pathlib, sys
log = pathlib.Path(__file__).with_name("ollama-argv.log")
log.write_text("\\n".join(sys.argv[1:]))
if sys.argv[1:2] == ["launch"]:
    if "--help" in sys.argv or "-h" in sys.argv:
        print("ollama launch")
        raise SystemExit(0)
    print("OLLAMA_LAUNCH:" + " ".join(sys.argv[1:]))
    if "--exit" in sys.argv:
        raise SystemExit(int(sys.argv[sys.argv.index("--exit") + 1]))
    raise SystemExit(0)
if sys.argv[1:2] == ["pull"]:
    print("unexpected pull", file=sys.stderr)
    raise SystemExit(99)
raise SystemExit(0)
"""


class LaunchLiveExec(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.home = Path(tempfile.mkdtemp(prefix="pfy-launcher-live-"))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.bindir = self.home / "bin"
        self.bindir.mkdir()
        self.claude = self.home / ".claude.json"
        self.claude_dir = self.home / ".claude"
        self.claude_dir.mkdir()
        self.claude.write_text("{}\n")
        _TagsHandler.models = ["qwen3.6:35b"]
        _TagsHandler.posts = []
        self.servers: list[HTTPServer] = []
        _write_exe(self.bindir / "claude", FAKE_HARNESS)
        _write_exe(self.bindir / "grok", FAKE_HARNESS)
        _write_exe(self.bindir / "cursor-agent", FAKE_HARNESS)
        _write_exe(self.bindir / "hermes", FAKE_HARNESS)
        _write_exe(self.bindir / "gemini", FAKE_HARNESS)
        self.install_ollama(has_launch=False)

    def tearDown(self) -> None:
        for server in self.servers:
            server.shutdown()
            server.server_close()
        self.servers = []

    def start_http(self, models: list[str] | None = None) -> str:
        if models is not None:
            _TagsHandler.models = list(models)
        port = _free_port()
        server = HTTPServer(("127.0.0.1", port), _TagsHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.servers.append(server)
        return f"127.0.0.1:{port}"

    def env(self, *, ollama_host: str, **extra: str) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["PATH"] = str(self.bindir) + os.pathsep + "/usr/bin:/bin"
        env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        env["XDG_STATE_HOME"] = str(self.home / ".local" / "state")
        env["PFY_ROOT"] = str(ROOT)
        env["OLLAMA_HOST"] = ollama_host
        for key in (
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
            "OPENAI_API_KEY",
            "XAI_API_KEY",
            "CURSOR_API_KEY",
            "CURSOR_AUTH_TOKEN",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "PFY_TEST_OPENAI_BASE",
            "PFY_LOCAL_RUNTIME",
            "LITELLM_BASE_URL",
            "LITELLM_PROXY_API_BASE",
            "PFY_LAUNCH_ISTTY",
        ):
            env.pop(key, None)
        env["PFY_DETECT_SKIP_HOST"] = "1"
        env.update(extra)
        return env

    def install_ollama(self, *, has_launch: bool) -> None:
        launch = (
            "if sys.argv[1:2] == ['launch']:\n"
            "    if '--help' in sys.argv or '-h' in sys.argv:\n"
            "        print('ollama launch')\n"
            "        raise SystemExit(0)\n"
            "    print('OLLAMA_LAUNCH:' + ' '.join(sys.argv[1:]))\n"
            "    if '--exit' in sys.argv:\n"
            "        raise SystemExit(int(sys.argv[sys.argv.index('--exit') + 1]))\n"
            "    raise SystemExit(0)\n"
            if has_launch
            else "if sys.argv[1:2] == ['launch']:\n    raise SystemExit(2)\n"
        )
        _write_exe(
            self.bindir / "ollama",
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "pathlib.Path(__file__).with_name('ollama-argv.log').write_text('\\n'.join(sys.argv[1:]))\n"
            + launch
            + "if sys.argv[1:2] == ['pull']:\n"
            "    print('unexpected pull', file=sys.stderr)\n"
            "    raise SystemExit(99)\n"
            "raise SystemExit(0)\n",
        )


    def run_pfy(
        self,
        *args: str,
        ollama_host: str,
        stdin: str | None = None,
        **extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PFY), *args],
            cwd=str(ROOT),
            env=self.env(ollama_host=ollama_host, **extra),
            input=stdin,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_exit_code_passthrough_0_3_42(self) -> None:
        host = self.start_http(["qwen3.6:35b"])
        for code in (0, 3, 42):
            with self.subTest(code=code):
                proc = self.run_pfy(
                    "launch",
                    "claude-code",
                    "--model",
                    "ollama:qwen3.6:35b",
                    "--yes",
                    "--",
                    "--exit",
                    str(code),
                    ollama_host=host,
                )
                self.assertEqual(proc.returncode, code, proc.stderr + proc.stdout)
                self.assertNotIn("live exec is not in this Phase 3 slice", proc.stdout + proc.stderr)

    def test_signal_exit_is_128_plus_n(self) -> None:
        host = self.start_http(["qwen3.6:35b"])
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--",
            "--signal",
            str(int(signal.SIGTERM)),
            ollama_host=host,
        )
        self.assertEqual(proc.returncode, 128 + int(signal.SIGTERM), proc.stderr + proc.stdout)

    def test_args_after_dashdash_pass_through_literally(self) -> None:
        host = self.start_http(["qwen3.6:35b"])
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--",
            "--quiet",
            "$(echo pwned)",
            "$HOME",
            "arg with spaces",
            ollama_host=host,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        # Child owns stdout: plan JSON must not precede the harness output.
        self.assertIn("ARGV:", proc.stdout)
        rec = json.loads(proc.stdout.split("ARGV:", 1)[1].strip())
        self.assertEqual(rec, ["--quiet", "$(echo pwned)", "$HOME", "arg with spaces"])
        self.assertNotIn("pwned\n", proc.stdout)
        self.assertNotIn(str(self.home), rec)

    def test_stdin_is_inherited(self) -> None:
        host = self.start_http(["qwen3.6:35b"])
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--",
            "--read-stdin",
            ollama_host=host,
            stdin="hello from parent\n",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(proc.stdout, "STDIN:hello from parent\n")

    def test_paid_source_is_refused_and_does_not_exec(self) -> None:
        host = self.start_http(["qwen3.6:35b"])
        before = _sha(self.claude)
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "anthropic:claude-3-5-sonnet",
            "--yes",
            ollama_host=host,
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("paid", text)
        self.assertNotIn("ARGV:", proc.stdout)
        self.assertEqual(_TagsHandler.posts, [])
        self.assertEqual(_sha(self.claude), before)

    def test_cursor_api_key_passthrough_is_refused_on_live_path(self) -> None:
        host = self.start_http(["qwen3.6:35b"])
        proc = self.run_pfy(
            "launch",
            "cursor",
            "--yes",
            "--",
            "--api-key",
            "placeholder",
            ollama_host=host,
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = proc.stdout + proc.stderr
        self.assertIn("api-key", text.lower().replace("_", "-"))
        self.assertNotIn("placeholder", text)
        self.assertNotIn("ARGV:", proc.stdout)

    def test_missing_binary_is_a_clear_error(self) -> None:
        host = self.start_http(["qwen3.6:35b"])
        (self.bindir / "claude").unlink()
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            ollama_host=host,
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = (proc.stdout + proc.stderr).lower()
        self.assertTrue("not on path" in text or "not found" in text, text)
        self.assertIn("claude", text)
        self.assertNotIn("live exec is not in this Phase 3 slice", text)

    def test_model_not_pulled_is_a_clear_error_and_does_not_pull(self) -> None:
        host = self.start_http([])  # daemon up, empty tag list
        ollama_log = self.bindir / "ollama-argv.log"
        if ollama_log.exists():
            ollama_log.unlink()
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            ollama_host=host,
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = proc.stdout + proc.stderr
        self.assertIn("qwen3.6:35b", text)
        self.assertTrue("not pulled" in text.lower() or "is not pulled" in text.lower(), text)
        self.assertIn("will not pull", text.lower())
        self.assertFalse(any("/api/pull" in p for p in _TagsHandler.posts), _TagsHandler.posts)
        if ollama_log.exists():
            self.assertNotIn("pull", ollama_log.read_text())
        self.assertNotIn("ARGV:", proc.stdout)

    def test_dry_run_json_is_unchanged_and_does_not_exec(self) -> None:
        host = self.start_http(["qwen3.6:35b"])
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "--quiet",
            ollama_host=host,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertTrue(rec["dry_run"])
        self.assertEqual(rec["harness"], "claude-code")
        self.assertEqual(rec["model"], "ollama:qwen3.6:35b")
        self.assertEqual(rec["argv"][-1], "--quiet")
        self.assertNotIn("ARGV:", proc.stdout)
        self.assertEqual(_TagsHandler.posts, [])

    def test_grok_live_exec_passes_exit_and_args(self) -> None:
        host = self.start_http(["qwen3.6:35b"])
        proc = self.run_pfy(
            "launch",
            "grok",
            "--yes",
            "--",
            "--exit",
            "42",
            ollama_host=host,
        )
        self.assertEqual(proc.returncode, 42, proc.stderr + proc.stdout)


if __name__ == "__main__":
    unittest.main()
