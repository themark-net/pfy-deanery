import unittest
from pathlib import Path

SCRIPT = Path("eval/integrate/codebase-memory-mcp/run-on-main.sh")


class ReceiptRunKindTest(unittest.TestCase):
    def test_script_records_pipeline_run_kind(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("codebase-memory-mcp", text)
        self.assertIn('"pipeline"', text.replace("'", '"'))
        self.assertNotIn("run_kind=gate", text.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()
