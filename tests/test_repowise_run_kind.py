import json
import unittest
from pathlib import Path


class TestRepowiseRunKind(unittest.TestCase):
    def test_script_sets_pipeline_run_kind(self):
        text = Path("eval/integrate/repowise/run-on-main.sh").read_text()
        self.assertIn("pipeline", text)
        self.assertNotIn('run_kind": "gate"', text)
        self.assertIn("repowise", text)
