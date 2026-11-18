"""Phase 3: Hermes and Gemini launch + setup/doctor/uninstall (docs/design/pfy-launcher.md §13).

Temp HOME, fake hermes/gemini binaries that must never be executed, fake npx,
local loopback probes only. No public network, no paid keys, no real cloud
calls. Launch must not write harness config; only explicit setup may.
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

HERMES_YAML = (
    "# user comment stays\n"
    "mcp_servers:\n"
    "  other:\n"
    "    command: keep-me\n"
)
GEMINI_JSON = (
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


class _P3Home(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.home = Path(tempfile.mkdtemp(prefix="pfy-launcher-p3-"))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.bindir = self.home / "bin"
        self.npx_log = self.home / "npx.log"
        self.servers: list[HTTPServer] = []

    def tearDown(self) -> None:
        for server in self.servers:
            server.shutdown()
            server.server_close()
        self.servers = []

    def start_http(self) -> str:
        port = _free_port()
        server = HTTPServer(("127.0.0.1", port), _TagsHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.servers.append(server)
        return f"127.0.0.1:{port}"

    def env(self, **extra: str) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(self.home)
        env["PATH"] = str(self.bindir) + os.pathsep + "/usr/bin:/bin"
        env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        env["XDG_STATE_HOME"] = str(self.home / ".local" / "state")
        env["PFY_ROOT"] = str(ROOT)
        env["NPX_LOG"] = str(self.npx_log)
        env["PFY_DETECT_SKIP_HOST"] = "1"
        for key in (
            "ANTHROPIC_API_KEY",
            "ANTHROPIC_AUTH_TOKEN",
            "OPENAI_API_KEY",
            "XAI_API_KEY",
            "CURSOR_API_KEY",
            "CURSOR_AUTH_TOKEN",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "GOOGLE_GENAI_USE_VERTEXAI",
            "GOOGLE_CLOUD_API_KEY",
            "OPENROUTER_API_KEY",
            "HERMES_API_KEY",
            "PFY_TEST_OPENAI_BASE",
            "PFY_LOCAL_RUNTIME",
            "LITELLM_BASE_URL",
            "LITELLM_PROXY_API_BASE",
            "PFY_LAUNCH_ISTTY",
            "OLLAMA_HOST",
            "HERMES_HOME",
            "GEMINI_CLI_HOME",
            "GROK_HOME",
            "CLAUDE_CONFIG_DIR",
            "CODEX_HOME",
            "OPENCODE_CONFIG",
            "OPENCODE_CONFIG_DIR",
            "PFY_STATE_DIR",
        ):
            env.pop(key, None)
        env.update(extra)
        return env

    def run_pfy(self, *args: str, stdin: str | None = None, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PFY), *args],
            cwd=str(ROOT),
            env=self.env(**extra),
            input=stdin,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def install_fake(self, name: str) -> None:
        _write_exe(self.bindir / name, "#!/bin/sh\necho 'unexpected %s exec' >&2\nexit 99\n" % name)

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

    def install_npx(self) -> None:
        _write_exe(
            self.bindir / "npx",
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "home = os.environ['HOME']\n"
            "log = os.environ.get('NPX_LOG') or os.path.join(home, 'npx.log')\n"
            "with open(log, 'a', encoding='utf-8') as f:\n"
            "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "with open(os.path.join(home, 'npx-env.json'), 'w', encoding='utf-8') as f:\n"
            "    json.dump(dict(os.environ), f)\n",
        )

    def npx_calls(self) -> list[list[str]]:
        if not self.npx_log.is_file():
            return []
        return [json.loads(line) for line in self.npx_log.read_text().splitlines() if line.strip()]

    def seed_hermes(self) -> Path:
        path = self.home / ".hermes" / "config.yaml"
        path.parent.mkdir(parents=True)
        path.write_text(HERMES_YAML)
        return path

    def seed_gemini(self) -> Path:
        path = self.home / ".gemini" / "settings.json"
        path.parent.mkdir(parents=True)
        path.write_text(GEMINI_JSON)
        return path


class LaunchHermesGemini(_P3Home):
    def test_hermes_ollama_dry_run_uses_official_custom_flags(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_fake("hermes")
        path = self.seed_hermes()
        before = _sha(path)
        host = self.start_http()
        proc = self.run_pfy(
            "launch",
            "hermes",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            OLLAMA_HOST=host,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertNotIn("unexpected hermes exec", proc.stderr)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["harness"], "hermes")
        self.assertEqual(rec["model"], "ollama:qwen3.6:35b")
        self.assertTrue(rec["dry_run"])
        self.assertEqual(rec.get("delegate"), "")
        self.assertEqual(rec["argv"][0], "hermes")
        self.assertEqual(rec["argv"][1:7], ["--provider", "custom", "--base-url", "http://%s/v1" % host, "--model", "qwen3.6:35b"])
        self.assertNotIn("--api-key", rec["argv"])
        self.assertEqual(rec["env"], {})
        self.assertEqual(_sha(path), before)
        self.assertEqual(path.read_text(), HERMES_YAML)

    def test_hermes_delegates_to_ollama_launch_when_available(self) -> None:
        self.install_ollama(has_launch=True)
        self.install_fake("hermes")
        host = self.start_http()
        proc = self.run_pfy(
            "launch",
            "hermes",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            OLLAMA_HOST=host,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["delegate"], "ollama launch")
        self.assertEqual(rec["argv"], ["ollama", "launch", "hermes", "--model", "qwen3.6:35b"])

    def test_hermes_llamacpp_uses_spine_base_url(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_fake("hermes")
        spine = self.start_http()
        proc = self.run_pfy(
            "launch",
            "hermes",
            "--model",
            "llamacpp:my-alias",
            "--yes",
            "--dry-run",
            "--json",
            OLLAMA_HOST="127.0.0.1:1",
            PFY_TEST_OPENAI_BASE=spine,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["model"], "llamacpp:my-alias")
        self.assertEqual(rec["argv"][0:6], ["hermes", "--provider", "custom", "--base-url", "http://%s/v1" % spine, "--model"])
        self.assertEqual(rec["argv"][6], "my-alias")
        self.assertEqual(rec["env"], {})

    def test_hermes_paid_model_is_refused(self) -> None:
        self.install_fake("hermes")
        path = self.seed_hermes()
        before = _sha(path)
        proc = self.run_pfy(
            "launch",
            "hermes",
            "--model",
            "openrouter:foo",
            "--yes",
            "--dry-run",
            "--json",
            OLLAMA_HOST="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        self.assertNotIn("unexpected hermes exec", proc.stderr)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("paid", text)
        self.assertEqual(_sha(path), before)

    def test_hermes_openrouter_provider_is_refused(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_fake("hermes")
        host = self.start_http()
        proc = self.run_pfy(
            "launch",
            "hermes",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "--provider",
            "openrouter",
            OLLAMA_HOST=host,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        self.assertNotIn("unexpected hermes exec", proc.stderr)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("refused", text)
        self.assertIn("local", text)

    def test_hermes_api_key_passthrough_is_refused(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_fake("hermes")
        host = self.start_http()
        proc = self.run_pfy(
            "launch",
            "hermes",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "--api-key",
            "secret",
            OLLAMA_HOST=host,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        self.assertNotIn("unexpected hermes exec", proc.stderr)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("api-key", text)
        self.assertIn("refused", text)

    def test_gemini_ollama_dry_run_uses_local_litellm_env(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_fake("gemini")
        path = self.seed_gemini()
        before = _sha(path)
        ollama = self.start_http()
        lite = self.start_http()
        proc = self.run_pfy(
            "launch",
            "gemini",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            OLLAMA_HOST=ollama,
            LITELLM_BASE_URL="http://%s/v1" % lite,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertNotIn("unexpected gemini exec", proc.stderr)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["harness"], "gemini")
        self.assertEqual(rec["model"], "ollama:qwen3.6:35b")
        self.assertEqual(rec["delegate"], "litellm")
        self.assertEqual(rec["argv"][:3], ["gemini", "--model", "qwen3.6:35b"])
        env = rec["env"]
        self.assertEqual(env.get("GOOGLE_GEMINI_BASE_URL"), "http://%s" % lite)
        self.assertEqual(env.get("GEMINI_MODEL"), "qwen3.6:35b")
        self.assertNotIn("GEMINI_API_KEY", env)
        self.assertNotIn("GOOGLE_API_KEY", env)
        self.assertEqual(_sha(path), before)
        self.assertEqual(path.read_text(), GEMINI_JSON)

    def test_gemini_delegates_to_ollama_launch_when_available(self) -> None:
        self.install_ollama(has_launch=True)
        self.install_fake("gemini")
        host = self.start_http()
        proc = self.run_pfy(
            "launch",
            "gemini",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            OLLAMA_HOST=host,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["delegate"], "ollama launch")
        self.assertEqual(rec["argv"], ["ollama", "launch", "gemini", "--model", "qwen3.6:35b"])

    def test_gemini_litellm_down_names_local_yaml(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_fake("gemini")
        host = self.start_http()
        proc = self.run_pfy(
            "launch",
            "gemini",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            OLLAMA_HOST=host,
            LITELLM_BASE_URL="http://127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        text = (proc.stdout + proc.stderr)
        self.assertIn("LiteLLM", text)
        self.assertIn("local-only.yaml", text)

    def test_gemini_api_key_passthrough_is_refused(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_fake("gemini")
        ollama = self.start_http()
        lite = self.start_http()
        proc = self.run_pfy(
            "launch",
            "gemini",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "--api-key",
            "secret",
            OLLAMA_HOST=ollama,
            LITELLM_BASE_URL="http://%s/v1" % lite,
        )
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        self.assertNotIn("unexpected gemini exec", proc.stderr)
        text = (proc.stdout + proc.stderr).lower()
        self.assertIn("refused", text)

    def test_tty_selector_picks_hermes_local_and_shows_costs(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_fake("hermes")
        path = self.seed_hermes()
        before = _sha(path)
        host = self.start_http()
        proc = self.run_pfy(
            "launch",
            "--yes",
            "--dry-run",
            "--json",
            stdin="4\n1\n",
            PFY_LAUNCH_ISTTY="1",
            OLLAMA_HOST=host,
            PFY_TEST_OPENAI_BASE="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        menu = proc.stdout + proc.stderr
        self.assertIn("hermes", menu.lower())
        self.assertIn("local models only", menu.lower())
        self.assertIn("subscription", menu.lower())
        self.assertTrue("estimate $" in menu.lower() or "estimate unavailable" in menu.lower(), menu)
        rec = json.loads(proc.stdout.splitlines()[-1])
        self.assertEqual(rec["harness"], "hermes")
        self.assertEqual(rec["model"], "ollama:qwen3.6:35b")
        self.assertEqual(rec["argv"][0], "hermes")
        self.assertNotIn("unexpected hermes exec", proc.stderr)
        self.assertEqual(_sha(path), before)

    def test_tty_selector_picks_gemini_local(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_fake("gemini")
        path = self.seed_gemini()
        before = _sha(path)
        ollama = self.start_http()
        lite = self.start_http()
        proc = self.run_pfy(
            "launch",
            "--yes",
            "--dry-run",
            "--json",
            stdin="5\n1\n",
            PFY_LAUNCH_ISTTY="1",
            OLLAMA_HOST=ollama,
            LITELLM_BASE_URL="http://%s/v1" % lite,
            PFY_TEST_OPENAI_BASE="127.0.0.1:1",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        menu = proc.stdout + proc.stderr
        self.assertIn("gemini", menu.lower())
        self.assertIn("local models only", menu.lower())
        rec = json.loads(proc.stdout.splitlines()[-1])
        self.assertEqual(rec["harness"], "gemini")
        self.assertEqual(rec["model"], "ollama:qwen3.6:35b")
        self.assertEqual(rec["argv"][:3], ["gemini", "--model", "qwen3.6:35b"])
        self.assertNotIn("unexpected gemini exec", proc.stderr)
        self.assertEqual(_sha(path), before)


class SetupDoctorUninstall(_P3Home):
    def _apply(self, harness: str) -> subprocess.CompletedProcess[str]:
        return self.run_pfy("setup", "--preset", "core", "--harness", harness, "--yes")

    def doctor_states(self, proc: subprocess.CompletedProcess[str]) -> dict[tuple[str, str], str]:
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "ok")
        return {(r["harness"], r["item"]): r["state"] for r in payload["doctor"]}

    def test_hermes_setup_doctor_uninstall_round_trip(self) -> None:
        self.install_npx()
        path = self.seed_hermes()
        original = path.read_bytes()
        before = _sha(path)
        applied = self._apply("hermes")
        blob = applied.stdout + applied.stderr
        self.assertEqual(applied.returncode, 0, blob)
        text = path.read_text()
        self.assertIn("# user comment stays", text)
        self.assertIn("managed-by: pfy item=code-graph", text)
        self.assertIn("codebase-memory-mcp", text)
        self.assertIn("enabled: true", text)
        self.assertIn("command: keep-me", text)
        skills = self.home / ".hermes" / "skills"
        self.assertTrue((skills / "adr" / "SKILL.md").is_file())
        calls = self.npx_calls()
        self.assertTrue(any("--client" in c and "hermes" in c for c in calls), calls)
        self.assertNotEqual(_sha(path), before)

        snapshot = {str(p): _sha(p) for p in (path, Path(str(path) + ".pfy.backup"))}
        got = self.doctor_states(self.run_pfy("doctor", "--json"))
        for item in ("core-skills", "code-graph", "rea"):
            self.assertEqual(got[("hermes", item)], "aligned", (item, got))
        self.assertEqual(_sha(path), snapshot[str(path)])
        self.assertEqual(_sha(Path(str(path) + ".pfy.backup")), snapshot[str(path) + ".pfy.backup"])

        proc = self.run_pfy("uninstall", "--yes")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(Path(str(path) + ".pfy.backup").exists())
        self.assertFalse((skills / "adr").exists())

    def test_gemini_setup_doctor_uninstall_round_trip(self) -> None:
        self.install_npx()
        path = self.seed_gemini()
        original = path.read_bytes()
        before = _sha(path)
        applied = self._apply("gemini")
        blob = applied.stdout + applied.stderr
        self.assertEqual(applied.returncode, 0, blob)
        data = json.loads(path.read_text())
        self.assertEqual(data["mcpServers"]["other"]["command"], "keep-me")
        entry = data["mcpServers"]["code-graph"]
        self.assertEqual(entry["command"], "codebase-memory-mcp")
        self.assertEqual(entry["_pfy"]["owner"], "pfy")
        skills = self.home / ".agents" / "skills"
        self.assertTrue((skills / "adr" / "SKILL.md").is_file())
        calls = self.npx_calls()
        self.assertTrue(any("--client" in c and "gemini_cli" in c for c in calls), calls)
        self.assertNotEqual(_sha(path), before)

        snapshot = {str(p): _sha(p) for p in (path, Path(str(path) + ".pfy.backup"))}
        got = self.doctor_states(self.run_pfy("doctor", "--json"))
        for item in ("core-skills", "code-graph", "rea"):
            self.assertEqual(got[("gemini", item)], "aligned", (item, got))
        self.assertEqual(_sha(path), snapshot[str(path)])
        self.assertEqual(_sha(Path(str(path) + ".pfy.backup")), snapshot[str(path) + ".pfy.backup"])

        proc = self.run_pfy("uninstall", "--yes")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(Path(str(path) + ".pfy.backup").exists())
        self.assertFalse((skills / "adr").exists())

    def test_launch_does_not_write_harness_config(self) -> None:
        self.install_ollama(has_launch=False)
        self.install_fake("hermes")
        self.install_fake("gemini")
        hermes = self.seed_hermes()
        gemini = self.seed_gemini()
        h_before, g_before = _sha(hermes), _sha(gemini)
        ollama = self.start_http()
        lite = self.start_http()
        for name in ("hermes", "gemini"):
            proc = self.run_pfy(
                "launch",
                name,
                "--model",
                "ollama:qwen3.6:35b",
                "--yes",
                "--dry-run",
                "--json",
                OLLAMA_HOST=ollama,
                LITELLM_BASE_URL="http://%s/v1" % lite,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(_sha(hermes), h_before)
        self.assertEqual(_sha(gemini), g_before)
        self.assertFalse((self.home / ".local" / "state" / "pfy" / "installed.json").exists())


class YamlMcpHelper(unittest.TestCase):
    def test_render_yaml_mcp_keeps_comments_and_strip_restores(self) -> None:
        from pfylib.adapters.base import _strip_yaml_item, render_yaml_mcp

        current = HERMES_YAML.encode()
        entry = {"name": "code-graph", "command": "codebase-memory-mcp"}
        written = render_yaml_mcp(current, "code-graph", entry)
        text = written.decode()
        self.assertIn("# user comment stays", text)
        self.assertIn("command: keep-me", text)
        self.assertIn("# managed-by: pfy item=code-graph", text)
        self.assertIn("enabled: true", text)
        again = render_yaml_mcp(written, "code-graph", entry)
        self.assertEqual(again, written)
        stripped = _strip_yaml_item(text, "code-graph")
        self.assertIsNotNone(stripped)
        self.assertIn("# user comment stays", stripped or "")
        self.assertIn("command: keep-me", stripped or "")
        self.assertNotIn("codebase-memory-mcp", stripped or "")
        self.assertNotIn("managed-by: pfy item=code-graph", stripped or "")
