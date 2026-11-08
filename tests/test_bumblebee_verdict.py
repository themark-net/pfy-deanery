import json
import pathlib
import unittest


class BumblebeeVerdictTest(unittest.TestCase):
    def test_verdict_proposes_i3_and_card_bytes_stay(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        card = root / "data" / "stages" / "bumblebee.json"
        before = card.read_bytes()
        verdict = json.loads(
            (root / "eval" / "integrate" / "bumblebee" / "VERDICT.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(verdict["proposed_stage"], "I3")
        self.assertEqual(verdict["value_gate"], "pass")
        self.assertEqual(verdict["modularity_gate"], "pass")
        self.assertIn("metric", verdict)
        self.assertIn("threshold", verdict)
        self.assertTrue(str(verdict["metric"]).strip())
        self.assertTrue(str(verdict["threshold"]).strip())
        self.assertEqual(card.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
