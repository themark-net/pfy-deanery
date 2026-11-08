#!/usr/bin/env python3
"""A hung or broken dcg binary still denies the fallback list."""
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "integrations" / "dcg" / "guard.sh"


class TestTimeout(unittest.TestCase):
    def test_hung_binary_falls_back_and_denies(self):
        self.assertTrue(GUARD.is_file(), "guard.sh missing")
        with tempfile.TemporaryDirectory() as d:
            binary = Path(d) / "dcg"
            binary.write_text("#!/bin/sh\nexec sleep 30\n")
            binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env.pop("PFY_DCG_DISABLE", None)
            env["PFY_DCG_BIN"] = str(binary)
            proc = subprocess.run(
                ["bash", str(GUARD), "rm", "-rf", "/"],
                env=env,
                capture_output=True,
                timeout=8,
            )
            self.assertEqual(proc.returncode, 126, proc.stderr)
            self.assertIn(b"dcg-fallback", proc.stderr)
            self.assertIn(b"timed out", proc.stderr)

    def test_bad_json_falls_back_and_denies(self):
        self.assertTrue(GUARD.is_file(), "guard.sh missing")
        with tempfile.TemporaryDirectory() as d:
            binary = Path(d) / "dcg"
            binary.write_text("#!/bin/sh\nprintf '%s\\n' 'not-json'\nexit 1\n")
            binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env.pop("PFY_DCG_DISABLE", None)
            env["PFY_DCG_BIN"] = str(binary)
            proc = subprocess.run(
                ["bash", str(GUARD), "git", "reset", "--hard"],
                env=env,
                capture_output=True,
                timeout=8,
            )
            self.assertEqual(proc.returncode, 126, proc.stderr)
            self.assertIn(b"dcg-fallback", proc.stderr)


if __name__ == "__main__":
    unittest.main()
