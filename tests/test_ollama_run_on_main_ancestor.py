import unittest
from pathlib import Path


class OllamaRunOnMainAncestorTest(unittest.TestCase):
    def test_script_requires_ancestor_of_origin_main(self):
        text = Path("eval/integrate/ollama/run-on-main.sh").read_text(encoding="utf-8")
        self.assertIn("origin/main", text)
        self.assertIn("merge-base", text)
        self.assertIn("ancestor", text)
        self.assertIn("receipt", text)


if __name__ == "__main__":
    unittest.main()
