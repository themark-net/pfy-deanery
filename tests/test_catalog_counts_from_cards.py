import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_counts.py"


class CountsFromCardsTest(unittest.TestCase):
    def test_progress_dashboard_and_coverage_come_from_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cards = tmp / "stages"
            cards.mkdir()
            (cards / "alpha.json").write_text(json.dumps({
                "id": "alpha", "stage": "I2", "intent": "inspect", "uses": [], "features": [], "tags": [],
            }))
            (cards / "beta.json").write_text(json.dumps({
                "id": "beta", "stage": "I1", "intent": "generate", "uses": [], "features": [], "tags": [],
            }))
            (cards / "_registry.json").write_text(json.dumps({
                "version": 1,
                "policy": "keep",
                "default_stage": "I0",
                "probe_path": "x",
                "handoff": "y",
                "coverage": "85 tools registered",
            }))
            registry = cards / "_registry.json"
            dashboard = tmp / "dashboard.latest.md"
            progress = tmp / "counts.latest.json"
            proc = subprocess.run(
                [
                    "python3", str(SCRIPT),
                    "--cards", str(cards),
                    "--registry", str(registry),
                    "--dashboard", str(dashboard),
                    "--progress", str(progress),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            body = progress.read_text()
            data = json.loads(body)
            self.assertEqual(data["card_count"], 2)
            self.assertEqual(data["i2_plus"], 1)
            self.assertEqual(data["coverage"], "2 tools registered")
            self.assertIn("inspect", data["per_intent"])
            self.assertIn("I2", data["per_stage"])
            self.assertIn("missing_fields", data)
            reg = json.loads(registry.read_text())
            self.assertEqual(reg["coverage"], "2 tools registered")
            self.assertEqual(reg["version"], 1)
            self.assertEqual(reg["policy"], "keep")
            self.assertEqual(reg["default_stage"], "I0")
            self.assertEqual(reg["probe_path"], "x")
            self.assertEqual(reg["handoff"], "y")
            text = dashboard.read_text()
            self.assertIn("2 tools registered", text)
            self.assertIn("alpha", text)
            self.assertIn("beta", text)
            source = SCRIPT.read_text()
            self.assertIn("source of truth", source)


if __name__ == "__main__":
    unittest.main()
