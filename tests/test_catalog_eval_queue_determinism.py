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
        "integration_stage": "s2",
        "intent": "probe",
        "next_gate": "install-probe",
        "entry": "tools/" + slug,
        "uses": [],
        "features": [],
        "tags": [],
        "tier_ceiling": "t2",
        "handoff_by": "",
        "potential": "med",
    }

class TestQueueDeterminism(unittest.TestCase):
    def test_two_runs_match_bytes(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            stages = d / "stages"
            stages.mkdir()
            for slug in ("b-tool", "a-tool"):
                (stages / (slug + ".json")).write_text(json.dumps(_card(slug)))
            exc = d / "exclusions.tsv"
            exc.write_text("slug\treason\n")
            out = d / "queue.tsv"
            cmd = [
                "python3", str(SCRIPT),
                "--stages", str(stages),
                "--exclusions", str(exc),
                "--out", str(out),
            ]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            body = out.read_bytes()
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(out.read_bytes(), body)

if __name__ == "__main__":
    unittest.main()
