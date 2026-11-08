import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_eval_queue.py"

def _card(slug):
    return {
        "slug": slug,
        "integration_stage": "s1",
        "intent": "probe",
        "next_gate": "install-probe",
        "entry": "tools/" + slug,
        "uses": [],
        "features": [],
        "tags": [],
    }

class TestQueueExclusions(unittest.TestCase):
    def test_exclusion_omits_slug_and_blank_reason_fails(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            stages = d / "stages"
            stages.mkdir()
            for slug in ("keep-me", "drop-me"):
                (stages / (slug + ".json")).write_text(json.dumps(_card(slug)))
            exc = d / "exclusions.tsv"
            exc.write_text("slug\treason\ndrop-me\tleft for Mark\n")
            out = d / "queue.tsv"
            cmd = ["python3", str(SCRIPT), "--stages", str(stages), "--exclusions", str(exc), "--out", str(out)]
            ok = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            body = out.read_text()
            self.assertIn("keep-me", body)
            self.assertNotIn("drop-me", body)
            exc.write_text("slug\treason\ndrop-me\t\n")
            out.unlink()
            bad = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("reason", (bad.stderr + bad.stdout).lower())
            self.assertFalse(out.exists())

if __name__ == "__main__":
    unittest.main()
