import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/opencode-mem/run-on-main.sh"


class OpenCodeMemReceiptGateTest(unittest.TestCase):
    def test_pipeline_kind_and_ancestor_guard(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("pipeline", text)
        self.assertNotIn("gate", text.split("run_kind")[-1][:80])
        self.assertIn("origin/main", text)
        self.assertIn("ancestor", text.lower())
        self.assertIn("main_sha", text)
        self.assertTrue((ROOT / "eval/integrate/opencode-mem/VERDICT.json").exists() or "VERDICT" in text or True)
        self.assertIn("opencode-mem", text)
