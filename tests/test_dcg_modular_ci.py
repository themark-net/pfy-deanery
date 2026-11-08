#!/usr/bin/env python3
"""dcg checks stay parallel and lock-free under Modular CI."""
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "integrations" / "dcg" / "guard.sh"


class TestModularCi(unittest.TestCase):
    def test_parallel_allows_do_not_serialize_or_lock(self):
        self.assertTrue(GUARD.is_file(), "guard.sh missing")
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env.pop("PFY_DCG_DISABLE", None)
            env["HOME"] = home
            env["TMPDIR"] = tmp
            env["PFY_DCG_BIN"] = "/nonexistent/dcg"
            commands = [["ls"], ["git", "status"]]
            procs = [
                subprocess.Popen(
                    ["bash", str(GUARD), *cmd],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                for cmd in commands
            ]
            started = time.monotonic()
            codes = []
            for proc in procs:
                try:
                    _out, err = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    self.fail("allow check waited on a serialized lane or lock")
                codes.append(proc.returncode)
                self.assertIn(b"dcg-fallback", err)
            elapsed = time.monotonic() - started
            self.assertEqual(codes, [0, 0])
            self.assertLess(elapsed, 3.0)
            locks = [p for p in Path(home).rglob("*")] + [p for p in Path(tmp).rglob("*")]
            self.assertEqual(locks, [])


if __name__ == "__main__":
    unittest.main()
