"""Auto-raise and needs-mark against temp cards. No git, no model."""
from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAISE = ROOT / "scripts" / "catalog_auto_raise.py"
NEEDS = ROOT / "scripts" / "catalog_needs_mark.py"


def card(slug, **extra):
    body = {
        "name": slug,
        "integration_stage": "I1",
        "intent": "staged_evaluation",
        "next_gate": "eval",
        "entry": "",
        "uses": "format logs",
        "features": [],
        "tags": [],
        "potential": "ambiguous",
        "non_goals": ["no install"],
        "evidence": [],
        "tier_ceiling": "I1",
        "risk_class": "none",
    }
    body.update(extra)
    return body


def write_card(stages, slug, body):
    path = stages / f"{slug}.json"
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def verdict(root, slug, value="pass", modularity="pass"):
    path = root / "eval" / "evals" / slug / "VERDICT.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "metric": "probe_score",
        "threshold": 1,
        "value_gate": value,
        "modularity_gate": modularity,
        "proposed_stage": "I2",
    }, indent=2) + "\n", encoding="utf-8")


class RaisePolicyTest(unittest.TestCase):
    def test_clean_tool_is_raised_and_risky_classes_are_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stages = root / "data" / "stages"
            stages.mkdir(parents=True)
            (stages / "_registry.json").write_text("{}\n", encoding="utf-8")
            write_card(stages, "aa-raise", card("aa-raise"))
            verdict(root, "aa-raise")
            for slug, risk in (
                ("aa-sec", "security"),
                ("aa-money", "live-money"),
                ("aa-take", "runtime-takeover"),
            ):
                write_card(stages, slug, card(slug, risk_class=risk))
                verdict(root, slug)
            write_card(stages, "aa-unknown", card("aa-unknown", risk_class="mystery", uses=""))
            verdict(root, "aa-unknown")
            write_card(stages, "aa-i3", card("aa-i3", integration_stage="I3", tier_ceiling="I3", evidence=["probe:local"]))
            write_card(stages, "aa-stay", card("aa-stay", integration_stage="I4", tier_ceiling="I4"))
            before_i3 = (stages / "aa-i3.json").read_bytes()
            before_stay = (stages / "aa-stay.json").read_bytes()

            dry = subprocess.run(
                ["python3", str(RAISE), "--root", str(root), "--date", "2026-11-08", "--dry-run"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertIn("raise\taa-raise\t", dry.stdout)
            self.assertEqual((stages / "aa-raise.json").read_text(encoding="utf-8").count('"tier_ceiling": "I1"'), 1)

            real = subprocess.run(
                ["python3", str(RAISE), "--root", str(root), "--date", "2026-11-08"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(real.returncode, 0, real.stderr)
            raised = json.loads((stages / "aa-raise.json").read_text(encoding="utf-8"))
            self.assertEqual(raised["tier_ceiling"], "I3")
            last = raised["ceiling_history"][-1]
            self.assertEqual(last["from"], "I1")
            self.assertEqual(last["to"], "I3")
            self.assertEqual(last["by"], "catalog_loop")
            self.assertEqual(last["date"], "2026-11-08")
            self.assertTrue(last["evidence"])
            for slug in ("aa-sec", "aa-money", "aa-take", "aa-unknown"):
                body = json.loads((stages / f"{slug}.json").read_text(encoding="utf-8"))
                self.assertEqual(body["tier_ceiling"], "I1", slug)
                self.assertNotIn("ceiling_history", body)
            self.assertEqual((stages / "aa-i3.json").read_bytes(), before_i3)
            self.assertEqual((stages / "aa-stay.json").read_bytes(), before_stay)
            self.assertIn("refuse\taa-sec\tsecurity", real.stdout)
            self.assertIn("refuse\taa-money\tlive-money", real.stdout)
            self.assertIn("refuse\taa-take\truntime-takeover", real.stdout)
            self.assertIn("refuse\taa-unknown\tunknown", real.stdout)
            self.assertIn("skip\taa-i3\t", real.stdout)
            self.assertIn("skip\taa-stay\t", real.stdout)

            again = subprocess.run(
                ["python3", str(RAISE), "--root", str(root), "--date", "2026-11-08"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(again.returncode, 0, again.stderr)
            twice = json.loads((stages / "aa-raise.json").read_text(encoding="utf-8"))
            self.assertEqual(len(twice["ceiling_history"]), 1)

            exclusions = root / "eval" / "catalog-queue" / "exclusions.tsv"
            exclusions.parent.mkdir(parents=True, exist_ok=True)
            exclusions.write_text("slug\treason\nzz-mark\tneeds Mark\n", encoding="utf-8")
            needs = subprocess.run(
                ["python3", str(NEEDS), "--root", str(root)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(needs.returncode, 0, needs.stderr)
            text = (root / "eval" / "catalog-queue" / "needs-mark.tsv").read_text(encoding="utf-8")
            self.assertTrue(text.startswith("slug\tkind\treason\tevidence\tsince\n"))
            self.assertNotIn("/home/", text)
            self.assertIn("aa-sec\trisky-class\tsecurity\t", text)
            self.assertIn("aa-money\trisky-class\tlive-money\t", text)
            self.assertIn("aa-take\trisky-class\truntime-takeover\t", text)
            self.assertIn("aa-unknown\trisky-class\tunknown\t", text)
            self.assertIn("zz-mark\texcluded\tneeds Mark\t", text)
            first = text
            second = subprocess.run(
                ["python3", str(NEEDS), "--root", str(root)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("unchanged", second.stdout)
            self.assertEqual((root / "eval" / "catalog-queue" / "needs-mark.tsv").read_text(encoding="utf-8"), first)

    def test_gpu_and_over_25gb_do_not_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stages = root / "data" / "stages"
            stages.mkdir(parents=True)
            write_card(stages, "aa-gpu", card("aa-gpu", uses="needs a gpu"))
            write_card(stages, "aa-huge", card("aa-huge", uses="pull a 37.6 GB pack"))
            write_card(stages, "aa-open", card("aa-open", uses="open-weights format"))
            verdict(root, "aa-gpu")
            verdict(root, "aa-huge")
            verdict(root, "aa-open")
            proc = subprocess.run(
                ["python3", str(RAISE), "--root", str(root), "--date", "2026-11-08"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("refuse\taa-gpu\tgpu", proc.stdout)
            self.assertIn("refuse\taa-huge\tpull-over-25gb", proc.stdout)
            self.assertIn("raise\taa-open\t", proc.stdout)
            for slug in ("aa-gpu", "aa-huge"):
                check = subprocess.run(
                    ["python3", str(RAISE), "--root", str(root), "--launch-check", slug],
                    capture_output=True, text=True, timeout=30,
                )
                self.assertEqual(check.returncode, 0, check.stderr)
                self.assertTrue(check.stdout.startswith("skip\t"), check.stdout)
            open_check = subprocess.run(
                ["python3", str(RAISE), "--root", str(root), "--launch-check", "aa-open"],
                capture_output=True, text=True, timeout=30,
            )
            self.assertTrue(open_check.stdout.startswith("launch\t"), open_check.stdout)
            needs = subprocess.run(
                ["python3", str(NEEDS), "--root", str(root)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(needs.returncode, 0, needs.stderr)
            text = (root / "eval" / "catalog-queue" / "needs-mark.tsv").read_text(encoding="utf-8")
            self.assertIn("aa-gpu\tgpu\t", text)
            self.assertIn("aa-huge\tpull-over-25gb\t", text)
            self.assertNotIn("aa-open\tgpu\t", text)
            self.assertNotIn("aa-open\trisky-class\t", text)
