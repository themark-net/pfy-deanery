"""Entry 149 must publish the test count the module actually defines.

The smoke line still says 18 stub tests. tests/test_x_intake_smoke_149.py
has more test methods. A reader who trusts the entry under-counts the suite.
The dated automation handoff is the record of that day and is not this check.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "sources" / "entries" / "149-mempalace.md"
MODULE = ROOT / "tests" / "test_x_intake_smoke_149.py"
COUNT_RE = re.compile(r"tests\.test_x_intake_smoke_149` \((\d+) stub tests;")
METHOD_RE = re.compile(r"^    def test_", re.M)


class Entry149CountTests(unittest.TestCase):
    def test_published_count_matches_methods(self):
        """Fail: the Smoke line's stub-test count is not the method count.
        Recovery: that integer equals the number of test methods.
        A missing count, or a count that includes helpers, fails too."""
        text = ENTRY.read_text(encoding="utf-8")
        match = COUNT_RE.search(text)
        self.assertIsNotNone(match, "entry lost the published stub-test count")
        published = int(match.group(1))
        methods = METHOD_RE.findall(MODULE.read_text(encoding="utf-8"))
        self.assertGreater(len(methods), 0)
        self.assertEqual(published, len(methods))


if __name__ == "__main__":
    unittest.main()
