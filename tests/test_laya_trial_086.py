"""Entry 086 trial fails closed when the Laya venv or server is missing. Cite #230."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT / "examples" / "typed-decisions-local" / "trial.py"


class LayaTrialFailClosedTests(unittest.TestCase):
    def test_missing_venv_exits_nonzero_with_reason(self):
        env = os.environ.copy()
        env["LAYA_PYTHON"] = "/no/such/laya-venv/bin/python"
        p = subprocess.run(
            [sys.executable, str(TRIAL), "--check"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        # Fail: missing venv looked like success → trial numbers would be invented.
        # Recover: keep exit non-zero and a reason that names the missing venv path.
        self.assertNotEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertNotEqual(p.returncode, 0)
        blob = json.loads(p.stdout.strip().splitlines()[-1])
        reason = blob.get("reason") or ""
        self.assertIn("no Laya venv", reason)
        self.assertIn("/no/such/laya-venv/bin/python", reason)

    def test_missing_server_with_no_start_fails_closed(self):
        py = ROOT / ".venv-laya" / "bin" / "python"
        if not os.access(py, os.X_OK):
            self.skipTest("Laya venv not present; venv-missing path is covered above")
        env = os.environ.copy()
        env["LAYA_PYTHON"] = str(py)
        with tempfile.TemporaryDirectory(prefix="laya-trial-") as td:
            receipt = Path(td) / "receipt.json"
            p = subprocess.run(
                [
                    sys.executable,
                    str(TRIAL),
                    "--no-start",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "1",
                    "--receipt",
                    str(receipt),
                ],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
        # Fail: unreachable laya-serve counted as a Laya win/skip with fake metrics.
        # Recover: --no-start on a dead port exits non-zero and names the health URL.
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("not reachable", p.stdout)
        self.assertIn("127.0.0.1:1", p.stdout)

    def test_shadow_no_start_fails_closed_and_writes_receipt(self):
        py = Path(os.environ.get("LAYA_PYTHON") or str(Path.home() / "DEVELOP/pfy-mentat/tmp/laya-trial/.venv-laya/bin/python"))
        if not os.access(py, os.X_OK):
            py = ROOT / ".venv-laya" / "bin" / "python"
        if not os.access(py, os.X_OK):
            self.skipTest("Laya venv not present; venv-missing path is covered above")
        env = os.environ.copy()
        env["LAYA_PYTHON"] = str(py)
        with tempfile.TemporaryDirectory(prefix="laya-shadow-") as td:
            receipt = Path(td) / "receipt.json"
            p = subprocess.run(
                [
                    sys.executable,
                    str(TRIAL),
                    "--shadow",
                    "--no-start",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "1",
                    "--receipt",
                    str(receipt),
                ],
                cwd=str(ROOT),
                env=env,
                capture_output=True,
                text=True,
            )
            # Fail: --shadow on a dead port invents catch/false-escalate numbers.
            # Recover: write a blocker receipt and exit 2.
            self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
            self.assertTrue(receipt.is_file(), p.stdout + p.stderr)
            blob = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(blob.get("verdict"), "FAIL_CANNOT_RUN")
        self.assertEqual(blob.get("mode"), "shadow")
        self.assertIn("not reachable", blob.get("reason") or "")
