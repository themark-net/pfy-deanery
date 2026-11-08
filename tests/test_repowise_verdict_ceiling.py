import json
import unittest
from pathlib import Path


class TestRepowiseVerdictCeiling(unittest.TestCase):
    def test_verdict_proposes_i3_off_card(self):
        verdict = json.loads(Path("eval/integrate/repowise/VERDICT.json").read_text())
        self.assertEqual(verdict.get("proposed_stage"), "I3")
        self.assertEqual(verdict.get("value_gate"), "pass")
        self.assertEqual(verdict.get("modularity_gate"), "pass")
        self.assertIn("metric", verdict)
        self.assertIn("threshold", verdict)
        card = Path("data/stages/repowise.json")
        if card.exists():
            data = json.loads(card.read_text())
            ceiling = str(data.get("tier_ceiling", "I1"))
            self.assertNotEqual(ceiling, "I3")
