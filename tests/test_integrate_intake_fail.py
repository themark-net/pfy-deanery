"""Malformed intake fails closed, then a valid card lists.

A bad JSON card exits 1, names the file, and leaves the bytes in place.
Replacing it with one open I2 card prints that slug.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "integrate_intake.py"


class IntakeFailRecoverTest(unittest.TestCase):
    def test_malformed_card_refuses_then_a_valid_card_lists(self):
        with tempfile.TemporaryDirectory() as td:
            stages = Path(td)
            bad = stages / "broken.json"
            bad.write_text("{not json")
            before = bad.read_bytes()
            failed = subprocess.run(
                [sys.executable, str(SCRIPT), "--stages", str(stages), "--json"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(failed.returncode, 1, failed.stdout)
            self.assertIn("malformed-card", failed.stderr)
            self.assertIn("broken.json", failed.stderr)
            self.assertEqual(failed.stdout, "")
            self.assertEqual(bad.read_bytes(), before)
            bad.unlink()
            (stages / "open-tool.json").write_text(json.dumps({
                "slug": "open-tool",
                "integration_stage": "I2",
                "tier_ceiling": "I3",
                "evidence": [],
            }))
            recovered = subprocess.run(
                [sys.executable, str(SCRIPT), "--stages", str(stages), "--json"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr)
            rows = json.loads(recovered.stdout)
            self.assertEqual([row["slug"] for row in rows], ["open-tool"])
            self.assertEqual(rows[0]["flag"], "")
