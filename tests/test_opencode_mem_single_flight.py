import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/opencode-mem/run-on-main.sh"


class OpenCodeMemSingleFlightTest(unittest.TestCase):
    def test_second_start_exits_2_and_names_push_flock(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("opencode-mem.dispatched", text)
        self.assertIn("exit 2", text)
        self.assertIn("flock", text)
        self.assertIn("model_lock.sh", text)
        self.assertNotIn("ollama pull", text)
        receipt_writes = [
            line
            for line in text.splitlines()
            if "receipt" in line and (">" in line or "write" in line.lower())
        ]
        self.assertTrue(text.strip().startswith("#!"))
        self.assertIn("exit 2", text[: text.find("receipt") if "receipt" in text else len(text)] + text)
