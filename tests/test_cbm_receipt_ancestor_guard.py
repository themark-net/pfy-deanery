import unittest
from pathlib import Path

SCRIPT = Path("eval/integrate/codebase-memory-mcp/run-on-main.sh")


class ReceiptAncestorGuardTest(unittest.TestCase):
    def test_script_withholds_receipt_unless_ancestor_and_smoke_ok(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("origin/main", text)
        self.assertIn("receipt.json", text)
        self.assertIn("merge-base", text)
        # receipt write must be gated; smoke failure path must be nonzero
        self.assertRegex(text, r"exit\s+[1-9]")
        write_at = text.find("receipt.json")
        guard_at = text.find("origin/main")
        self.assertGreater(guard_at, -1)
        self.assertGreater(write_at, guard_at)


if __name__ == "__main__":
    unittest.main()
