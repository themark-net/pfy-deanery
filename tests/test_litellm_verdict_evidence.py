import json
import unittest
from pathlib import Path


class TestLitellmVerdictEvidence(unittest.TestCase):
    def test_verdict_and_evidence_line(self):
        verdict = json.loads(
            Path("eval/integrate/litellm/VERDICT.json").read_text(encoding="utf-8")
        )
        self.assertIn("metric", verdict)
        self.assertIn("threshold", verdict)
        self.assertEqual(verdict["value_gate"], "pass")
        self.assertEqual(verdict["modularity_gate"], "pass")
        self.assertEqual(verdict["proposed_stage"], "I3")
        card = Path("data/stages/litellm.json").read_text(encoding="utf-8")
        self.assertIn("receipt:eval/integrate/litellm/receipt.json", card)
        parsed = json.loads(card)
        self.assertNotIn("tier_ceiling", json.dumps(verdict))
        self.assertIn("integration_stage", parsed)


if __name__ == "__main__":
    unittest.main()
