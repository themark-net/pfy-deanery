import unittest
from pathlib import Path


class OllamaRunOnMainLockTest(unittest.TestCase):
    def test_script_names_lane_marker_and_uses_model_lock(self):
        script = Path("eval/integrate/ollama/run-on-main.sh")
        text = script.read_text(encoding="utf-8")
        self.assertIn("scripts/model_lock.sh", text)
        self.assertIn("$HOME/DEVELOP/pfy-mentat/tmp/integrate2/ollama.dispatched", text)
        self.assertIn("flock", text)
        self.assertNotIn("ollama pull", text)
        self.assertNotIn("systemctl", text)


if __name__ == "__main__":
    unittest.main()
