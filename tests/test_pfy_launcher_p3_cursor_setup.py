"""Phase 3 leftover: Cursor MCP/skills setup → doctor → uninstall.

Official user-level paths: ~/.cursor/mcp.json and ~/.cursor/skills/
(https://cursor.com/docs/mcp, https://cursor.com/docs/skills).

Temp HOME only. Never touch the real login-home ~/.cursor. Fake
cursor-agent and npx on PATH; those binaries must never be needed for
launch dry-run, and cursor-agent must never run during setup. No public
network, no paid keys, no on-demand.
"""
from __future__ import annotations

import hashlib
import json
import os
import pwd
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "pfy"

# Login home, not $HOME. Tests rewrite HOME to a throwaway dir.
_REAL_CURSOR = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".cursor"

CURSOR_JSON = (
    "{\n"
    '  "mcpServers": {\n'
    '    "other": {\n'
    '      "command": "keep-me"\n'
    "    }\n"
    "  }\n"
    "}\n"
)


def _sha(path: Path) -> str | None:
    if not path.exists() and not path.is_symlink():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_exe(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _tree_snapshot(root: Path) -> tuple:
    if not root.exists() and not root.is_symlink():
        return ("missing",)
    if root.is_symlink() or not root.is_dir():
        st = root.lstat()
        return ("not-dir", root, st.st_ino, st.st_mtime_ns, st.st_size, st.st_mode)
    rows = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(dirpath)
        for name in sorted(dirnames) + sorted(filenames):
            path = base / name
            info = path.lstat()
            rel = path.relative_to(root).as_posix()
            if stat.S_ISLNK(info.st_mode):
                data = os.readlink(path).encode("utf-8")
            elif stat.S_ISREG(info.st_mode):
                data = path.read_bytes()
            else:
                rows.append((rel, "other", info.st_mode, info.st_ino, info.st_mtime_ns))
                continue
            rows.append((rel, hashlib.sha256(data).hexdigest(), info.st_mode, info.st_ino, info.st_mtime_ns))
    return ("dir", tuple(rows))


_REAL_CURSOR_BEFORE = _tree_snapshot(_REAL_CURSOR)


class CursorSetupDoctorUninstall(unittest.TestCase):
    def setUp(self) -> None:
        self.home = Path(tempfile.mkdtemp(prefix="pfy-cursor-setup-"))
        self.addCleanup(self._cleanup)
        self.bindir = self.home / "bin"
        self.npx_log = self.home / "npx.log"
        self.install_npx()
        _write_exe(self.bindir / "cursor-agent", "#!/bin/sh\necho 'unexpected cursor-agent exec' >&2\nexit 99\n")

    def tearDown(self) -> None:
        self.assertEqual(
            _tree_snapshot(_REAL_CURSOR),
            _REAL_CURSOR_BEFORE,
            "tests touched the real ~/.cursor at %s" % _REAL_CURSOR,
        )

    def _cleanup(self) -> None:
        if self.home.exists():
            shutil.rmtree(self.home, ignore_errors=True)
        self.assertEqual(
            _tree_snapshot(_REAL_CURSOR),
            _REAL_CURSOR_BEFORE,
            "cleanup touched the real ~/.cursor at %s" % _REAL_CURSOR,
        )

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
            "CURSOR_HOME",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "OPENROUTER_API_KEY",
            "PFY_TEST_OPENAI_BASE",
            "PFY_LOCAL_RUNTIME",
            "LITELLM_BASE_URL",
            "LITELLM_PROXY_API_BASE",
            "PFY_LAUNCH_ISTTY",
            "OLLAMA_HOST",
            "GROK_HOME",
            "CLAUDE_CONFIG_DIR",
            "CODEX_HOME",
            "OPENCODE_CONFIG",
            "OPENCODE_CONFIG_DIR",
            "HERMES_HOME",
            "GEMINI_CLI_HOME",
            "PFY_STATE_DIR",
        ):
            env.pop(key, None)
        env.update(extra)
        return env

    def run_pfy(self, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PFY), *args],
            cwd=str(ROOT),
            env=self.env(**extra),
            capture_output=True,
            text=True,
            timeout=30,
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

    def seed_cursor(self) -> Path:
        path = self.home / ".cursor" / "mcp.json"
        path.parent.mkdir(parents=True)
        path.write_text(CURSOR_JSON)
        return path

    def doctor_states(self, proc: subprocess.CompletedProcess[str]) -> dict[tuple[str, str], str]:
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["status"], "ok")
        return {(r["harness"], r["item"]): r["state"] for r in payload["doctor"]}

    def test_setup_doctor_uninstall_round_trip(self) -> None:
        path = self.seed_cursor()
        original = path.read_bytes()
        before = _sha(path)
        applied = self.run_pfy("setup", "--preset", "core", "--harness", "cursor", "--yes")
        blob = applied.stdout + applied.stderr
        self.assertEqual(applied.returncode, 0, blob)
        self.assertNotIn("unexpected cursor-agent exec", blob)
        data = json.loads(path.read_text())
        self.assertEqual(data["mcpServers"]["other"]["command"], "keep-me")
        entry = data["mcpServers"]["code-graph"]
        self.assertEqual(entry["command"], "codebase-memory-mcp")
        self.assertEqual(entry["_pfy"]["owner"], "pfy")
        dumped = json.dumps(entry)
        self.assertNotIn("api-key", dumped.lower())
        self.assertNotIn("api_key", dumped.lower())
        self.assertNotIn("on-demand", dumped.lower())
        self.assertNotIn("CURSOR_API_KEY", dumped)
        skills = self.home / ".cursor" / "skills"
        self.assertTrue((skills / "adr" / "SKILL.md").is_file())
        backup = Path(str(path) + ".pfy.backup")
        self.assertTrue(backup.is_file())
        self.assertEqual(backup.read_bytes(), original)
        calls = self.npx_calls()
        self.assertTrue(any("--client" in c and "cursor" in c for c in calls), calls)
        joined = " ".join(" ".join(c) for c in calls).lower()
        self.assertNotIn("api-key", joined)
        self.assertNotIn("on-demand", joined)
        npx_env = json.loads((self.home / "npx-env.json").read_text())
        for key in ("CURSOR_API_KEY", "CURSOR_AUTH_TOKEN", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
            self.assertNotIn(key, npx_env)
        self.assertNotEqual(_sha(path), before)
        self.assertTrue(str(path).startswith(str(self.home)))
        self.assertNotEqual(path.resolve(), (_REAL_CURSOR / "mcp.json").resolve() if (_REAL_CURSOR / "mcp.json").exists() else Path("/nonexistent"))

        snapshot = {str(p): _sha(p) for p in (path, backup)}
        got = self.doctor_states(self.run_pfy("doctor", "--json"))
        for item in ("core-skills", "code-graph", "rea"):
            self.assertEqual(got[("cursor", item)], "aligned", (item, got))
        self.assertEqual(_sha(path), snapshot[str(path)])
        self.assertEqual(_sha(backup), snapshot[str(backup)])

        proc = self.run_pfy("uninstall", "--yes")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(backup.exists())
        self.assertFalse((skills / "adr").exists())

    def test_setup_without_yes_writes_nothing(self) -> None:
        path = self.seed_cursor()
        original = path.read_bytes()
        proc = self.run_pfy("setup", "--preset", "core", "--harness", "cursor")
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse(Path(str(path) + ".pfy.backup").exists())
        self.assertFalse((self.home / ".cursor" / "skills" / "adr").exists())
        self.assertFalse((self.home / ".local" / "state" / "pfy" / "installed.json").exists())

    def test_launch_does_not_write_cursor_config(self) -> None:
        path = self.seed_cursor()
        before = _sha(path)
        proc = self.run_pfy("launch", "cursor", "--yes", "--dry-run", "--json")
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertNotIn("unexpected cursor-agent exec", blob)
        rec = json.loads(proc.stdout.splitlines()[-1])
        self.assertEqual(rec["harness"], "cursor")
        self.assertEqual(_sha(path), before)
        self.assertFalse((self.home / ".local" / "state" / "pfy" / "installed.json").exists())
        self.assertFalse(Path(str(path) + ".pfy.backup").exists())


class RealCursorUntouched(unittest.TestCase):
    def test_module_snapshot_is_the_login_home(self) -> None:
        self.assertEqual(_REAL_CURSOR, Path(pwd.getpwuid(os.getuid()).pw_dir) / ".cursor")
        self.assertEqual(_tree_snapshot(_REAL_CURSOR), _REAL_CURSOR_BEFORE)
