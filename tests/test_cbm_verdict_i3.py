import json
import unittest
from pathlib import Path

VERDICT = Path("eval/integrate/codebase-memory-mcp/VERDICT.json")


class VerdictI3Test(unittest.TestCase):
    def test_verdict_gates_pass_at_i3(self):
        data = json.loads(VERDICT.read_text(encoding="utf-8"))
        self.assertEqual(data["metric"], "smoke_exit")
        self.assertEqual(data["threshold"], 0)
        self.assertEqual(data["value"], 0)
        self.assertEqual(data["value_gate"], "pass")
        self.assertEqual(data["modularity_gate"], "pass")
        self.assertEqual(data["proposed_stage"], "I3")


if __name__ == "__main__":
    unittest.main()
