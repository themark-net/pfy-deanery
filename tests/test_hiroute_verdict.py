import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
VERDICT = ROOT / "eval" / "integrate" / "hiroute" / "VERDICT.json"


class HirouteVerdictTest(unittest.TestCase):
    def test_verdict_proposes_i3_with_passing_gates(self):
        data = json.loads(VERDICT.read_text(encoding="utf-8"))
        self.assertTrue(str(data["metric"]).strip())
        self.assertTrue(str(data["threshold"]).strip())
        self.assertEqual(data["value_gate"], "pass")
        self.assertEqual(data["modularity_gate"], "pass")
        self.assertEqual(data["proposed_stage"], "I3")


if __name__ == "__main__":
    unittest.main()
