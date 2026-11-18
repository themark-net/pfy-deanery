"""Phase 2: pfy launch with ollama/llamacpp sources, TTY picker, and grok (docs/design/pfy-launcher.md §13).

Temp HOME, fake claude/ollama/grok/cursor-agent on PATH, local loopback probes only. No public
network, no paid keys, no real cloud calls, no harness-config writes.
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
        if self.path.split("?", 1)[0] in ("/api/tags", "/v1/models", "/models", "/health"):
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
        self.servers: list[HTTPServer] = []

    def tearDown(self) -> None:
        for server in [self.httpd, *self.servers]:
            if server is None:
                continue
            server.shutdown()
            server.server_close()
        self.httpd = None
        self.servers = []

    def start_http(self) -> str:
        port = _free_port()
        server = HTTPServer(("127.0.0.1", port), _TagsHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.servers.append(server)
        if self.httpd is None:
            self.httpd = server
        return f"127.0.0.1:{port}"

    def start_ollama_http(self) -> str:
        return self.start_http()

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
        env.pop("XAI_API_KEY", None)
        env.pop("CURSOR_API_KEY", None)
        env.pop("CURSOR_AUTH_TOKEN", None)
        env.pop("PFY_TEST_OPENAI_BASE", None)
        env.pop("PFY_LOCAL_RUNTIME", None)
        env.pop("LITELLM_BASE_URL", None)
        env.pop("LITELLM_PROXY_API_BASE", None)
        env.pop("PFY_LAUNCH_ISTTY", None)
        env["PFY_DETECT_SKIP_HOST"] = "1"
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

    def install_grok(self) -> None:
        _write_exe(self.bindir / "grok", "#!/bin/sh\necho 'unexpected grok exec' >&2\nexit 99\n")

    def install_cursor(self) -> None:
        _write_exe(self.bindir / "cursor-agent", "#!/bin/sh\necho 'unexpected cursor-agent exec' >&2\nexit 99\n")

    def fingerprint(self) -> tuple[str | None, dict[str, str | None]]:
        return _sha(self.claude), {str(p): _sha(p) for p in self.claude_dir.rglob("*") if p.is_file()}

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
        self.assertEqual(rec["argv"], ["ollama", "launch", "claude", "--model", "qwen3.6:35b"])

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

    def test_llamacpp_dry_run_json_uses_litellm_env(self) -> None:
        self.install_ollama(has_launch=False)
        spine = self.start_http()
        lite = self.start_http()
        before, before_dir = self.fingerprint()
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "llamacpp:my-alias",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host="127.0.0.1:1",
            PFY_TEST_OPENAI_BASE=spine,
            PFY_LOCAL_RUNTIME="llama-swap",
            LITELLM_BASE_URL=f"http://{lite}/v1",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["harness"], "claude-code")
        self.assertEqual(rec["model"], "llamacpp:my-alias")
        self.assertTrue(rec["dry_run"])
        self.assertEqual(rec.get("delegate"), "litellm")
        self.assertEqual(rec["argv"][0], "claude")
        self.assertEqual(rec["env"]["ANTHROPIC_BASE_URL"], f"http://{lite}")
        self.assertEqual(rec["env"]["ANTHROPIC_AUTH_TOKEN"], "litellm")
        self.assertNotIn("ANTHROPIC_API_KEY", rec["env"])
        self.assertEqual(_sha(self.claude), before)
        self.assertEqual({str(p): _sha(p) for p in self.claude_dir.rglob("*") if p.is_file()}, before_dir)

    def test_llamacpp_spine_down_names_llama_swap(self) -> None:
        self.install_ollama(has_launch=False)
        lite = self.start_http()
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "llamacpp:my-alias",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host="127.0.0.1:1",
            PFY_TEST_OPENAI_BASE="127.0.0.1:1",
            PFY_LOCAL_RUNTIME="llama-server",
            LITELLM_BASE_URL=f"http://{lite}",
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        text = proc.stdout + proc.stderr
        self.assertIn("llama-swap or llama-server", text)

    def test_llamacpp_litellm_down_names_local_yaml(self) -> None:
        self.install_ollama(has_launch=False)
        spine = self.start_http()
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "llamacpp:my-alias",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host="127.0.0.1:1",
            PFY_TEST_OPENAI_BASE=spine,
            PFY_LOCAL_RUNTIME="llama-server",
            LITELLM_BASE_URL="http://127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        text = proc.stdout + proc.stderr
        self.assertIn("config/litellm/local-only.yaml", text)

    def test_non_tty_missing_flags_exits_2(self) -> None:
        self.install_ollama(has_launch=False)
        proc = self.run_pfy(
            "launch",
            ollama_host="127.0.0.1:1",
            PFY_LAUNCH_ISTTY="0",
        )
        self.assertEqual(proc.returncode, 2, proc.stderr + proc.stdout)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("flags", text)
        self.assertTrue("--model" in text or "harness" in text)

    def test_non_tty_harness_without_model_defaults_to_local(self) -> None:
        """Fail: non-TTY `pfy launch claude-code` without --model exits 2.
        Recover: it plans the local default and does not call a cloud source.
        """
        self.install_ollama(has_launch=False)
        host = self.start_ollama_http()
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host=host,
            PFY_LAUNCH_ISTTY="0",
            PFY_TEST_OPENAI_BASE="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout.splitlines()[-1])
        self.assertEqual(rec["harness"], "claude-code")
        self.assertEqual(rec["model"], "ollama:qwen3.6:35b")
        self.assertTrue(rec["dry_run"])
        blob = (proc.stdout + proc.stderr).lower()
        self.assertNotIn("pb://", blob)

    def test_tty_selector_picks_local_default(self) -> None:
        self.install_ollama(has_launch=False)
        host = self.start_ollama_http()
        before, before_dir = self.fingerprint()
        proc = self.run_pfy(
            "launch",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host=host,
            stdin="1\n1\n",
            PFY_LAUNCH_ISTTY="1",
            PFY_TEST_OPENAI_BASE="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        # Menu (printed first) shows the local default and cost/subscription labels.
        menu = proc.stdout + proc.stderr
        self.assertIn("qwen3.6:35b", menu)
        self.assertIn("subscription", menu.lower())
        rec = json.loads(proc.stdout.splitlines()[-1])
        self.assertEqual(rec["harness"], "claude-code")
        self.assertEqual(rec["model"], "ollama:qwen3.6:35b")
        self.assertTrue(rec["dry_run"])
        self.assertEqual(_sha(self.claude), before)
        self.assertEqual({str(p): _sha(p) for p in self.claude_dir.rglob("*") if p.is_file()}, before_dir)

    def test_tty_selector_enter_picks_local_default(self) -> None:
        """Fail: empty Enter on the model menu is 'no selection'.
        Recover: Enter keeps ollama:qwen3.6:35b, the local default.
        """
        self.install_ollama(has_launch=False)
        host = self.start_ollama_http()
        proc = self.run_pfy(
            "launch",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host=host,
            stdin="1\n\n",
            PFY_LAUNCH_ISTTY="1",
            PFY_TEST_OPENAI_BASE="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        menu = proc.stdout + proc.stderr
        self.assertIn("qwen3.6:35b", menu)
        self.assertRegex(menu.lower(), r"enter keeps")
        rec = json.loads(proc.stdout.splitlines()[-1])
        self.assertEqual(rec["harness"], "claude-code")
        self.assertEqual(rec["model"], "ollama:qwen3.6:35b")
        self.assertTrue(rec["dry_run"])

    def test_tty_selector_shows_estimate_and_refuses_cloud(self) -> None:
        self.install_ollama(has_launch=False)
        host = self.start_ollama_http()
        # Pick claude-code, then the first cloud row (after local default, one llamacpp alias, grok, cursor).
        proc = self.run_pfy(
            "launch",
            "--yes",
            "--dry-run",
            "--json",
            "--max-usd",
            "9",
            ollama_host=host,
            stdin="1\n5\n",
            PFY_LAUNCH_ISTTY="1",
            PFY_TEST_OPENAI_BASE="127.0.0.1:1",
        )
        self.assertNotEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        text = (proc.stdout + proc.stderr).lower()
        self.assertTrue("estimate $" in text or "estimate unavailable" in text, text)
        self.assertIn("paid", text)

    def test_yes_without_max_usd_does_not_run_cloud(self) -> None:
        from pfylib.launch import LaunchError, require_cloud_cap

        with self.assertRaises(LaunchError) as ctx:
            require_cloud_cap(yes=True, max_usd=None, estimate="estimate $0.0070")
        self.assertIn("--max-usd", str(ctx.exception.reason))
        require_cloud_cap(yes=True, max_usd=1.0, estimate="estimate $0.0070")

    def test_grok_dry_run_json_does_not_exec_fake_binary(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_grok()
        before, before_dir = self.fingerprint()
        proc = self.run_pfy(
            "launch",
            "grok",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "--quiet",
            ollama_host="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertNotIn("unexpected grok exec", proc.stderr)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["harness"], "grok")
        self.assertEqual(rec["model"], "subscription")
        self.assertEqual(rec["argv"], ["grok", "--quiet"])
        self.assertEqual(rec["env"], {})
        self.assertTrue(rec["dry_run"])
        self.assertEqual(_sha(self.claude), before)
        self.assertEqual({str(p): _sha(p) for p in self.claude_dir.rglob("*") if p.is_file()}, before_dir)

    def test_tty_selector_picks_grok_subscription(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_grok()
        proc = self.run_pfy(
            "launch",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host="127.0.0.1:1",
            stdin="2\n",
            PFY_LAUNCH_ISTTY="1",
            PFY_TEST_OPENAI_BASE="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("subscription", text)
        rec = json.loads(proc.stdout.splitlines()[-1])
        self.assertEqual(rec["harness"], "grok")
        self.assertEqual(rec["model"], "subscription")
        self.assertEqual(rec["argv"], ["grok"])
        self.assertNotIn("unexpected grok exec", proc.stderr)


    def test_cursor_dry_run_json_does_not_exec_fake_binary(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_cursor()
        cursor_json = self.home / ".cursor" / "mcp.json"
        cursor_json.parent.mkdir(parents=True)
        cursor_json.write_text("{\"mcpServers\": {}}\n")
        before = _sha(cursor_json)
        proc = self.run_pfy(
            "launch",
            "cursor",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "--print",
            ollama_host="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertNotIn("unexpected cursor-agent exec", proc.stderr)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["harness"], "cursor")
        self.assertEqual(rec["model"], "subscription")
        self.assertEqual(rec["argv"], ["cursor-agent", "--print"])
        self.assertEqual(rec["env"], {})
        self.assertTrue(rec["dry_run"])
        self.assertEqual(_sha(cursor_json), before)
        self.assertNotIn("CURSOR_API_KEY", rec["env"])
        self.assertNotIn("--api-key", rec["argv"])

    def test_cursor_api_key_passthrough_is_refused(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_cursor()
        proc = self.run_pfy(
            "launch",
            "cursor",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "--api-key",
            "placeholder",
            ollama_host="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        self.assertNotIn("unexpected cursor-agent exec", proc.stderr)
        text = proc.stdout + proc.stderr
        self.assertIn("subscription", text.lower())
        self.assertIn("--api-key", text)
        self.assertNotIn("placeholder", text)
        self.assertIn("cursor-agent login", text)

    def test_cursor_worker_passthrough_is_refused(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_cursor()
        proc = self.run_pfy(
            "launch",
            "cursor",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "worker",
            "start",
            ollama_host="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        self.assertNotIn("unexpected cursor-agent exec", proc.stderr)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("worker", text)
        self.assertIn("subscription", text)

    def test_tty_selector_picks_cursor_subscription(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_cursor()
        proc = self.run_pfy(
            "launch",
            "--yes",
            "--dry-run",
            "--json",
            ollama_host="127.0.0.1:1",
            stdin="3\n",
            PFY_LAUNCH_ISTTY="1",
            PFY_TEST_OPENAI_BASE="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("subscription", text)
        rec = json.loads(proc.stdout.splitlines()[-1])
        self.assertEqual(rec["harness"], "cursor")
        self.assertEqual(rec["model"], "subscription")
        self.assertEqual(rec["argv"], ["cursor-agent"])
        self.assertEqual(rec["env"], {})
        self.assertNotIn("unexpected cursor-agent exec", proc.stderr)



if __name__ == "__main__":
    unittest.main()
