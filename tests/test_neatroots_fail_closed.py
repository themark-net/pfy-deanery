import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/neatroots/run-on-main.sh"

class TestNeatrootsFailClosed(unittest.TestCase):
    def test_script_declares_fail_closed_timeout(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("60", text)
        self.assertIn("timeout", text.lower())
        self.assertIn("exit 2", text)
        self.assertRegex(text, r"receipt")

if __name__ == "__main__":
    unittest.main()
