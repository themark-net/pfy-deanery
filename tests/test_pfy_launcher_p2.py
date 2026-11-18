"""Phase 2 first slice: pfy launch <harness> --model ollama:<tag> (docs/design/pfy-launcher.md §13).

Temp HOME, fake claude/ollama on PATH, local loopback probe only. No public
network, no paid keys, no harness-config writes.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import stat
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "pfy"

CLAUDE_JSON = (
    "{\n"
    '  "mcpServers": {\n'
    '    "other": {\n'
    '      "command": "keep-me"\n'
    "    }\n"
    "  }\n"
    "}\n"
)


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
    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] in ("/api/tags", "/v1/models"):
            body = b'{"models":[]}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


class LaunchP2(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.home = Path(tempfile.mkdtemp(prefix="pfy-launcher-p2-"))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.bindir = self.home / "bin"
        _write_exe(self.bindir / "claude", "#!/bin/sh\necho 'unexpected exec' >&2\nexit 99\n")
        self.claude = self.home / ".claude.json"
        self.claude_dir = self.home / ".claude"
        self.claude_dir.mkdir()
        self.claude.write_text(CLAUDE_JSON)
        self.httpd: HTTPServer | None = None

    def tearDown(self) -> None:
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None

    def start_ollama_http(self) -> str:
        port = _free_port()
        server = HTTPServer(("127.0.0.1", port), _TagsHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.httpd = server
        return f"127.0.0.1:{port}"

    def env(self, *, ollama_host: str, **extra: str) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["PATH"] = str(self.bindir) + os.pathsep + "/usr/bin:/bin"
        env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        env["XDG_STATE_HOME"] = str(self.home / ".local" / "state")
        env["PFY_ROOT"] = str(ROOT)
        env["OLLAMA_HOST"] = ollama_host
        env.pop("ANTHROPIC_API_KEY", None)
        env.pop("ANTHROPIC_AUTH_TOKEN", None)
        env.pop("OPENAI_API_KEY", None)
        env.update(extra)
        return env

    def install_ollama(self, *, has_launch: bool) -> None:
        launch_branch = (
            "if sys.argv[1:2] == ['launch']:\n"
            "    if '--help' in sys.argv or '-h' in sys.argv:\n"
            "        print('ollama launch')\n"
            "        raise SystemExit(0)\n"
            "    print('unexpected ollama launch exec', file=sys.stderr)\n"
            "    raise SystemExit(99)\n"
            if has_launch
            else "if sys.argv[1:2] == ['launch']:\n    raise SystemExit(2)\n"
        )
        _write_exe(
            self.bindir / "ollama",
            "#!/usr/bin/env python3\n"
            "import sys\n"
            f"{launch_branch}"
            "raise SystemExit(0)\n",
        )

    def run_pfy(self, *args: str, ollama_host: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PFY), *args],
            cwd=str(ROOT),
            env=self.env(ollama_host=ollama_host, **extra),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def test_dry_run_json_leaves_claude_config_unchanged(self) -> None:
        self.install_ollama(has_launch=False)
        host = self.start_ollama_http()
        before = _sha(self.claude)
        before_dir = {p: _sha(p) for p in self.claude_dir.rglob("*") if p.is_file()}
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host=host,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["harness"], "claude-code")
        self.assertEqual(rec["model"], "ollama:qwen3.6:35b")
        self.assertTrue(rec["dry_run"])
        self.assertEqual(rec.get("delegate"), "")
        self.assertEqual(rec["argv"][0], "claude")
        env = rec["env"]
        self.assertIn("ANTHROPIC_BASE_URL", env)
        self.assertTrue(env["ANTHROPIC_BASE_URL"].startswith("http://"))
        self.assertIn("ANTHROPIC_AUTH_TOKEN", env)
        self.assertEqual(_sha(self.claude), before)
        self.assertEqual({p: _sha(p) for p in self.claude_dir.rglob("*") if p.is_file()}, before_dir)

    def test_delegates_to_ollama_launch_when_available(self) -> None:
        self.install_ollama(has_launch=True)
        host = self.start_ollama_http()
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host=host,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["delegate"], "ollama launch")
        self.assertEqual(rec["argv"], ["ollama", "launch", "claude-code", "--model", "qwen3.6:35b"])

    def test_paid_source_for_claude_is_refused(self) -> None:
        self.install_ollama(has_launch=False)
        before = _sha(self.claude)
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "anthropic:claude-3-5-sonnet",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout) if proc.stdout.strip().startswith("{") else {}
        text = (proc.stdout + proc.stderr + rec.get("reason", "")).lower()
        self.assertIn("paid", text)
        self.assertEqual(_sha(self.claude), before)

    def test_paid_source_for_codex_is_refused(self) -> None:
        proc = self.run_pfy(
            "launch",
            "codex",
            "--model",
            "openai:gpt-4o",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("paid", text)

    def test_ollama_down_exits_1_and_names_serve(self) -> None:
        self.install_ollama(has_launch=False)
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        text = proc.stdout + proc.stderr
        self.assertIn("ollama serve", text)

    def test_wizard_subcommand_is_not_the_phase2_verb(self) -> None:
        # Reserved #225 names must still reach the session wizard, not Phase 2.
        proc = self.run_pfy("launch", "harness", ollama_host="127.0.0.1:1")
        text = proc.stdout + proc.stderr
        self.assertIn("#225", text)
        self.assertNotIn("paid source refused", text.lower())
        self.assertNotIn("ollama serve", text)


if __name__ == "__main__":
    unittest.main()
