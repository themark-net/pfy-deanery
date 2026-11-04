"""Bare ./pfy must not start ollama serve unless the operator opts in.

Fake ollama records argv. Health is a closed port. The window step is a
no-op. Host 127.0.0.1:11434 is refused by the curl stub.
"""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PFY = ROOT / "pfy"


def _closed_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _exe(path: Path, body: str) -> None:
    path.write_text(textwrap.dedent(body), encoding="utf-8")
    path.chmod(0o755)


class BarePfyNoDaemon(unittest.TestCase):
    def setUp(self):
        import tempfile

        parent = ROOT / "tmp"
        parent.mkdir(parents=True, exist_ok=True)
        self.home = Path(tempfile.mkdtemp(prefix="pfy-nodeamon-", dir=str(parent)))
        self.addCleanup(self._rm, self.home)
        self.state = self.home / "state"
        self.state.mkdir()
        self.bindir = self.home / "bin"
        self.bindir.mkdir()
        # Host PATH may contain llama-server, shimmy, or ollama. Mirror
        # /bin and /usr/bin without those engines so the hint is the fake ollama.
        self.realbin = self.home / "real"
        self.realbin.mkdir()
        hidden = {
            "ollama",
            "ft",
            "freetoken",
            "llama-server",
            "llama-swap",
            "shimmy",
            "grok",
            "opencode",
            "hermes",
            "claude",
            "codex",
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
        self.argv_log = self.home / "ollama-argv"
        self.block_log = self.home / "curl-blocked"
        self.closed = "http://127.0.0.1:%d" % _closed_port()
        _exe(
            self.bindir / "ollama",
            f"""\
            #!/bin/bash
            printf '%s\\n' "$*" >> "{self.argv_log}"
            exit 0
            """,
        )
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

    @staticmethod
    def _rm(path: Path) -> None:
        import shutil

        shutil.rmtree(path, ignore_errors=True)

    def _env(self, **extra) -> dict:
        env = os.environ.copy()
        for key in (
            "PFY_START_ENGINE",
            "PFY_START_ENGINE_FLAG",
            "PFY_LOCAL_RUNTIME",
            "LOCAL_OPENAI_BASE_URL",
            "OPENAI_BASE_URL",
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
                "PFY_OLLAMA_BASE": self.closed,
                "OLLAMA_ARGV": str(self.argv_log),
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
            out, err = proc.communicate(timeout=90)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGTERM)
            try:
                out, err = proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)
                out, err = proc.communicate()
            raise subprocess.TimeoutExpired(proc.args, 90, output=out, stderr=err)
        return subprocess.CompletedProcess(proc.args, proc.returncode, out, err)

    def _argv(self) -> str:
        if not self.argv_log.is_file():
            return ""
        return self.argv_log.read_text(encoding="utf-8")

    def _assert_no_host_ollama(self):
        if not self.block_log.is_file():
            return
        self.assertNotIn("11434", self.block_log.read_text(encoding="utf-8"))

    def _assert_hint(self, proc):
        blob = proc.stdout + proc.stderr
        hints = [
            line
            for line in blob.splitlines()
            if "ollama down" in line.lower() and "ollama serve" in line
        ]
        self.assertEqual(hints, ["ollama down: ollama serve"], blob)
        self.assertNotIn("serve", self._argv().split(), blob)
        self._assert_no_host_ollama()
        self.assertEqual(proc.returncode, 0, blob)

    def test_bare_up_start_and_board_do_not_serve(self):
        self._assert_hint(self._run([]))
        self.argv_log.unlink(missing_ok=True)
        self._assert_hint(self._run(["up"]))
        self.argv_log.unlink(missing_ok=True)
        self._assert_hint(self._run(["start"]))
        self.argv_log.unlink(missing_ok=True)
        self._assert_hint(self._run(["board"]))

    def test_pfy_start_engine_records_serve(self):
        proc = self._run([], self._env(PFY_START_ENGINE="1"))
        blob = proc.stdout + proc.stderr
        self.assertIn("\nserve\n", "\n" + self._argv())
        self._assert_no_host_ollama()
        self.assertNotIn("ollama down:", blob)

    def test_start_engine_flag_records_serve(self):
        proc = self._run(["--start-engine"])
        blob = proc.stdout + proc.stderr
        self.assertIn("serve", self._argv().split(), blob)
        self._assert_no_host_ollama()
        self.assertNotIn("ollama down:", blob)


if __name__ == "__main__":
    unittest.main()
