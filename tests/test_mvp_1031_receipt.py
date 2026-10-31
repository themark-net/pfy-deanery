"""Behavior checks for the mvp-1031 red fixture and, later, the receipt checker.

No grok, no model, no network. Scratch stays under this worktree tmp/.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "eval" / "mvp-1031" / "fixture"
SCRATCH = ROOT / "tmp" / "mvp-eval-1031"
SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(SCRATCH)
tempfile.tempdir = str(SCRATCH)


class FixtureRedUntilSumTests(unittest.TestCase):
    def test_shipped_add_fails_and_sum_passes(self):
        # Fail: a fixture that already returns the sum would ship green and the demo would have nothing to fix.
        # Recover: keep add wrong in the tree; the same test file passes once add returns a + b.
        red = subprocess.run(
            [sys.executable, "-m", "unittest", "test_add"],
            cwd=FIXTURE,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(red.returncode, 0, red.stdout + red.stderr)
        self.assertIn("AssertionError", red.stderr)

        work = Path(tempfile.mkdtemp(prefix="fix-add-", dir=SCRATCH))
        try:
            shutil.copy(FIXTURE / "test_add.py", work / "test_add.py")
            (work / "add.py").write_text(
                "def add(a, b):\n    return a + b\n",
                encoding="utf-8",
            )
            green = subprocess.run(
                [sys.executable, "-m", "unittest", "test_add"],
                cwd=work,
                capture_output=True,
                text=True,
            )
            self.assertEqual(green.returncode, 0, green.stdout + green.stderr)
        finally:
            shutil.rmtree(work)


if __name__ == "__main__":
    unittest.main()
