import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/neatroots/run-on-main.sh"

class TestNeatrootsDoubleRun(unittest.TestCase):
    def test_marker_and_named_flock_stop_a_second_run(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("$HOME/DEVELOP/pfy-mentat/tmp/integrate2/neatroots.dispatched", text)
        self.assertIn("$HOME/DEVELOP/pfy-mentat/tmp/integrate2/neatroots.push.lock", text)
        self.assertIn("exit 2", text)
        self.assertIn("flock", text)

if __name__ == "__main__":
    unittest.main()
