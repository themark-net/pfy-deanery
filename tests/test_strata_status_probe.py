import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "strata" / "run-on-main.sh"


class StrataStatusProbeTest(unittest.TestCase):
    def test_status_request_does_not_start_or_download(self):
        text = SCRIPT.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("PFY_STRATA_BASE", text)
        self.assertIn("status", lowered)
        self.assertNotIn("ollama pull", lowered)
        self.assertNotIn("systemctl", lowered)
        for banned in ("strata serve", "download weights", "wget ", "curl -o"):
            self.assertNotIn(banned, lowered)

    def test_timeout_is_not_a_pass_and_generate_is_locked(self):
        text = SCRIPT.read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("timeout", lowered)
        generate_at = lowered.find("generate")
        if generate_at >= 0:
            window = lowered[max(0, generate_at - 400): generate_at + 80]
            self.assertIn("model_lock.sh", window)


if __name__ == "__main__":
    unittest.main()
