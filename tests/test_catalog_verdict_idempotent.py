import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_apply_verdict.py"


class VerdictIdempotentApplyTest(unittest.TestCase):
    def test_second_apply_is_byte_identical(self):
        self.assertTrue(SCRIPT.is_file(), "catalog_apply_verdict.py missing")
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "widget.json"
            verdict = Path(tmp) / "VERDICT.json"
            card.write_text(json.dumps({
                "slug": "widget",
                "integration_stage": "I0",
                "intent": "awareness",
                "evidence": ["eval/widget/notes.md", "eval/widget/VERDICT"],
                "self_pipeline": None,
                "tier_ceiling": "I1",
            }))
            verdict.write_text(json.dumps({
                "metric": "probe_score",
                "threshold": 1,
                "value_gate": "pass",
                "modularity_gate": "pass",
                "proposed_stage": "I1",
                "one_line": "PROMOTE I1 staged eval evidence",
            }))
            cmd = ["python3", str(SCRIPT), "--card", str(card), "--verdict", str(verdict)]
            first = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            after_first = card.read_bytes()
            body = json.loads(after_first.decode())
            self.assertEqual(body.get("integration_stage"), "I1")
            second = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
            self.assertEqual(card.read_bytes(), after_first)


if __name__ == "__main__":
    unittest.main()
