"""Fail, then recover, for the three apply risks.

Malformed verdict: the card stays put until the JSON has metric, threshold,
and both gates. Missing card: the script names the missing path and writes
nothing until the card exists. Stage above the evidence ceiling: the illegal
promote is refused, then a proposed stage inside the ceiling is written.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_apply_verdict.py"

LEGAL_CARD = {
    "slug": "widget",
    "integration_stage": "I0",
    "intent": "awareness",
    "evidence": ["eval/widget/notes.md", "eval/widget/VERDICT"],
    "self_pipeline": None,
    "tier_ceiling": "I1",
}


def _verdict(stage: str) -> dict:
    return {
        "metric": "probe_score",
        "threshold": 1,
        "value_gate": "pass",
        "modularity_gate": "pass",
        "proposed_stage": stage,
    }


class VerdictFailRecoverTest(unittest.TestCase):
    def test_malformed_verdict_refuses_then_a_legal_one_applies(self):
        self.assertTrue(SCRIPT.is_file(), "catalog_apply_verdict.py missing")
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "widget.json"
            verdict = Path(tmp) / "VERDICT.json"
            card.write_text(json.dumps(LEGAL_CARD))
            before = card.read_bytes()
            verdict.write_text("{not json")
            bad = subprocess.run(
                ["python3", str(SCRIPT), "--card", str(card), "--verdict", str(verdict)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertNotEqual(bad.returncode, 0)
            self.assertIn("malformed", (bad.stderr + bad.stdout).lower())
            self.assertEqual(card.read_bytes(), before)
            verdict.write_text(json.dumps(_verdict("I1")))
            good = subprocess.run(
                ["python3", str(SCRIPT), "--card", str(card), "--verdict", str(verdict)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(good.returncode, 0, good.stderr + good.stdout)
            self.assertEqual(json.loads(card.read_text())["integration_stage"], "I1")

    def test_missing_card_refuses_then_a_written_card_applies(self):
        self.assertTrue(SCRIPT.is_file(), "catalog_apply_verdict.py missing")
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "widget.json"
            verdict = Path(tmp) / "VERDICT.json"
            verdict.write_text(json.dumps(_verdict("I1")))
            missing = subprocess.run(
                ["python3", str(SCRIPT), "--card", str(card), "--verdict", str(verdict)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("card", (missing.stderr + missing.stdout).lower())
            self.assertFalse(card.exists())
            card.write_text(json.dumps(LEGAL_CARD))
            recovered = subprocess.run(
                ["python3", str(SCRIPT), "--card", str(card), "--verdict", str(verdict)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr + recovered.stdout)
            self.assertEqual(json.loads(card.read_text())["integration_stage"], "I1")

    def test_stage_above_ceiling_refuses_then_a_legal_stage_applies(self):
        self.assertTrue(SCRIPT.is_file(), "catalog_apply_verdict.py missing")
        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / "scan-only.json"
            verdict = Path(tmp) / "VERDICT.json"
            original = json.dumps({
                "slug": "scan-only",
                "integration_stage": "I1",
                "intent": "staged_evaluation",
                "evidence": ["notes.md", "scan-summary.md", "report.md"],
                "self_pipeline": None,
                "tier_ceiling": "I3",
            }, indent=2)
            card.write_text(original)
            before = card.read_bytes()
            verdict.write_text(json.dumps(_verdict("I3")))
            blocked = subprocess.run(
                ["python3", str(SCRIPT), "--card", str(card), "--verdict", str(verdict)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertNotEqual(blocked.returncode, 0)
            self.assertIn("ceiling", (blocked.stderr + blocked.stdout).lower())
            self.assertEqual(card.read_bytes(), before)
            verdict.write_text(json.dumps(_verdict("I1")))
            recovered = subprocess.run(
                ["python3", str(SCRIPT), "--card", str(card), "--verdict", str(verdict)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(recovered.returncode, 0, recovered.stderr + recovered.stdout)
            self.assertEqual(json.loads(card.read_text())["integration_stage"], "I1")


if __name__ == "__main__":
    unittest.main()
