import json
import unittest
from pathlib import Path


class TestTasteSkillVerdict(unittest.TestCase):
    def test_proposed_i3_needs_the_linked_receipt(self):
        verdict = json.loads(
            Path("eval/integrate/taste-skill/VERDICT.json").read_text(encoding="utf-8")
        )
        self.assertTrue(str(verdict["metric"]).strip())
        self.assertIsInstance(verdict["threshold"], (int, float))
        self.assertNotIsInstance(verdict["threshold"], bool)
        self.assertEqual(verdict["value_gate"], "pass")
        self.assertEqual(verdict["modularity_gate"], "pass")
        self.assertEqual(verdict["proposed_stage"], "I3")
        card = json.loads(
            Path("data/stages/taste-skill.json").read_text(encoding="utf-8")
        )
        self.assertEqual(card["tier_ceiling"], "I3")
        # I3 only when apply linked the main-run receipt on the card.
        cites = "receipt:eval/integrate/taste-skill/receipt.json" in (card.get("evidence") or [])
        self.assertEqual(card["integration_stage"] == "I3", cites, card.get("evidence"))


if __name__ == "__main__":
    unittest.main()
