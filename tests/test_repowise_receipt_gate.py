import unittest
from pathlib import Path


class TestRepowiseReceiptGate(unittest.TestCase):
    def test_script_withholds_receipt_unless_ancestor_and_smoke_ok(self):
        text = Path("eval/integrate/repowise/run-on-main.sh").read_text()
        self.assertIn("origin/main", text)
        self.assertIn("smoke-repowise", text)
        self.assertIn("receipt.json", text)
        self.assertIn("ancestor", text)
