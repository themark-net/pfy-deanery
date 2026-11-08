import json
import unittest
from pathlib import Path


class TestTasteSkillVerdict(unittest.TestCase):
    def test_proposed_i3_stays_off_the_card(self):
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
        self.assertEqual(card["integration_stage"], "I2")
        self.assertEqual(card["tier_ceiling"], "I1")
        evidence = card.get("evidence") or []
        self.assertFalse(
            any(isinstance(item, str) and item.strip().lower().startswith("receipt:") for item in evidence)
        )


if __name__ == "__main__":
    unittest.main()
