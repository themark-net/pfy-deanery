"""T-0002 rollup cites the new receipts and does not invent a score."""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HEADING = "## Aggregate synthesis rollup (2026-10-30) - T-0002"


class ScoringRollupTests(unittest.TestCase):
    def test_october_rollup_cites_receipts_and_adds_no_score(self):
        """Fail: the October section assigns an overall number, drops the
        Pipecat receipt, or names a tools.json version other than the file.
        Recovery: delete the invented number and point the version phrase at
        data/tools.json. Do not rescore the July table."""
        text = (ROOT / "docs" / "scoring-summary.md").read_text(encoding="utf-8")
        self.assertIn("## Aggregate synthesis rollup (2026-07-30)", text)
        start = text.index(HEADING)
        section = text[start:]
        self.assertIn("sources/entries/150-pipecat.md", section)
        self.assertIn("No new S1-S4", section)
        self.assertIn("Not a Feature GO", section)
        self.assertIsNone(re.search(r"overall\s*[:=]\s*\d", section, re.I))
        version = re.search(r"tools\.json` version stays (\d+\.\d+\.\d+)", section)
        self.assertIsNotNone(version)
        tools = json.loads((ROOT / "data" / "tools.json").read_text(encoding="utf-8"))
        self.assertEqual(tools["version"], version.group(1))
        aggregates = (ROOT / "sources" / "aggregates.md").read_text(encoding="utf-8")
        self.assertIn("No aggregates logged yet", aggregates)
        todo = (ROOT / "docs" / "TODO.md").read_text(encoding="utf-8")
        active = todo.split("## Active (sorted", 1)[1].split("## Done", 1)[0]
        done = todo.split("## Done", 1)[1]
        self.assertNotIn("| T-0002 |", active)
        self.assertIn("| T-0002 |", done)


if __name__ == "__main__":
    unittest.main()
