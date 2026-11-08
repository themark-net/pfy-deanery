import json
import unittest
from pathlib import Path


class OllamaVerdictShapeTest(unittest.TestCase):
    def test_verdict_and_receipt_fields(self):
        verdict = json.loads(
            Path("eval/integrate/ollama/VERDICT.json").read_text(encoding="utf-8")
        )
        self.assertEqual(verdict["metric"], "http_status")
        self.assertEqual(verdict["threshold"], 200)
        self.assertEqual(verdict["value_gate"], "pass")
        self.assertEqual(verdict["modularity_gate"], "pass")
        self.assertEqual(verdict["proposed_stage"], "I3")
        script = Path("eval/integrate/ollama/run-on-main.sh").read_text(encoding="utf-8")
        for key in ("slug", "run_kind", "main_sha", "outcome", "tool_version", "did"):
            self.assertIn(key, script)
        self.assertIn("pipeline", script)


if __name__ == "__main__":
    unittest.main()
