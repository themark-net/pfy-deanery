"""Issue #25 catalog text: the Laguna lab stays unchecked until a receipt exists."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOD = ROOT / "docs/ops/laguna-local-dod.md"
ENTRY = ROOT / "sources/entries/073-laguna-s-2-1.md"
PULL_BOX = "- [ ] `ollama pull` / llama.cpp load succeeds; one completion via OpenAI-compatible API"


class LagunaSmokeNoteTests(unittest.TestCase):
    def test_pull_box_stays_open_and_no_weights_are_tracked(self):
        dod = DOD.read_text(encoding="utf-8")
        entry = ENTRY.read_text(encoding="utf-8")
        self.assertIn(PULL_BOX, dod)
        self.assertNotIn("- [x] `ollama pull`", dod)
        self.assertIn("did not pull weights", entry)
        tracked = subprocess.run(
            ["git", "ls-files"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.lower()
        self.assertNotIn(".gguf", tracked)
        self.assertNotIn("laguna-s-2.1", tracked)


if __name__ == "__main__":
    unittest.main()
