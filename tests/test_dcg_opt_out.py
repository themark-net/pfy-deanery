#!/usr/bin/env python3
"""Explicit PFY_DCG_DISABLE=1 is the only opt-out."""
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "integrations" / "dcg" / "guard.sh"


def _run(value):
    env = os.environ.copy()
    env["PFY_DCG_BIN"] = "/nonexistent/dcg"
    if value is None:
        env.pop("PFY_DCG_DISABLE", None)
    else:
        env["PFY_DCG_DISABLE"] = value
    return subprocess.run(
        ["bash", str(GUARD), "rm", "-rf", "/"],
        env=env,
        capture_output=True,
        timeout=5,
    )


class TestOptOut(unittest.TestCase):
    def test_disable_one_allows_and_logs(self):
        self.assertTrue(GUARD.is_file(), "guard.sh missing")
        proc = _run("1")
        self.assertEqual(proc.returncode, 0)
        self.assertIn(b"dcg-disabled", proc.stderr)
        self.assertNotIn(b"dcg-fallback", proc.stderr)

    def test_other_values_still_deny(self):
        self.assertTrue(GUARD.is_file(), "guard.sh missing")
        for value in (None, "0", "true", ""):
            proc = _run(value)
            self.assertEqual(proc.returncode, 126, repr(value))
            self.assertIn(b"dcg-fallback", proc.stderr)


if __name__ == "__main__":
    unittest.main()
