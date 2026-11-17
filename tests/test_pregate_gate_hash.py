#!/usr/bin/env python3
"""gate-hash fails a mode change, a new tests/*.pth, and a gitignored payload.

A clean tree and cache junk (__pycache__, *.pyc) still pass. The helper is
scripts/pregate_gate_hash.py, the same program pregate.sh runs.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "pregate_gate_hash.py"


class PregateGateHashTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp(prefix="pgh-"))
        subprocess.check_call(["git", "init", "-q"], cwd=self.repo)
        subprocess.check_call(["git", "config", "user.email", "dev@example.com"], cwd=self.repo)
        subprocess.check_call(["git", "config", "user.name", "dev"], cwd=self.repo)
        (self.repo / "tests").mkdir()
        (self.repo / "tests" / "t.py").write_text("x = 1\n", encoding="utf-8")
        (self.repo / ".gitignore").write_text("secret.pth\n__pycache__/\n*.pyc\n", encoding="utf-8")
        subprocess.check_call(["git", "add", "tests/t.py", ".gitignore"], cwd=self.repo)
        subprocess.check_call(["git", "commit", "-q", "-m", "init"], cwd=self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)

    def _run(self) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["BASE_SHA"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.repo, text=True
        ).strip()
        return subprocess.run(
            ["python3", str(HELPER)],
            cwd=self.repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_pregate_sh_calls_the_helper(self) -> None:
        src = (ROOT / "scripts" / "pregate.sh").read_text(encoding="utf-8")
        self.assertIn('python3 "$SCRIPT_DIR/pregate_gate_hash.py"', src)

    def test_clean_tree_passes(self) -> None:
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS gate-hash", proc.stdout)

    def test_mode_change_fails(self) -> None:
        path = self.repo / "tests" / "t.py"
        path.chmod(path.stat().st_mode | stat.S_IXUSR)
        proc = self._run()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("mode changed vs HEAD: tests/t.py", proc.stdout)
        self.assertIn("100644 -> 100755", proc.stdout)

    def test_untracked_pth_fails(self) -> None:
        (self.repo / "tests" / "payload.pth").write_bytes(b"weights")
        proc = self._run()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("new vs HEAD (staged, untracked, or ignored): tests/payload.pth", proc.stdout)

    def test_ignored_pth_under_tests_fails(self) -> None:
        (self.repo / "tests" / "secret.pth").write_bytes(b"ignored-weights")
        proc = self._run()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("new vs HEAD (staged, untracked, or ignored): tests/secret.pth", proc.stdout)

    def test_pycache_does_not_fail(self) -> None:
        cache = self.repo / "tests" / "__pycache__"
        cache.mkdir()
        (cache / "t.cpython-313.pyc").write_bytes(b"cache")
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("PASS gate-hash", proc.stdout)

    def test_content_change_still_fails(self) -> None:
        (self.repo / "tests" / "t.py").write_text("x = 2\n", encoding="utf-8")
        proc = self._run()
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("modified vs HEAD: tests/t.py", proc.stdout)


if __name__ == "__main__":
    unittest.main()
