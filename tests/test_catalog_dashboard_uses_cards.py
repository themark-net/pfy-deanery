import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTS = ROOT / "scripts" / "catalog_counts.py"
DASH = ROOT / "scripts" / "catalog_dashboard.py"


class DashboardUsesCardsTest(unittest.TestCase):
    def test_dashboard_shim_matches_counts_without_tools_json(self):
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
            registry = cards / "_registry.json"
            registry.write_text(json.dumps({
                "version": 1,
                "policy": "keep",
                "default_stage": "I0",
                "probe_path": "x",
                "handoff": "y",
                "coverage": "stale",
            }))
            dash_a = tmp / "a.md"
            prog_a = tmp / "a.json"
            dash_b = tmp / "b.md"
            prog_b = tmp / "b.json"
            common = ["--cards", str(cards), "--registry", str(registry)]
            first = subprocess.run(
                ["python3", str(COUNTS), *common, "--dashboard", str(dash_a), "--progress", str(prog_a)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            registry.write_text(json.dumps({
                "version": 1,
                "policy": "keep",
                "default_stage": "I0",
                "probe_path": "x",
                "handoff": "y",
                "coverage": "stale",
            }))
            second = subprocess.run(
                ["python3", str(DASH), *common, "--dashboard", str(dash_b), "--progress", str(prog_b)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(dash_a.read_bytes(), dash_b.read_bytes())
            self.assertIn("2 tools registered", dash_b.read_text())
            self.assertNotIn("tools.json", dash_b.read_text())


if __name__ == "__main__":
    unittest.main()
