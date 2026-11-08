import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_eval_queue.py"

def _card(slug, **extra):
    base = {
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
    base.update(extra)
    return base

class TestQueueOrder(unittest.TestCase):
    def test_mode_rank_then_slug(self):
        with tempfile.TemporaryDirectory() as raw:
            d = Path(raw)
            stages = d / "stages"
            stages.mkdir()
            cards = [
                _card("z-ref", intent="reference", tags=["design-reference"], next_gate="read"),
                _card("b-trial"),
                _card("a-model", next_gate="model-probe", tags=["local-model"]),
                _card("a-trial"),
            ]
            for c in cards:
                (stages / (c["slug"] + ".json")).write_text(json.dumps(c))
            exc = d / "exclusions.tsv"
            exc.write_text("slug\treason\n")
            out = d / "queue.tsv"
            proc = subprocess.run(
                ["python3", str(SCRIPT), "--stages", str(stages), "--exclusions", str(exc), "--out", str(out)],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            lines = out.read_text().strip().splitlines()
            self.assertEqual(lines[0].split("\t"), ["n", "slug", "mode", "gap", "entry", "card", "why"])
            rows = [line.split("\t") for line in lines[1:]]
            self.assertEqual([r[1] for r in rows], ["a-trial", "b-trial", "a-model", "z-ref"])
            self.assertEqual([r[2] for r in rows], ["trial", "trial", "model", "ref"])
            self.assertEqual([r[0] for r in rows], ["1", "2", "3", "4"])
            self.assertEqual(rows[0][3], "install-probe")
            self.assertEqual(rows[0][5], "a-trial.json")

if __name__ == "__main__":
    unittest.main()
