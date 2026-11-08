import json
import unittest
from pathlib import Path


class SponsioVerdictTest(unittest.TestCase):
    def test_verdict_fields(self):
        verdict = json.loads(
            Path("eval/integrate/sponsio/VERDICT.json").read_text()
        )
        self.assertEqual(verdict["metric"], "cached_wheel_fixture")
        self.assertEqual(verdict["threshold"], 1)
        self.assertTrue(verdict["value_gate"])
        self.assertTrue(verdict["modularity_gate"])
        self.assertEqual(verdict["proposed_stage"], "I3")


if __name__ == "__main__":
    unittest.main()
