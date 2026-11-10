"""catalog_evq_verdicts.py: one-line batch VERDICT to VERDICT.json, no stage moves."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "catalog_evq_verdicts.py"
APPLY = ROOT / "scripts" / "catalog_apply_verdict.py"
SHA = "b" * 40


def make(root: Path, slug: str, stage: str, line: str | None, **extra) -> Path:
    card = {"name": slug, "integration_stage": stage, "tier_ceiling": "I1", "evidence": [f"eval/evq9/{slug}/VERDICT"], "risk_class": "none"}
    card.update(extra)
    stages = root / "data" / "stages"
    stages.mkdir(parents=True, exist_ok=True)
    path = stages / f"{slug}.json"
    path.write_text(json.dumps(card, indent=2) + "\n", encoding="utf-8")
    if line is not None:
        d = root / "eval" / "evq9" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "VERDICT").write_text(line, encoding="utf-8")
    return path


def run(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", str(SCRIPT), "--root", str(root), "--batch", "evq9", *args], capture_output=True, text=True, timeout=30)


class EvqVerdictsTest(unittest.TestCase):
    def test_stay_lines_become_verdicts_and_apply_leaves_the_card(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stay = make(root, "stay", "I0", "STAY I0 reference: no gain here\n", pin=SHA)
            make(root, "promo", "I1", "PROMOTE I2 gain 3\n")
            make(root, "moved", "I1", "STAY I0 old line\n")
            make(root, "one", "I1", "STAY I1: fine\n")
            (root / "eval" / "evq9" / "ghost").mkdir(parents=True)
            (root / "eval" / "evq9" / "ghost" / "VERDICT").write_text("STAY I0 x\n", encoding="utf-8")
            out = run(root, "--stage", "I0")
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertEqual(
                out.stdout.splitlines(),
                ["skip ghost no-card", "skip moved stage-differs", "skip one other-stage", "skip promo not-stay", "wrote stay"],
            )
            dest = root / "eval" / "evq9" / "stay" / "VERDICT.json"
            data = json.loads(dest.read_text(encoding="utf-8"))
            self.assertEqual(data["proposed_stage"], "I0")
            self.assertEqual(data["value_gate"], "fail")
            self.assertEqual(data["pin"], SHA)
            self.assertEqual(data["why"], "reference: no gain here")
            self.assertEqual(data["source"], "eval/evq9/stay/VERDICT")
            before = stay.read_bytes()
            applied = subprocess.run(["python3", str(APPLY), "--card", str(stay), "--verdict", str(dest)], capture_output=True, text=True, timeout=30, cwd=root)
            self.assertEqual(applied.returncode, 0, applied.stderr)
            self.assertIn("STAY I0", applied.stdout)
            self.assertEqual(stay.read_bytes(), before)
            json_bytes = dest.read_bytes()
            again = run(root, "--stage", "I0")
            self.assertIn("skip stay has-json", again.stdout.splitlines())
            self.assertEqual(dest.read_bytes(), json_bytes)

    def test_dry_run_writes_nothing_and_bad_batch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make(root, "stay", "I0", "STAY I0 x\n")
            out = run(root, "--dry-run")
            self.assertEqual(out.stdout.strip(), "wrote stay")
            self.assertFalse((root / "eval" / "evq9" / "stay" / "VERDICT.json").exists())
            bad = subprocess.run(["python3", str(SCRIPT), "--root", str(root), "--batch", "../x"], capture_output=True, text=True, timeout=30)
            self.assertEqual(bad.returncode, 2)

    def test_real_batch_stay_i0_verdicts_match_their_cards(self):
        base = ROOT / "eval" / "evq1107"
        if not base.is_dir():
            self.skipTest("no evq1107 batch")
        checked = 0
        for path in sorted(base.glob("*/VERDICT.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("metric") != "batch_report_verdict":
                continue
            card = json.loads((ROOT / "data" / "stages" / f"{path.parent.name}.json").read_text(encoding="utf-8"))
            self.assertEqual(card["integration_stage"], data["proposed_stage"], path)
            self.assertTrue((path.parent / "VERDICT").is_file(), path)
            checked += 1
        self.assertGreaterEqual(checked, 38)


if __name__ == "__main__":
    unittest.main()
