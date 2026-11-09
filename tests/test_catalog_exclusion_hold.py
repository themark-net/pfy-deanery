"""Excluded slugs are not applied and not auto-raised. No model, no network."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAISE = ROOT / "scripts" / "catalog_auto_raise.py"
APPLY = ROOT / "scripts" / "catalog_apply_verdict.py"
ATG = "atomic-task-graph-atg"
CARD = ROOT / "data" / "stages" / f"{ATG}.json"
EXCLUSIONS = ROOT / "eval" / "catalog-queue" / "exclusions.tsv"


def _card(slug: str) -> dict:
    return {
        "name": slug,
        "integration_stage": "I2",
        "intent": "staged_evaluation",
        "next_gate": "eval",
        "uses": "format logs",
        "features": [],
        "tags": [],
        "potential": "ambiguous",
        "non_goals": ["no install"],
        "evidence": ["probe:local"],
        "tier_ceiling": "I2",
        "risk_class": "none",
    }


def _verdict(root: Path, slug: str, stage: str = "I3") -> None:
    path = root / "eval" / "evals" / slug / "VERDICT.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "metric": "probe_score",
        "threshold": 1,
        "value_gate": "pass",
        "modularity_gate": "pass",
        "proposed_stage": stage,
    }) + "\n", encoding="utf-8")


class ExclusionHoldTest(unittest.TestCase):
    def test_real_atg_row_blocks_raise_and_apply(self):
        text = EXCLUSIONS.read_text(encoding="utf-8")
        self.assertIn(f"{ATG}\t", text)
        # The live queue is operator state in the private ops checkout. Rebuild
        # it from the public inputs into a temp file instead.
        with tempfile.TemporaryDirectory() as built:
            out = Path(built) / "needs-mark.tsv"
            made = subprocess.run(
                ["python3", str(ROOT / "scripts" / "catalog_needs_mark.py"), "--root", str(ROOT), "--out", str(out)],
                cwd=ROOT, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(made.returncode, 0, made.stderr)
            needs = out.read_text(encoding="utf-8")
        self.assertIn(f"{ATG}\texcluded\t", needs)
        before = CARD.read_bytes()
        self.assertEqual(json.loads(before)["tier_ceiling"], "I2")
        self.assertEqual(json.loads(before)["integration_stage"], "I2")

        dry = subprocess.run(
            ["python3", str(RAISE), "--root", str(ROOT), "--slug", ATG, "--dry-run"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn(f"refuse\t{ATG}\texcluded", dry.stdout)
        self.assertNotIn(f"raise\t{ATG}\t", dry.stdout)
        check = subprocess.run(
            ["python3", str(RAISE), "--root", str(ROOT), "--launch-check", ATG],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertTrue(check.stdout.startswith(f"skip\t{ATG}\texcluded"), check.stdout)

        with tempfile.TemporaryDirectory() as tmp:
            card = Path(tmp) / f"{ATG}.json"
            card.write_bytes(before)
            verdict = Path(tmp) / "VERDICT.json"
            verdict.write_text(json.dumps({
                "metric": "stay_probe",
                "threshold": 1,
                "value_gate": "pass",
                "modularity_gate": "pass",
                "proposed_stage": "I2",
            }) + "\n", encoding="utf-8")
            proc = subprocess.run(
                ["python3", str(APPLY), "--card", str(card), "--verdict", str(verdict)],
                cwd=ROOT, capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            self.assertIn(f"refused: excluded: {ATG}", proc.stderr)
            self.assertEqual(card.read_bytes(), before)
        self.assertEqual(CARD.read_bytes(), before)

    def test_passing_gates_do_not_raise_an_excluded_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stages = root / "data" / "stages"
            stages.mkdir(parents=True)
            excluded = stages / f"{ATG}.json"
            open_card = stages / "zz-open.json"
            excluded.write_text(json.dumps(_card(ATG), indent=2) + "\n", encoding="utf-8")
            open_card.write_text(json.dumps(_card("zz-open"), indent=2) + "\n", encoding="utf-8")
            _verdict(root, ATG)
            _verdict(root, "zz-open")
            exc = root / "eval" / "catalog-queue" / "exclusions.tsv"
            exc.parent.mkdir(parents=True, exist_ok=True)
            exc.write_text(
                "slug\treason\n"
                f"{ATG}\tMark stopped ATG. Do not auto-raise.\n",
                encoding="utf-8",
            )
            before = excluded.read_bytes()
            proc = subprocess.run(
                ["python3", str(RAISE), "--root", str(root), "--date", "2026-11-08"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn(f"refuse\t{ATG}\texcluded", proc.stdout)
            self.assertIn("raise\tzz-open\t", proc.stdout)
            self.assertEqual(excluded.read_bytes(), before)
            self.assertEqual(json.loads(open_card.read_text(encoding="utf-8"))["tier_ceiling"], "I3")

    def test_lane_selects_its_commits_not_main_only_files(self):
        env = os.environ.copy()
        env.update({
            "GIT_AUTHOR_NAME": "catalog-health",
            "GIT_AUTHOR_EMAIL": "catalog-health@localhost",
            "GIT_COMMITTER_NAME": "catalog-health",
            "GIT_COMMITTER_EMAIL": "catalog-health@localhost",
        })
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.check_call(["git", "init", "-q", "-b", "main"], cwd=root, env=env)
            readme = root / "README.md"
            readme.write_text("base\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "README.md"], cwd=root, env=env)
            subprocess.check_call(["git", "commit", "-qm", "base"], cwd=root, env=env)
            subprocess.check_call(["git", "branch", "lane"], cwd=root, env=env)
            needs = root / "eval" / "catalog-queue" / "needs-mark.tsv"
            needs.parent.mkdir(parents=True)
            needs.write_text("slug\tkind\treason\tevidence\tsince\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "eval/catalog-queue/needs-mark.tsv"], cwd=root, env=env)
            subprocess.check_call(["git", "commit", "-qm", "main only"], cwd=root, env=env)
            subprocess.check_call(["git", "switch", "-q", "lane"], cwd=root, env=env)
            verdict = root / "eval" / "evals" / "zz-tool" / "VERDICT.json"
            verdict.parent.mkdir(parents=True)
            verdict.write_text("{}\n", encoding="utf-8")
            subprocess.check_call(["git", "add", "eval/evals/zz-tool/VERDICT.json"], cwd=root, env=env)
            subprocess.check_call(["git", "commit", "-qm", "lane only"], cwd=root, env=env)

            three = subprocess.check_output(
                ["git", "diff", "--name-only", "--diff-filter=ACMR", "main...HEAD"],
                cwd=root, text=True,
            ).split()
            two = subprocess.check_output(
                ["git", "diff", "--name-only", "main", "HEAD"],
                cwd=root, text=True,
            ).split()
            self.assertEqual(three, ["eval/evals/zz-tool/VERDICT.json"])
            self.assertIn("eval/catalog-queue/needs-mark.tsv", two)

            selected = subprocess.run(
                ["python3", str(ROOT / "scripts" / "test_select.py"), "--root", str(root), "--paths", *three],
                cwd=root, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(selected.returncode, 0, selected.stderr)
            body = json.loads(selected.stdout)
            self.assertNotIn("eval/catalog-queue/needs-mark.tsv", body["changed"])
            self.assertNotIn("unknown file: eval/catalog-queue/needs-mark.tsv", body["reason"])

        for name in ("eval_lane.sh", "integrate_lane.sh"):
            text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertNotIn("test_select.py --base origin/main", text)
            self.assertIn("origin/main...HEAD", text)
            self.assertIn("test_select.py --paths", text)


if __name__ == "__main__":
    unittest.main()
