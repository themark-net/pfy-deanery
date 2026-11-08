import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_eval_queue.py"

def _good(slug):
    return {
        "slug": slug,
        "integration_stage": "s2",
        "intent": "probe",
        "next_gate": "install-probe",
        "entry": "tools/" + slug,
        "uses": [],
        "features": [],
        "tags": [],
    }

class TestQueueFailRecover(unittest.TestCase):
    def _run(self, stages, exc, out):
        return subprocess.run(
            ["python3", str(SCRIPT), "--stages", str(stages), "--exclusions", str(exc), "--out", str(out)],
            capture_output=True, text=True,
        )

    def test_missing_field_preserves_previous_queue(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            stages = d / "stages"
            stages.mkdir()
            (stages / "ok.json").write_text(json.dumps(_good("ok-tool")))
            exc = d / "exclusions.tsv"
            exc.write_text("slug\treason\n")
            out = d / "queue.tsv"
            good = self._run(stages, exc, out)
            self.assertEqual(good.returncode, 0, good.stderr)
            previous = out.read_bytes()
            (stages / "bad.json").write_text(json.dumps({"slug": "bad-tool", "intent": "probe"}))
            bad = self._run(stages, exc, out)
            self.assertNotEqual(bad.returncode, 0)
            text = (bad.stderr + bad.stdout).lower()
            self.assertIn("bad.json", text)
            self.assertIn("integration_stage", text)
            self.assertEqual(out.read_bytes(), previous)

    def test_malformed_card_does_not_create_queue(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            stages = d / "stages"
            stages.mkdir()
            (stages / "broken.json").write_text("{")
            exc = d / "exclusions.tsv"
            exc.write_text("slug\treason\n")
            out = d / "queue.tsv"
            proc = self._run(stages, exc, out)
            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("broken.json", (proc.stderr + proc.stdout).lower())
            self.assertFalse(out.exists())

if __name__ == "__main__":
    unittest.main()
