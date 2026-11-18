"""ollama launch argv matches the official CLI (ollama 0.30.8 on nimo).

From `ollama launch --help` (read-only, no model load):
  ollama launch [INTEGRATION] [-- [EXTRA_ARGS...]] [flags]
Official integrations include claude and hermes, not claude-code or gemini.
Flags before `--` are only --model, --config, --restore, -y/--yes, and -h/--help.
A passthrough like -p must follow `--`, or the real CLI errors with
"unknown shorthand flag".

Temp HOME, fake ollama that parses argv the same way, loopback HTTP only.
No public network, no paid keys, no auto-pull, no real cloud calls.
Does not import other test_pfy_launcher_* modules (discover double-count).
"""
from __future__ import annotations

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

# Integration names from `ollama launch --help` on nimo (ollama 0.30.8).
OFFICIAL_INTEGRATIONS = frozenset({
    "claude", "codex-app", "codex-desktop", "codex-gui", "hermes", "openclaw",
    "clawdbot", "moltbot", "opencode", "codex", "hermes-desktop", "copilot",
    "copilot-cli", "omp", "droid", "kimi", "pi", "pool", "cline", "qwen",
    "vscode", "code",
})

FAKE_OLLAMA = r"""#!/usr/bin/env python3
import json, os, pathlib, sys

KNOWN = {"--config", "--restore", "--yes", "-y", "--help", "-h"}
SUPPORTED = %s

args = sys.argv[1:]
pathlib.Path(__file__).with_name("ollama-argv.log").write_text(json.dumps(args))
if args[:1] == ["pull"]:
    print("unexpected pull", file=sys.stderr)
    raise SystemExit(99)
if args[:1] != ["launch"]:
    raise SystemExit(0)
rest = args[1:]
if "--help" in rest or "-h" in rest:
    print("ollama launch")
    print("  ollama launch [INTEGRATION] [-- [EXTRA_ARGS...]] [flags]")
    raise SystemExit(0)
if "--" in rest:
    idx = rest.index("--")
    before, after = rest[:idx], rest[idx + 1 :]
else:
    before, after = rest, []
integration = None
i = 0
while i < len(before):
    tok = before[i]
    if not tok.startswith("-"):
        if integration is not None:
            print("Error: unexpected argument %%s" %% tok, file=sys.stderr)
            raise SystemExit(1)
        integration = tok
        i += 1
        continue
    name = tok.split("=", 1)[0]
    if name == "--model":
        if "=" not in tok:
            if i + 1 >= len(before):
                print("Error: flag needs an argument: --model", file=sys.stderr)
                raise SystemExit(1)
            i += 2
        else:
            i += 1
        continue
    if name in KNOWN:
        i += 1
        continue
    if tok.startswith("-") and not tok.startswith("--"):
        print("Error: unknown shorthand flag: %%r in %%s" %% (tok[1:2], tok), file=sys.stderr)
        raise SystemExit(1)
    print("Error: unknown flag: %%s" %% tok, file=sys.stderr)
    raise SystemExit(1)
if integration is None:
    print("Error: Flags and extra arguments require an integration name", file=sys.stderr)
    raise SystemExit(1)
if integration not in SUPPORTED:
    print("Error: unknown integration %%r" %% integration, file=sys.stderr)
    raise SystemExit(1)
pathlib.Path(__file__).with_name("ollama-passthrough.log").write_text(json.dumps(after))
if "--exit" in after:
    raise SystemExit(int(after[after.index("--exit") + 1]))
if "--signal" in after:
    os.kill(os.getpid(), int(after[after.index("--signal") + 1]))
print("OLLAMA_LAUNCH:" + json.dumps({"integration": integration, "after": after}))
raise SystemExit(0)
""" % (repr(sorted(OFFICIAL_INTEGRATIONS)),)


