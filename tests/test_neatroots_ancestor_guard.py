import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/neatroots/run-on-main.sh"

class TestNeatrootsAncestorGuard(unittest.TestCase):
    def test_ancestor_guard_present(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("origin/main", text)
        self.assertIn("--is-ancestor", text)
        self.assertIn("receipt.json", text)

if __name__ == "__main__":
    unittest.main()
