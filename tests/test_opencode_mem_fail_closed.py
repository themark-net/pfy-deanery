import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/opencode-mem/run-on-main.sh"


class OpenCodeMemFailClosedTest(unittest.TestCase):
    def test_timeout_or_missing_probe_is_not_a_pass(self):
        text = SCRIPT.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("timeout", lowered)
        self.assertIn("receipt", lowered)
        self.assertNotRegex(lowered, r"timeout[^\n]{0,80}pass")
        self.assertIn("HOME", text)
        self.assertNotIn(".config/opencode", text.replace("~/.config/opencode", "").replace("$HOME/.config/opencode", ""))
