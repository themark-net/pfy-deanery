"""Mismatch scan flags a stage above the evidence ceiling and does not demote.

A SkillSpector-shaped card (notes, scan summary, report, no self_pipeline)
stays at I3 while the report names it. A Bumblebee-shaped card stays at I2
while tier_ceiling I1 is named. An operator path at I3 without a main-run
receipt is flagged with missing-main-receipt and is not demoted.
The same cards produce the same report on a second run.
The worktree scan names SkillSpector, not Bumblebee (in a shallow CI
checkout only as R-main-receipt git-unavailable), and leaves both cards.
The real cards' stages are read from the card and its promotion_history
(the last stage promote or demote), not hard-coded, so a promotion by the
rules (data/promotion-rules.json) does not break this test.
"""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_apply_verdict.py"


def _card(name: str, stage: str, evidence: list[str], tier: str, self_pipeline=None) -> dict:
    return {
        "name": name,
        "integration_stage": stage,
        "intent": "staged_evaluation",
        "evidence": evidence,
        "self_pipeline": self_pipeline,
        "tier_ceiling": tier,
        "uses": "Notes only.",
        "features": ["receipt"],
    }


def _shallow() -> bool:
    proc = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--is-shallow-repository"],
                          capture_output=True, text=True)
    return proc.stdout.strip() == "true"


def _rules_stage(card: dict) -> str:
    """Stage the rules last wrote: the last stage promote/demote "to", else integration_stage."""
    for entry in reversed(card.get("promotion_history") or []):
        if entry.get("kind") == "stage" and entry.get("result") in ("promote", "demote") and entry.get("to"):
            return entry["to"]
    return card["integration_stage"]


class VerdictMismatchScanTest(unittest.TestCase):
    def test_fixture_flags_without_demoting_and_is_stable(self):
        self.assertTrue(SCRIPT.is_file(), "catalog_apply_verdict.py missing")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stage_dir = root / "data" / "stages"
            stage_dir.mkdir(parents=True)
            scan_only = stage_dir / "scan-only.json"
            probe_cap = stage_dir / "probe-cap.json"
            onboard = stage_dir / "onboard-ok.json"
            scan_only.write_text(json.dumps(_card(
                "Scan Only",
                "I3",
                ["notes.md", "scan-summary.md", "report.md"],
                "I3",
            ), indent=2))
            probe_cap.write_text(json.dumps(_card(
                "Probe Cap",
                "I2",
                [
                    "notes_doc:docs/ops/example.md",
                    "pin:abc1234",
                    "eval/example/REPORT.md",
                    "eval/example/VERDICT",
                    "scripts/pfy_mcp_scan.py",
                ],
                "I1",
            ), indent=2))
            onboard.write_text(json.dumps(_card(
                "Onboard Ok",
                "I3",
                ["make:smoke-widget", "path:bootstrap/widget"],
                "I3",
            ), indent=2))
            before = {
                path: path.read_bytes()
                for path in (scan_only, probe_cap, onboard)
            }
            report = root / "CEILING-MISMATCHES.md"

            def _scan() -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    ["python3", str(SCRIPT), "--scan", "--root", str(root), "--report", str(report)],
                    cwd=ROOT, capture_output=True, text=True,
                )

            first = _scan()
            self.assertEqual(first.returncode, 0, first.stderr + first.stdout)
            text = report.read_text(encoding="utf-8")
            head, _, _tail = text.partition("## Intent")
            scan_line = next(line for line in head.splitlines() if line.startswith("| Scan Only |"))
            probe_line = next(line for line in head.splitlines() if line.startswith("| Probe Cap |"))
            self.assertIn("| I3 |", scan_line)
            self.assertIn("| I1 |", scan_line)
            self.assertIn("missing-main-receipt", scan_line)
            self.assertIn("| I2 |", probe_line)
            self.assertIn("| I1 |", probe_line)
            self.assertNotIn("missing-main-receipt", probe_line)
            onboard_line = next(line for line in head.splitlines() if line.startswith("| Onboard Ok |"))
            self.assertIn("| I3 |", onboard_line)
            self.assertIn("missing-main-receipt", onboard_line)
            for path, blob in before.items():
                self.assertEqual(path.read_bytes(), blob)
            self.assertEqual(json.loads(scan_only.read_text())["integration_stage"], "I3")
            self.assertEqual(json.loads(probe_cap.read_text())["integration_stage"], "I2")
            second = _scan()
            self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
            self.assertEqual(report.read_bytes(), text.encode("utf-8"))
            for path, blob in before.items():
                self.assertEqual(path.read_bytes(), blob)

    def test_worktree_scan_names_skillspector_and_not_bumblebee(self):
        self.assertTrue(SCRIPT.is_file(), "catalog_apply_verdict.py missing")
        skill = ROOT / "data" / "stages" / "skillspector.json"
        bumble = ROOT / "data" / "stages" / "bumblebee.json"
        before_skill = skill.read_bytes()
        before_bumble = bumble.read_bytes()
        skill_card = json.loads(before_skill)
        bumble_card = json.loads(before_bumble)
        skill_stage = skill_card["integration_stage"]
        # The card holds the stage its rule ledger last wrote.
        self.assertEqual(skill_stage, _rules_stage(skill_card))
        self.assertEqual(bumble_card["integration_stage"], _rules_stage(bumble_card))
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "CEILING-MISMATCHES.md"
            proc = subprocess.run(
                ["python3", str(SCRIPT), "--scan", "--root", str(ROOT), "--report", str(report)],
                cwd=ROOT, capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            text = report.read_text(encoding="utf-8")
            head, _, _tail = text.partition("## Intent")
            skill_line = next(line for line in head.splitlines() if line.startswith("| SkillSpector |"))
            self.assertIn("| %s |" % skill_stage, skill_line)
            self.assertIn("| I1 |", skill_line)
            self.assertIn("missing-main-receipt", skill_line)
            # Operator decision 2026-11-10: Bumblebee's ceiling is I3, and the
            # rules moved it there with a main-run receipt, so whatever stage
            # its ledger holds is backed and it is not a mismatch.
            self.assertEqual(bumble_card["tier_ceiling"], "I3")
            bumble_lines = [line for line in head.splitlines() if line.startswith("| Bumblebee |")]
            if _shallow():
                # A depth-1 CI checkout cannot prove the receipt's main_sha is
                # on origin/main, so the scan names it git-unavailable. That
                # is the only reason allowed there.
                for line in bumble_lines:
                    self.assertIn("R-main-receipt: git-unavailable", line)
            else:
                self.assertEqual(bumble_lines, [])
        self.assertEqual(skill.read_bytes(), before_skill)
        self.assertEqual(bumble.read_bytes(), before_bumble)


if __name__ == "__main__":
    unittest.main()
