#!/usr/bin/env python3
"""Missing dcg binary: deny the fallback list, allow ordinary commands."""
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "integrations" / "dcg" / "guard.sh"

DENY = [
    ["rm", "-rf", "/"],
    ["git", "push", "--force"],
    ["git", "reset", "--hard"],
    ["git", "clean", "-fd"],
]
ALLOW = [
    ["ls"],
    ["git", "status"],
    ["pytest"],
    ["git", "push", "origin", "main"],
]


class TestFailSafe(unittest.TestCase):
    def _run(self, argv):
        env = os.environ.copy()
        env.pop("PFY_DCG_DISABLE", None)
        env["PFY_DCG_BIN"] = "/nonexistent/dcg"
        return subprocess.run(
            ["bash", str(GUARD), *argv],
            env=env,
            capture_output=True,
            timeout=5,
        )

    def test_destructive_patterns_exit_126(self):
        self.assertTrue(GUARD.is_file(), "guard.sh missing")
        for argv in DENY:
            proc = self._run(argv)
            self.assertEqual(proc.returncode, 126, argv)
            self.assertIn(b"dcg-fallback", proc.stderr)

    def test_ordinary_commands_exit_0(self):
        self.assertTrue(GUARD.is_file(), "guard.sh missing")
        for argv in ALLOW:
            proc = self._run(argv)
            self.assertEqual(proc.returncode, 0, argv)
            self.assertIn(b"dcg-fallback", proc.stderr)


if __name__ == "__main__":
    unittest.main()
