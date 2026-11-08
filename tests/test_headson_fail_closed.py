import unittest
from pathlib import Path


class TestHeadsonFailClosed(unittest.TestCase):
    def test_ancestry_and_timeout_block_receipt(self):
        script = Path("eval/integrate/headson/run-on-main.sh").read_text()
        self.assertIn("merge-base --is-ancestor", script)
        self.assertIn("origin/main", script)
        self.assertIn("timeout", script)
        self.assertNotIn("git fetch", script)
        self.assertNotIn("git pull", script)


if __name__ == "__main__":
    unittest.main()
