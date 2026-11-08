import unittest
from pathlib import Path


REQUIRED = [
    "slug",
    "run_kind",
    "main_sha",
    "log_path",
    "started",
    "finished",
    "outcome",
    "tool_version",
    "did",
    "pipeline",
]


class TestHeadsonReceiptFields(unittest.TestCase):
    def test_script_emits_pipeline_receipt_fields(self):
        script = Path("eval/integrate/headson/run-on-main.sh").read_text()
        for field in REQUIRED:
            self.assertIn(field, script)
        self.assertNotIn('run_kind", "gate"', script)
        self.assertNotIn("run_kind=gate", script)


if __name__ == "__main__":
    unittest.main()
