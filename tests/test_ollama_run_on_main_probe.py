import unittest
from pathlib import Path


class OllamaRunOnMainProbeTest(unittest.TestCase):
    def test_readonly_version_get_fail_closed(self):
        text = Path("eval/integrate/ollama/run-on-main.sh").read_text(encoding="utf-8")
        self.assertIn("/api/version", text)
        self.assertIn("127.0.0.1:11434", text)
        self.assertIn("scripts/model_lock.sh", text)
        self.assertNotIn("/api/generate", text)
        self.assertNotIn("/api/chat", text)
        for forbidden in ("ollama pull", "ollama stop", "ollama restart", "ollama rm"):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
