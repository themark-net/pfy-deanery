import json
import unittest
from pathlib import Path


class TestRepowiseVerdictMetric(unittest.TestCase):
    def test_metric_is_smoke_exit_zero(self):
        verdict = json.loads(Path("eval/integrate/repowise/VERDICT.json").read_text())
        metric = str(verdict["metric"]).lower()
        self.assertIn("smoke", metric)
        self.assertTrue(verdict["threshold"] in (0, "0"))
        self.assertEqual(verdict["value_gate"], "pass")
        self.assertEqual(verdict["modularity_gate"], "pass")
        self.assertEqual(verdict["proposed_stage"], "I3")
