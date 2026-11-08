"""CodeGuard probe walk: a scan root under a path named tmp still sees files.

The worktree lives under a directory named tmp. Skipping that name on the
absolute path drops every file and the probe would report a clean tree.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "codeguard" / "probe.py"


class CodeGuardWalkTests(unittest.TestCase):
    def test_walk_counts_a_file_when_an_ancestor_is_named_tmp(self) -> None:
        parent = Path(tempfile.mkdtemp(prefix="codeguard-walk-"))
        self.addCleanup(shutil.rmtree, parent, True)
        root = parent / "tmp" / "repo"
        root.mkdir(parents=True)
        (root / "sample.py").write_text("x = 1\n", encoding="utf-8")
        self.assertIn("tmp", root.parts)
        proc = subprocess.run(
            [sys.executable, str(PROBE), "--walk-check", str(root)],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "1")


if __name__ == "__main__":
    unittest.main()
