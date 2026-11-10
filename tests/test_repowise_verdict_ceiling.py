import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


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
            self.assertEqual(data.get("tier_ceiling"), "I3")

    def test_i3_only_with_a_cited_main_receipt(self):
        # The card may reach I3 only when apply linked the main-run receipt.
        data = json.loads((ROOT / "data/stages/repowise.json").read_text())
        cites = "receipt:eval/integrate/repowise/receipt.json" in (data.get("evidence") or [])
        self.assertEqual(data.get("integration_stage") == "I3", cites, data.get("evidence"))
