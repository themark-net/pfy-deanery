"""Security scanners and guards: I2 sandbox trial without the operator, I3 only with the full gate.

Operator decision 2026-11-10. How this fails: a security card is raised past
I2 by the loop, a security verdict lands I2 without a sandboxed trial, or a
security card reaches I3 without a Tester and Reviewer PASS at one pinned
SHA on origin/main. How we recover: auto-raise stops at I2, apply caps a
verdict without "sandbox": "sandlock" at I1 and a card without a passing
gate:eval/integrate/<slug>/GATE.json at I2. Every refusal keeps the card bytes.
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from tests.test_catalog_apply_verdict_receipt import load_mod, make_repo, write_receipt

ROOT = Path(__file__).resolve().parents[1]
RAISE = ROOT / "scripts" / "catalog_auto_raise.py"


def load_raise():
    spec = importlib.util.spec_from_file_location("auto_raise_security_test", RAISE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sec_card(repo: Path, slug: str, stage: str = "I2", ceiling: str = "I3", gate: bool = True) -> Path:
    path = repo / "data" / "stages" / f"{slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    evidence = ["entry:sources/entries/001-x.md", f"receipt:eval/integrate/{slug}/receipt.json"]
    if gate:
        evidence.append(f"gate:eval/integrate/{slug}/GATE.json")
    body = {"name": slug, "integration_stage": stage, "tier_ceiling": ceiling, "risk_class": "security",
            "uses": "Scan lockfiles.", "evidence": evidence}
    path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
    return path


def write_gate(repo: Path, slug: str, pinned: str, tester: str = "PASS", reviewer: str = "PASS", reviewer_sha: str | None = None) -> None:
    path = repo / "eval" / "integrate" / slug / "GATE.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "slug": slug,
        "pinned_sha": pinned,
        "tester": {"verdict": tester, "sha": pinned},
        "reviewer": {"verdict": reviewer, "sha": reviewer_sha or pinned},
    }), encoding="utf-8")


class SecurityApplyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = load_mod()
        self._td = tempfile.TemporaryDirectory()
        self.td = Path(self._td.name)
        self.repo, self.main_sha, self.side_sha = make_repo(self.td)

    def tearDown(self) -> None:
        self._td.cleanup()

    def _apply(self, slug: str, card: Path, stage: str, sandbox: bool = True):
        v = {"metric": "probe_exit", "threshold": 0, "value": 0, "value_gate": "pass",
             "modularity_gate": "pass", "proposed_stage": stage}
        if sandbox:
            v["sandbox"] = "sandlock"
        vp = self.repo / "eval" / "integrate" / slug / "VERDICT.json"
        vp.parent.mkdir(parents=True, exist_ok=True)
        vp.write_text(json.dumps(v), encoding="utf-8")
        before = card.read_bytes()
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                self.mod.apply_verdict(card, vp, None, self.repo)
        except self.mod.Refuse as exc:
            self.assertEqual(card.read_bytes(), before)
            return str(exc)
        return None

    def _stage(self, card: Path) -> str:
        return json.loads(card.read_text(encoding="utf-8"))["integration_stage"]

    def test_i3_needs_a_passing_gate_at_one_pinned_main_sha(self) -> None:
        cases = {
            "nogate": None,
            "notpass": dict(reviewer="FAIL"),
            "mismatch": dict(reviewer_sha="c" * 40),
            "offmain": "side",
        }
        for slug, how in cases.items():
            write_receipt(self.repo, slug, self.main_sha)
            card = sec_card(self.repo, slug)
            if how == "side":
                write_gate(self.repo, slug, self.side_sha)
            elif how is not None:
                write_gate(self.repo, slug, self.main_sha, **how)
            err = self._apply(slug, card, "I3")
            self.assertIsNotNone(err, slug)
            self.assertIn("full gate", err, slug)
            self.assertEqual(self._stage(card), "I2", slug)
        write_receipt(self.repo, "passing", self.main_sha)
        card = sec_card(self.repo, "passing")
        write_gate(self.repo, "passing", self.main_sha)
        self.assertIsNone(self._apply("passing", card, "I3"))
        self.assertEqual(self._stage(card), "I3")

    def test_security_verdict_without_sandlock_caps_at_i1(self) -> None:
        card = sec_card(self.repo, "trial", stage="I1", ceiling="I2", gate=False)
        err = self._apply("trial", card, "I2", sandbox=False)
        self.assertIsNotNone(err)
        self.assertIn("sandbox sandlock", err)
        self.assertEqual(self._stage(card), "I1")

    def test_receipt_link_still_skips_security(self) -> None:
        write_receipt(self.repo, "sec", self.main_sha)
        path = self.repo / "data" / "stages" / "sec.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"name": "sec", "integration_stage": "I2", "tier_ceiling": "I3", "risk_class": "security", "evidence": []}), encoding="utf-8")
        card = json.loads(path.read_text(encoding="utf-8"))
        _c, linked, note = self.mod.link_main_receipt(card, self.repo, "sec")
        self.assertIsNone(linked)
        self.assertEqual(note, "risk-class security")


class SecurityRaiseTest(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = load_raise()

    def test_security_raises_to_i2_only_and_never_to_i3(self) -> None:
        base = {"risk_class": "security", "uses": "scan", "integration_stage": "I0"}
        self.assertEqual(self.mod.plan_card(dict(base, tier_ceiling="I1"), None)[0], "raise")
        self.assertEqual(self.mod.raise_target(dict(base, tier_ceiling="I1")), "I2")
        passing = {"value_gate": "pass", "modularity_gate": "pass"}
        self.assertEqual(self.mod.plan_card(dict(base, tier_ceiling="I2"), passing), ("skip", "security: I3 needs the full gate"))
        self.assertEqual(self.mod.plan_card(dict(base, tier_ceiling="I1", uses="scan with a gpu"), None), ("refuse", "gpu"))
        self.assertEqual(self.mod.plan_card({"risk_class": "live-money", "uses": "x", "tier_ceiling": "I1"}, passing), ("refuse", "live-money"))
        self.assertEqual(self.mod.raise_target({"risk_class": "none", "uses": "x"}), "I3")

    def test_launch_check_sandboxes_a_security_trial_below_i2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stages = root / "data" / "stages"
            stages.mkdir(parents=True)
            (root / "eval" / "catalog-queue").mkdir(parents=True)
            (root / "eval" / "catalog-queue" / "exclusions.tsv").write_text("slug\treason\n", encoding="utf-8")
            for slug, stage, ceiling in (("low", "I1", "I2"), ("capped", "I1", "I1"), ("done", "I2", "I3")):
                (stages / f"{slug}.json").write_text(json.dumps({"name": slug, "integration_stage": stage, "tier_ceiling": ceiling, "risk_class": "security", "uses": "scan"}), encoding="utf-8")
            got = {}
            for slug in ("low", "capped", "done"):
                out = subprocess.run(["python3", str(RAISE), "--root", str(root), "--launch-check", slug], capture_output=True, text=True, timeout=30)
                got[slug] = out.stdout.strip()
            self.assertEqual(got["low"], "launch\tlow\tsecurity-sandbox")
            self.assertEqual(got["capped"], "skip\tcapped\tsecurity")
            self.assertEqual(got["done"], "skip\tdone\tsecurity")


if __name__ == "__main__":
    unittest.main()
