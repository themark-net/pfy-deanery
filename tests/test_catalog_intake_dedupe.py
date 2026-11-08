"""Intake dedupe: same source, same line. A duplicate does not write a second card."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_intake_dedupe.py"


def run(root, source, write=False):
    cmd = ["python3", str(SCRIPT), source, "--root", str(root)]
    if write:
        cmd.append("--write-card")
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30)


class IntakeDedupeTest(unittest.TestCase):
    def test_same_source_is_new_once_then_a_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data" / "stages").mkdir(parents=True)
            first = run(root, "https://github.com/Example/Widget.git", write=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout.strip(), "new widget")
            card = json.loads((root / "data" / "stages" / "widget.json").read_text(encoding="utf-8"))
            self.assertEqual(card["integration_stage"], "I0")
            self.assertEqual(card["tier_ceiling"], "I0")
            self.assertEqual(card["github"], "https://github.com/example/widget")
            again = run(root, "Example/Widget", write=True)
            self.assertEqual(again.returncode, 0, again.stderr)
            self.assertEqual(again.stdout.strip(), "duplicate widget data/stages/widget.json")
            entries = root / "sources" / "entries"
            entries.mkdir(parents=True)
            (entries / "090-other-tool.md").write_text(
                "see https://github.com/acme/other-tool\n", encoding="utf-8"
            )
            posted = run(root, "https://github.com/acme/other-tool")
            self.assertEqual(posted.returncode, 0, posted.stderr)
            self.assertTrue(posted.stdout.startswith("duplicate other-tool "), posted.stdout)
            self.assertFalse((root / "data" / "stages" / "other-tool.json").exists())
            fresh = run(root, "Brand New Tool", write=True)
            self.assertEqual(fresh.stdout.strip(), "new brand-new-tool")
            repeat = run(root, "Brand New Tool")
            self.assertEqual(repeat.stdout.strip(), "duplicate brand-new-tool data/stages/brand-new-tool.json")
            self.assertEqual(run(root, "Brand New Tool").stdout, repeat.stdout)
