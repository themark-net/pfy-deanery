"""Gemini installer is the registry setup line; start does not run it (T-0106)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import attach, registry  # noqa: E402

INSTALL = "npm install -g @google/gemini-cli"
PFY = ROOT / "scripts" / "pfy"


class GeminiInstallTests(unittest.TestCase):
    def test_setup_is_the_installer_and_there_is_no_attach_profile(self):
        row = next(h for h in registry.load_harnesses(ROOT)["harnesses"] if h["id"] == "gemini")
        self.assertEqual(row["setup"], INSTALL)
        self.assertIsNone(row.get("attach"))
        self.assertIsNone(attach.profile("gemini", ROOT))

    def test_cli_stub_reads_setup_from_the_registry(self):
        text = PFY.read_text(encoding="utf-8")
        stub = text.split("STUB harness: gemini", 1)[1].split("exit 2", 1)[0]
        self.assertIn("json_field setup gemini", stub)
        self.assertNotIn("npm install", stub)


if __name__ == "__main__":
    unittest.main()
