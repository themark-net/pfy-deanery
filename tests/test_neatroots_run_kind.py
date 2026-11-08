import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/neatroots/run-on-main.sh"

class TestNeatrootsRunKind(unittest.TestCase):
    def test_run_kind_is_pipeline(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"run_kind"', text)
        self.assertIn("pipeline", text)
        self.assertNotIn('"run_kind": "gate"', text)
        self.assertNotIn("'gate'", text)

if __name__ == "__main__":
    unittest.main()
