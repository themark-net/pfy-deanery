import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_apply_verdict.py"

CARD = {
    "slug": "widget",
    "integration_stage": "I1",
    "intent": "staged_eval",
    "evidence": ["eval/widget/VERDICT"],
    "self_pipeline": None,
}


class IntentEnumTest(unittest.TestCase):
    def _run(self, tmp, intent):
        card = Path(tmp) / "widget.json"
        verdict = Path(tmp) / "VERDICT.json"
        card.write_text(json.dumps(dict(CARD)))
        before = card.read_bytes()
        verdict.write_text(json.dumps({
            "metric": "probe_score",
            "threshold": 1,
            "value_gate": "pass",
            "modularity_gate": "pass",
            "proposed_stage": "I1",
            "intent": intent,
        }))
        proc = subprocess.run(
            ["python3", str(SCRIPT), "--card", str(card), "--verdict", str(verdict)],
            cwd=ROOT, capture_output=True, text=True,
        )
        return proc, card, before

    def test_alias_accepted_and_unknown_rejected(self):
        self.assertTrue(SCRIPT.is_file(), "catalog_apply_verdict.py missing")
        with tempfile.TemporaryDirectory() as tmp:
            ok, card, _before = self._run(tmp, "staged_eval")
            self.assertEqual(ok.returncode, 0, ok.stderr + ok.stdout)
            body = json.loads(card.read_text())
            self.assertIn(body.get("intent"), ("staged_eval", "staged_evaluation"))
        with tempfile.TemporaryDirectory() as tmp:
            bad, card, before = self._run(tmp, "whatever_one_off")
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("intent", (bad.stderr + bad.stdout).lower())
            self.assertEqual(card.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
