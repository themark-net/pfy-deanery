"""SIGTERM during harnessrouter docker run removes the container with the real argv.

How this fails: the smoke dies on SIGTERM inside docker run, so docker rm
and docker volume rm never run, and no receipt is written.
How we recover: the logged arguments are exactly `rm -f pfy-hr-smoke` and
`volume rm -f pfy-hr-smoke`, the process exits 1, and the receipt reason
contains SIGTERM. A leading `--` is not that volume command.
"""
from __future__ import annotations

import json
import os
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "examples/x-intake-local/smoke_122_124.py"


def _write_exe(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


class HarnessRouterSigtermExactTests(unittest.TestCase):
    def test_sigterm_logs_the_real_rm_and_volume_rm(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-hr-sigterm-exact-") as raw:
            td = Path(raw)
            home = td / "home"
            home.mkdir()
            calls = td / "calls"
            ready = td / "ready"
            child_pid = td / "child.pid"
            docker = td / "docker"
            receipts = td / "receipts"
            _write_exe(
                docker,
                "#!/bin/sh\n"
                f"echo \"$@\" >> {shlex.quote(str(calls))}\n"
                "case \" $* \" in\n"
                "  *\" version \"*) exit 0 ;;\n"
                "  *\" container inspect \"*) exit 1 ;;\n"
                "  *\" volume inspect \"*) exit 1 ;;\n"
                "  *\" volume rm \"*) exit 0 ;;\n"
                "  *\" rm \"*) exit 0 ;;\n"
                "  *\" run \"*)\n"
                f"    echo $$ > {shlex.quote(str(child_pid))}\n"
                f"    touch {shlex.quote(str(ready))}\n"
                "    sleep 60\n"
                "    exit 0 ;;\n"
                "esac\n"
                "exit 0\n",
            )
            env = os.environ.copy()
            env["HOME"] = str(home)
            env["DOCKER_BIN"] = str(docker)
            env["PFY_SMOKE_RECEIPT_DIR"] = str(receipts)
            env["PFY_XINTAKE_TIMEOUT"] = "30"
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", 0))
                env["HR_SMOKE_PORT"] = str(sock.getsockname()[1])
            proc = subprocess.Popen(
                [sys.executable, SCRIPT, "--entry", "harnessrouter"],
                cwd=str(ROOT),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
            try:
                deadline = time.time() + 20
                while time.time() < deadline and not ready.exists():
                    if proc.poll() is not None:
                        break
                    time.sleep(0.05)
                self.assertTrue(ready.exists(), "docker run never started")
                os.kill(proc.pid, signal.SIGTERM)
                try:
                    stdout, stderr = proc.communicate(timeout=20)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    stdout, stderr = proc.communicate(timeout=5)
                    self.fail("smoke ignored SIGTERM for 20s\n" + stdout + stderr)
            finally:
                if child_pid.exists():
                    try:
                        os.kill(int(child_pid.read_text().strip()), signal.SIGKILL)
                    except (OSError, ValueError):
                        pass
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGKILL)
                    proc.wait(timeout=5)
            self.assertEqual(proc.returncode, 1, stdout + stderr)
            self.assertNotIn("Traceback", stdout + stderr)
            lines = [
                line.strip()
                for line in (calls.read_text(encoding="utf-8") if calls.exists() else "").splitlines()
            ]
            self.assertIn("rm -f pfy-hr-smoke", lines)
            self.assertIn("volume rm -f pfy-hr-smoke", lines)
            self.assertNotIn("-- volume rm -f pfy-hr-smoke", lines)
            receipt_path = receipts / "harnessrouter" / "latest.json"
            self.assertTrue(receipt_path.is_file(), stdout + stderr)
            got = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertIn("SIGTERM", got.get("reason", ""))
            self.assertEqual(got.get("verdict"), "FAIL")


if __name__ == "__main__":
    unittest.main()
