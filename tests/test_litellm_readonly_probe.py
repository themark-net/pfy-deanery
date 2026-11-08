import unittest
from pathlib import Path


class TestLitellmReadonlyProbe(unittest.TestCase):
    def test_script_does_not_touch_ollama_or_smoke(self):
        text = Path("eval/integrate/litellm/run-on-main.sh").read_text(encoding="utf-8")
        lowered = text.lower()
        for banned in (
            "smoke-litellm-ollama",
            "systemctl",
            "ollama serve",
            "ollama stop",
            "ollama pull",
        ):
            self.assertNotIn(banned, lowered)
        self.assertIn("scripts/model_lock.sh", text)
        self.assertIn("completion", lowered)
        self.assertNotIn("127.0.0.1:11434", text)
        self.assertNotIn("import litellm", text)
        self.assertIn("127.0.0.1:11435", text)
        self.assertIn("127.0.0.1:4000", text)


if __name__ == "__main__":
    unittest.main()
