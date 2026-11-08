import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_apply_verdict.py"


class CeilingRefuseTest(unittest.TestCase):
    def test_illegal_promote_does_not_write(self):
        self.assertTrue(SCRIPT.is_file(), "catalog_apply_verdict.py missing")
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "skillspector-like.json"
            verdict = Path(tmp) / "VERDICT.json"
            original = json.dumps({
                "slug": "skillspector-like",
                "integration_stage": "I1",
                "intent": "staged_evaluation",
                "evidence": ["notes.md", "scan-summary.md", "report.md"],
                "self_pipeline": None,
                "tier_ceiling": "I3",
            }, indent=2)
            card.write_text(original)
            before = card.read_bytes()
            verdict.write_text(json.dumps({
                "metric": "onboard_ready",
                "threshold": 1,
                "value_gate": "pass",
                "modularity_gate": "pass",
                "proposed_stage": "I3",
            }))
            proc = subprocess.run(
                ["python3", str(SCRIPT), "--card", str(card), "--verdict", str(verdict)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            blob = proc.stderr + proc.stdout
            self.assertIn("ceiling", blob.lower())
            self.assertEqual(card.read_bytes(), before)
            self.assertEqual(json.loads(card.read_text())["integration_stage"], "I1")


if __name__ == "__main__":
    unittest.main()
