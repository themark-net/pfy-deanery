#!/usr/bin/env python3
"""run_tests.py exit status follows the module, not the runner.

How this fails: a failing module is reported as rc 0, so CI goes green.
Recovery: the receipt rc and the process exit stay nonzero, and the output
tail names the failure. A passing module stays rc 0.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "scripts" / "run_tests.py"


class RunTestsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pfy-run-"))
        tests = self.tmp / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_ok.py").write_text(
            "import unittest\n"
            "class Ok(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertEqual(1, 1)\n",
            encoding="utf-8",
        )
        (tests / "test_bad.py").write_text(
            "import unittest\n"
            "class Bad(unittest.TestCase):\n"
            "    def test_bad(self):\n"
            "        self.fail('boom')\n",
            encoding="utf-8",
        )
        self.env = os.environ.copy()
        self.env["TMPDIR"] = str(self.tmp)
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *modules: str) -> subprocess.CompletedProcess[str]:
        receipt = self.tmp / "receipt.json"
        proc = subprocess.run(
            [sys.executable, str(RUN), "--root", str(self.tmp), "--receipt", str(receipt), "-j", "2", *modules],
            cwd=self.tmp,
            env=self.env,
            capture_output=True,
            text=True,
        )
        proc.receipt_path = receipt  # type: ignore[attr-defined]
        return proc

    def test_passing_module_is_rc_zero(self) -> None:
        proc = self._run("tests.test_ok")
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn("PASS tests.test_ok", proc.stdout)
        data = json.loads((self.tmp / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(data["rc"], 0)
        self.assertEqual(data["modules"], ["tests.test_ok"])

    def test_failing_module_is_rc_nonzero_and_tail_is_printed(self) -> None:
        proc = self._run("tests.test_bad")
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertIn("FAIL tests.test_bad", proc.stdout)
        self.assertIn("boom", blob)
        data = json.loads((self.tmp / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(data["rc"], 1)
        self.assertEqual(data["results"][0]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
