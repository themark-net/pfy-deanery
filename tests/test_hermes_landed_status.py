"""The Hermes bake-off bullet must use the landed status.

docs/PENDING-HANDOFF.md still says the 2026-10-19 branch lands on main.
docs/eval/HERMES-EVAL-HANDOFF.md says it landed. A future-tense bullet
sends the next reader to gate a branch that is already on main.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PENDING = ROOT / "docs" / "PENDING-HANDOFF.md"
EVAL = ROOT / "docs" / "eval" / "HERMES-EVAL-HANDOFF.md"
MARKER = "## 2026-10-19: Hermes Agent bake-off"


def _hermes_section(text: str) -> str:
    start = text.index(MARKER)
    rest = text[start + len(MARKER):]
    nxt = rest.find("\n## ")
    return rest if nxt < 0 else rest[:nxt]


class HermesLandedStatusTests(unittest.TestCase):
    def test_pending_bullet_matches_landed_handoff(self):
        """Fail: the 2026-10-19 bullet says Lands on main while the eval
        handoff says Landed on main.
        Recovery: that bullet says Landed on. Other sections stay as they are.
        If the eval handoff no longer says Landed on main, this check fails
        closed instead of inventing a status."""
        eval_text = EVAL.read_text(encoding="utf-8")
        self.assertIn("**Status (2026-10-30 PT):** Landed on main.", eval_text)
        section = _hermes_section(PENDING.read_text(encoding="utf-8"))
        self.assertNotIn("Lands on", section)
        self.assertIn("Landed on", section)


if __name__ == "__main__":
    unittest.main()
