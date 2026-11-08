import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERDICT = ROOT / "eval/integrate/neatroots/VERDICT.json"

class TestNeatrootsVerdict(unittest.TestCase):
    def test_verdict_fields(self):
        data = json.loads(VERDICT.read_text(encoding="utf-8"))
        self.assertEqual(data["metric"], "offline_trace_check")
        self.assertEqual(data["threshold"], "exit_code_0")
        self.assertEqual(data["value_gate"], "pass")
        self.assertEqual(data["modularity_gate"], "pass")
        self.assertEqual(data["proposed_stage"], "I3")

if __name__ == "__main__":
    unittest.main()
