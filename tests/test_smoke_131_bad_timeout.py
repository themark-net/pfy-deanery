"""smoke_131_133 exits 2 before the entry when PFY_XINTAKE_TIMEOUT is set and is not a finite number of seconds > 0.

Unset or empty still reaches the jah prereq miss. A bad value names PFY_XINTAKE_TIMEOUT and is not reported as a missing jah.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = "examples/x-intake-local/smoke_131_133.py"
JAH_MISS = "jah not found ($JAH_BIN, tmp/jevagentharness/.venv/bin/jah, PATH); see the handoff"


class BadTimeoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory(prefix="pfy-smoke131-timeout-")
        self.base = Path(self._td.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.path = self.base / "path"
        self.path.mkdir()
        self.receipts = self.base / "receipts"
        self.receipts.mkdir()

    def tearDown(self) -> None:
        self._td.cleanup()

    def run_smoke(self, timeout: str | None) -> tuple[int, dict]:
        env = os.environ.copy()
        for key in list(env):
            if key.startswith(("JAH_", "AI_MEMORY_", "HSON_")) or key == "PFY_XINTAKE_TIMEOUT":
                env.pop(key, None)
        env["HOME"] = str(self.home)
        env["PATH"] = str(self.path)
        env["PFY_SMOKE_RECEIPT_DIR"] = str(self.receipts)
        if timeout is not None:
            env["PFY_XINTAKE_TIMEOUT"] = timeout
        proc = subprocess.run(
            [sys.executable, SCRIPT, "--entry", "jah"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertNotIn("Traceback", proc.stderr + proc.stdout)
        receipt_path = self.receipts / "jah" / "latest.json"
        self.assertTrue(receipt_path.is_file(), proc.stdout + proc.stderr)
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(receipt["exit_code"], proc.returncode)
        return proc.returncode, receipt

    def test_bad_timeout_exits_2_before_jah_lookup(self) -> None:
        for bad in ("abc", "0", "-1", "nan", "inf"):
            with self.subTest(timeout=bad):
                code, receipt = self.run_smoke(bad)
                self.assertEqual(code, 2, receipt)
                self.assertIn("PFY_XINTAKE_TIMEOUT", receipt["reason"])
                self.assertNotIn("jah not found", receipt["reason"])
                self.assertNotIn("checks", receipt)

    def test_unset_or_empty_still_reports_missing_jah(self) -> None:
        for value in (None, ""):
            with self.subTest(timeout=value):
                code, receipt = self.run_smoke(value)
                self.assertEqual(code, 2, receipt)
                self.assertEqual(receipt["reason"], JAH_MISS)
