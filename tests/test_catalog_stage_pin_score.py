"""ATG evidence must keep the pin SHA and the score SHA.

Recompute turns pin:FULLSHA into the word pin and drops scored:SHORT.
The I2 score was taken at 86d1b890, not at the main pin. Losing scored:
hides that those are different commits.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "pin:543e778ed24fbf3fc903eb961feb627039019832"
SCORED = "scored:86d1b890"


def _load():
    spec = importlib.util.spec_from_file_location(
        "catalog_stage_eval_pin", ROOT / "scripts" / "catalog_stage_eval.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CatalogStagePinScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_atg_evidence_keeps_pin_and_scored_shas(self):
        """Fail: recompute drops pin:FULLSHA and scored:SHORT.
        Recovery: both stay on the ATG evidence list.
        A pin or scored token that is not hex is not kept.
        The stage file on disk is not written."""
        stages = ROOT / "data" / "tool_integration_stages.json"
        before = stages.read_bytes()
        by = {row["name"]: row for row in self.mod.evaluations()}
        evidence = by["Atomic Task Graph (ATG)"]["evidence"]
        self.assertIn(PIN, evidence)
        self.assertIn(SCORED, evidence)
        found = self.mod.evidence_for(
            "Atomic Task Graph (ATG)",
            {
                "pin": PIN.split(":", 1)[1],
                "evidence": [PIN, "pin:not-a-sha", SCORED, "scored:nope"],
            },
            "",
            set(),
        )
        self.assertIn(PIN, found)
        self.assertIn(SCORED, found)
        self.assertNotIn("pin:not-a-sha", found)
        self.assertNotIn("scored:nope", found)
        self.assertEqual(stages.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
