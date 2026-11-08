"""Missing Open Steps pack: the probe exits 2 and leaves the receipt untouched.

The child is eval/evq1107/open-steps/probe.py. HOME points at an empty temp
dir, so the cache checkout is absent. No network, no model, no hook binary.
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
PROBE = ROOT / "eval" / "evq1107" / "open-steps" / "probe.py"
RECEIPT = ROOT / "eval" / "evq1107" / "open-steps" / "results.json"


class MissingPackTest(unittest.TestCase):
    def test_missing_pack_exits_2_and_keeps_the_receipt(self) -> None:
        before = RECEIPT.read_bytes()
        with tempfile.TemporaryDirectory(prefix="pfy-open-steps-home-") as tmp:
            env = os.environ.copy()
            env["HOME"] = tmp
            env["XDG_CONFIG_HOME"] = str(Path(tmp) / "xdg-config")
            env["XDG_CACHE_HOME"] = str(Path(tmp) / "xdg-cache")
            env["XDG_DATA_HOME"] = str(Path(tmp) / "xdg-data")
            env["TMPDIR"] = str(Path(tmp) / "tmp")
            proc = subprocess.run(
                [sys.executable, str(PROBE)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            self.assertEqual(list(Path(tmp).rglob("*")), [])
        self.assertEqual(proc.returncode, 2, proc.stderr)
        doc = json.loads(proc.stdout)
        self.assertEqual(doc["error"], "stop-report.sh missing")
        self.assertNotIn("second_stop_still_blocked", doc)
        self.assertEqual(RECEIPT.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
