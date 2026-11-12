"""Langfuse stage-0 stay must not be stored as I1.

How this fails: the I1 rules pass on the existing card, so a verdict that
proposes I1 promotes a copy. Recovery: the committed verdict proposes I0,
apply stays, and the public files do not carry compose env defaults.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERDICT = ROOT / "eval" / "evals" / "langfuse" / "VERDICT.json"
FIXTURE = ROOT / "eval" / "evals" / "langfuse" / "fixtures" / "compose-surface.json"
RECEIPT = ROOT / "eval" / "evals" / "langfuse" / "receipt.json"
CARD = ROOT / "data" / "stages" / "langfuse.json"
APPLY = ROOT / "scripts" / "catalog_apply_verdict.py"
PUBLIC = (
    "eval/evals/langfuse/VERDICT.json",
    "eval/evals/langfuse/receipt.json",
    "eval/evals/langfuse/fixtures/compose-surface.json",
)
# Names of compose env keys, not their default values.
MARKERS = (
    "CHANGEME",
    "NEXTAUTH",
    "_PASSWORD",
    "_SECRET",
    "postgresql://",
    "sk-lf-",
    "MINIO_ROOT",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class LangfuseVerdictTest(unittest.TestCase):
    def test_surface_matches_fixture_and_stays_i0(self) -> None:
        verdict = _load(VERDICT)
        surface = _load(FIXTURE)
        stack = verdict["stack"]
        self.assertEqual(stack["services"], 7)
        self.assertEqual(stack["depends_on"], surface["depends_on"])
        self.assertEqual(stack["images"], surface["images"])
        self.assertEqual(stack["ports"], surface["ports"])
        self.assertEqual(
            stack["published_on_all_interfaces"],
            surface["published_on_all_interfaces"],
        )
        self.assertTrue(stack["telemetry_enabled_default"])
        self.assertFalse(surface["env_copied"])
        self.assertEqual(verdict["pin"], surface["pin"])
        passed = [name for name, leg in verdict["stage0_legs"].items() if leg == "pass"]
        self.assertEqual(passed, ["license_open"])
        self.assertEqual(verdict["stage0_legs_present"], 1)
        self.assertEqual(verdict["value"], 1)
        self.assertEqual(verdict["threshold"], 3)
        self.assertEqual(verdict["value_gate"], "fail")
        self.assertEqual(verdict["modularity_gate"], "fail")
        self.assertEqual(verdict["proposed_stage"], "I0")
        self.assertFalse(verdict["compose_invoked"])
        self.assertFalse(verdict["installed"])
        for rel in PUBLIC:
            text = (ROOT / rel).read_text(encoding="utf-8")
            for marker in MARKERS:
                self.assertNotIn(marker, text, rel)

    def test_i1_proposal_promotes_a_copy_and_i0_stays(self) -> None:
        before = CARD.read_bytes()
        verdict = _load(VERDICT)
        with tempfile.TemporaryDirectory() as tmp:
            stay_card = Path(tmp) / "stay.json"
            promote_card = Path(tmp) / "promote.json"
            stay_verdict = Path(tmp) / "stay-verdict.json"
            promote_verdict = Path(tmp) / "promote-verdict.json"
            stay_card.write_bytes(before)
            promote_card.write_bytes(before)
            stay_verdict.write_text(json.dumps(verdict), encoding="utf-8")
            promoted = dict(verdict)
            promoted["proposed_stage"] = "I1"
            promote_verdict.write_text(json.dumps(promoted), encoding="utf-8")
            stay = subprocess.run(
                ["python3", str(APPLY), "--card", str(stay_card), "--verdict", str(stay_verdict)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(stay.returncode, 0, stay.stderr + stay.stdout)
            self.assertTrue(stay.stdout.startswith("STAY I0 "), stay.stdout)
            self.assertEqual(stay_card.read_bytes(), before)
            promote = subprocess.run(
                ["python3", str(APPLY), "--card", str(promote_card), "--verdict", str(promote_verdict)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(promote.returncode, 0, promote.stderr + promote.stdout)
            self.assertTrue(promote.stdout.startswith("PROMOTE I1 "), promote.stdout)
            self.assertEqual(_load(promote_card)["integration_stage"], "I1")
        self.assertEqual(CARD.read_bytes(), before)
        self.assertTrue(RECEIPT.is_file())


if __name__ == "__main__":
    unittest.main()
