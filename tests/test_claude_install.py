"""Claude installer is one registry line, shared by CLI stub and Attach (T-0104)."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import attach, registry  # noqa: E402

INSTALL = "curl -fsSL https://claude.ai/install.sh | bash"
PFY = ROOT / "scripts" / "pfy"


class ClaudeInstallTests(unittest.TestCase):
    def test_registry_setup_and_attach_share_the_installer(self):
        row = next(h for h in registry.load_harnesses(ROOT)["harnesses"] if h["id"] == "claude-code")
        self.assertEqual(row["setup"], INSTALL)
        prof = attach.profile("claude-code", ROOT)
        self.assertEqual(prof["next_install"], INSTALL)

    def test_missing_binary_next_step_is_the_installer(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = attach.open_session(
                "claude",
                ROOT=ROOT,
                STATE=Path(tmp),
                which_bin=lambda *a: "",
                live_openai_base=lambda: ("", {"engine": "none", "status": "missing"}),
                inspect_models=lambda b: [],
                record_sidecar_pid=lambda *a: None,
                record_last_verb=lambda *a: None,
                pid_alive=lambda p: False,
                root_dir=ROOT,
            )
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["next_step"], INSTALL)

    def test_cli_stub_reads_setup_from_the_registry(self):
        text = PFY.read_text(encoding="utf-8")
        stub = text.split("FAIL attach -- claude missing", 1)[1].split("exit 2", 1)[0]
        self.assertIn("json_field setup claude-code", stub)
        self.assertNotIn("npm install", stub)
        self.assertNotIn("install.sh | bash", stub)


if __name__ == "__main__":
    unittest.main()
