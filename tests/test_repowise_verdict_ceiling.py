import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestRepowiseVerdictCeiling(unittest.TestCase):
    def test_verdict_proposes_i3_off_card(self):
        verdict = json.loads(Path("eval/integrate/repowise/VERDICT.json").read_text())
        self.assertEqual(verdict.get("proposed_stage"), "I3")
        self.assertEqual(verdict.get("value_gate"), "pass")
        self.assertEqual(verdict.get("modularity_gate"), "pass")
        self.assertIn("metric", verdict)
        self.assertIn("threshold", verdict)
        card = Path("data/stages/repowise.json")
        if card.exists():
            data = json.loads(card.read_text())
            ceiling = str(data.get("tier_ceiling", "I1"))
            self.assertNotEqual(ceiling, "I3")

    def test_card_bytes_match_origin_main(self):
        card = ROOT / "data/stages/repowise.json"
        proc = subprocess.run(
            ["git", "show", "origin/main:data/stages/repowise.json"],
            cwd=ROOT,
            capture_output=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(card.read_bytes(), proc.stdout)
