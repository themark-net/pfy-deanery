import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_apply_verdict.py"


class VerdictOneLineTest(unittest.TestCase):
    def test_json_renders_one_line_verdict(self):
        self.assertTrue(SCRIPT.is_file(), "catalog_apply_verdict.py missing")
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "widget.json"
            verdict = Path(tmp) / "VERDICT.json"
            one_line = Path(tmp) / "VERDICT"
            card.write_text(json.dumps({
                "slug": "widget",
                "integration_stage": "I1",
                "intent": "staged_evaluation",
                "evidence": ["eval/widget/VERDICT"],
                "self_pipeline": None,
            }))
            verdict.write_text(json.dumps({
                "metric": "probe_score",
                "threshold": 1,
                "value_gate": "pass",
                "modularity_gate": "pass",
                "proposed_stage": "I1",
            }))
            proc = subprocess.run(
                ["python3", str(SCRIPT), "--card", str(card), "--verdict", str(verdict),
                 "--write-one-line", str(one_line)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            text = one_line.read_text().strip()
            self.assertRegex(text, r"^(PROMOTE|STAY|DEMOTE) I[0-3] ")
            stored = json.loads(verdict.read_text())
            self.assertIn("metric", stored)
            self.assertIn("threshold", stored)
            self.assertIn(stored.get("value_gate"), ("pass", "fail"))
            self.assertIn(stored.get("modularity_gate"), ("pass", "fail"))


if __name__ == "__main__":
    unittest.main()
