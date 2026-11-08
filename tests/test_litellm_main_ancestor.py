import unittest
from pathlib import Path


class TestLitellmMainAncestor(unittest.TestCase):
    def test_ancestor_gate_precedes_receipt_write(self):
        text = Path("eval/integrate/litellm/run-on-main.sh").read_text(encoding="utf-8")
        ancestor = text.find("merge-base --is-ancestor")
        origin = text.find("origin/main")
        receipt = text.find("receipt.json")
        self.assertGreaterEqual(ancestor, 0)
        self.assertGreaterEqual(origin, 0)
        self.assertGreater(receipt, ancestor)


if __name__ == "__main__":
    unittest.main()
