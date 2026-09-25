"""Exo installer is the registry setup line; start does not run it (T-0107)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import attach, registry  # noqa: E402

INSTALL = (
    "curl -fsSL https://raw.githubusercontent.com/exoharness/exo/main/setup.sh -o setup.sh"
    " && bash setup.sh"
)
PFY = ROOT / "scripts" / "pfy"


class ExoInstallTests(unittest.TestCase):
    def test_setup_is_the_installer_and_there_is_no_attach_profile(self):
        row = next(h for h in registry.load_harnesses(ROOT)["harnesses"] if h["id"] == "exo")
        self.assertEqual(row["setup"], INSTALL)
        self.assertIsNone(row.get("attach"))
        self.assertIsNone(attach.profile("exo", ROOT))
        self.assertEqual(registry.load_harnesses(ROOT).get("default_harness"), "grok")

    def test_cli_stub_reads_setup_from_the_registry(self):
        text = PFY.read_text(encoding="utf-8")
        stub = text.split("STUB harness: exo", 1)[1].split("exit 2", 1)[0]
        self.assertIn("json_field setup exo", stub)
        self.assertNotIn("setup.sh", stub)


if __name__ == "__main__":
    unittest.main()
