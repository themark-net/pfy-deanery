import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_counts.py"


def card(tool_id, stage, intent):
    return {"id": tool_id, "stage": stage, "intent": intent, "uses": [], "features": [], "tags": []}


class FailRecoverCountsTest(unittest.TestCase):
    def test_malformed_card_does_not_replace_good_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            cards = tmp / "stages"
            cards.mkdir()
            (cards / "alpha.json").write_text(json.dumps(card("alpha", "I2", "inspect")))
            registry = cards / "_registry.json"
            registry.write_text(json.dumps({
                "version": 1,
                "policy": "keep",
                "default_stage": "I0",
                "probe_path": "x",
                "handoff": "y",
                "coverage": "stale",
            }))
            dashboard = tmp / "dashboard.latest.md"
            progress = tmp / "counts.latest.json"
            cmd = [
                "python3", str(SCRIPT),
                "--cards", str(cards),
                "--registry", str(registry),
                "--dashboard", str(dashboard),
                "--progress", str(progress),
            ]
            good = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(good.returncode, 0, good.stderr)
            before = {
                registry: registry.read_bytes(),
                dashboard: dashboard.read_bytes(),
                progress: progress.read_bytes(),
            }
            (cards / "beta.json").write_text("{not json")
            bad = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("beta.json", bad.stderr)
            for path, payload in before.items():
                self.assertEqual(path.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
