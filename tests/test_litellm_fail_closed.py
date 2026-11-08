import unittest
from pathlib import Path


class TestLitellmFailClosed(unittest.TestCase):
    def test_failures_do_not_write_a_receipt(self):
        text = Path("eval/integrate/litellm/run-on-main.sh").read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("timeout", lowered)
        self.assertIn("receipt.json", text)
        self.assertNotIn("timeout is a pass", lowered)
        self.assertIn("exit", lowered)


if __name__ == "__main__":
    unittest.main()
