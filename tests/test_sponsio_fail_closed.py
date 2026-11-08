import unittest
from pathlib import Path


class SponsioFailClosedTest(unittest.TestCase):
    def test_no_network_install_and_ancestor_guard(self):
        text = Path("eval/integrate/sponsio/run-on-main.sh").read_text()
        self.assertNotIn("pip install", text)
        self.assertIn("origin/main", text)
        self.assertIn("is-ancestor", text)
        self.assertIn("receipt", text)


if __name__ == "__main__":
    unittest.main()
