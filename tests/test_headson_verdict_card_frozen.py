import json
import unittest
from pathlib import Path


class TestHeadsonVerdictCardFrozen(unittest.TestCase):
    def test_verdict_proposes_i3_without_card_write_in_script(self):
        verdict = json.loads(
            Path("eval/integrate/headson/VERDICT.json").read_text()
        )
        self.assertEqual(verdict["metric"], "headson_preview_exit")
        self.assertEqual(verdict["threshold"], 0)
        self.assertEqual(verdict["value_gate"], "pass")
        self.assertEqual(verdict["modularity_gate"], "pass")
        self.assertEqual(verdict["proposed_stage"], "I3")
        script = Path("eval/integrate/headson/run-on-main.sh").read_text()
        self.assertNotIn("data/stages/headson.json", script)


if __name__ == "__main__":
    unittest.main()