def _write_exe(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _TagsHandler(BaseHTTPRequestHandler):
    models: ClassVar[list[str]] = ["qwen3.6:35b"]

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
        self.send_response(200)
        body = b"{}"
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


class OllamaLaunchArgv(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile

        self.home = Path(tempfile.mkdtemp(prefix="pfy-ollama-launch-"))
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.bindir = self.home / "bin"
        self.bindir.mkdir()
        _TagsHandler.models = ["qwen3.6:35b"]
        self.servers: list[HTTPServer] = []
        _write_exe(self.bindir / "ollama", FAKE_OLLAMA)
        for name in ("claude", "hermes", "gemini", "grok", "cursor-agent"):
            _write_exe(
                self.bindir / name,
                "#!/usr/bin/env python3\nimport sys\n"
                "print('unexpected direct exec '+sys.argv[0], file=sys.stderr)\n"
                "raise SystemExit(99)\n",
            )

    def tearDown(self) -> None:
        for server in self.servers:
            server.shutdown()
            server.server_close()
        self.servers = []

    def start_http(self) -> str:
        port = _free_port()
        server = HTTPServer(("127.0.0.1", port), _TagsHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
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

    def run_pfy(
        self,
        *args: str,
        ollama_host: str,
        **extra: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PFY), *args],
            cwd=str(ROOT),
            env=self.env(ollama_host=ollama_host, **extra),
            capture_output=True,
            text=True,
            timeout=30,
        )

    def passthrough(self) -> list:
        path = self.bindir / "ollama-passthrough.log"
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def test_fake_ollama_rejects_p_before_dashdash(self) -> None:
        # Contract of the real CLI, not tautological: this is why the live smoke failed.
        proc = subprocess.run(
            [
                str(self.bindir / "ollama"),
                "launch",
                "claude-code",
                "--model",
                "qwen3.6:35b",
                "-p",
                "ok",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("unknown shorthand flag", proc.stderr)

    def test_claude_dry_run_json_uses_official_name_and_dashdash(self) -> None:
        host = self.start_http()
        proc = self.run_pfy(
            "launch",
            "claude-code",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "-p",
            "Reply with the single word: ok",
            ollama_host=host,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertEqual(rec["delegate"], "ollama launch")
        self.assertEqual(
            rec["argv"],
            [
                "ollama",
                "launch",
                "claude",
                "--model",
                "qwen3.6:35b",
                "--",
                "-p",
                "Reply with the single word: ok",
            ],
        )
        self.assertFalse((self.bindir / "ollama-passthrough.log").exists())

    def test_claude_live_passthrough_and_exit_codes(self) -> None:
        host = self.start_http()
        for code in (0, 3, 42):
            with self.subTest(code=code):
                proc = self.run_pfy(
                    "launch",
                    "claude-code",
                    "--model",
                    "ollama:qwen3.6:35b",
                    "--yes",
                    "--",
                    "-p",
                    "Reply with the single word: ok",
                    "--exit",
                    str(code),
                    ollama_host=host,
                )
                self.assertEqual(proc.returncode, code, proc.stderr + proc.stdout)
                self.assertNotIn("unknown shorthand flag", proc.stderr)
                self.assertEqual(
                    self.passthrough(),
                    ["-p", "Reply with the single word: ok", "--exit", str(code)],
                )

    def test_claude_signal_still_passes_through(self) -> None:
        host = self.start_http()
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

    def test_hermes_dry_run_and_live_insert_dashdash(self) -> None:
        host = self.start_http()
        dry = self.run_pfy(
            "launch",
            "hermes",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "--quiet",
            ollama_host=host,
        )
        self.assertEqual(dry.returncode, 0, dry.stderr + dry.stdout)
        rec = json.loads(dry.stdout)
        self.assertEqual(rec["delegate"], "ollama launch")
        self.assertEqual(
            rec["argv"],
            ["ollama", "launch", "hermes", "--model", "qwen3.6:35b", "--", "--quiet"],
        )
        live = self.run_pfy(
            "launch",
            "hermes",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--",
            "--quiet",
            "--exit",
            "3",
            ollama_host=host,
        )
        self.assertEqual(live.returncode, 3, live.stderr + live.stdout)
        self.assertEqual(self.passthrough(), ["--quiet", "--exit", "3"])

    def test_gemini_does_not_delegate_to_unsupported_ollama_integration(self) -> None:
        host = self.start_http()
        proc = self.run_pfy(
            "launch",
            "gemini",
            "--model",
            "ollama:qwen3.6:35b",
            "--yes",
            "--dry-run",
            "--json",
            "--",
            "--prompt",
            "ok",
            ollama_host=host,
            LITELLM_BASE_URL="http://%s/v1" % host,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        rec = json.loads(proc.stdout)
        self.assertNotEqual(rec.get("delegate"), "ollama launch")
        self.assertEqual(rec["argv"][0], "gemini")
        self.assertNotIn("ollama", rec["argv"])
        self.assertEqual(rec["argv"][-2:], ["--prompt", "ok"])

    def test_grok_and_cursor_do_not_use_ollama_launch(self) -> None:
        host = self.start_http()
        for harness, binary in (("grok", "grok"), ("cursor", "cursor-agent")):
            with self.subTest(harness=harness):
                proc = self.run_pfy(
                    "launch",
                    harness,
                    "--yes",
                    "--dry-run",
                    "--json",
                    "--",
                    "--print",
                    ollama_host=host,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
                rec = json.loads(proc.stdout)
                self.assertNotEqual(rec.get("delegate"), "ollama launch")
                self.assertEqual(rec["argv"], [binary, "--print"])


if __name__ == "__main__":
    unittest.main()
