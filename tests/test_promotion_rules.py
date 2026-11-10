"""data/promotion-rules.json is the only promotion authority, and it fails closed.

How this fails: the rules file names a rule with no check (or a check is not
in the file) and a card moves on a rule nobody wrote down; a hard stop is
added or dropped silently; the doc or skill drifts from the file; or the
ledger grows a new entry every tick. How we recover: load_rules raises
RuleError and apply, auto-raise, and launch-check refuse; the hard-stop set
is pinned here; the doc and skill name every rule ID; equal entries are not
appended twice.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import promotion_rules as pr  # noqa: E402

HARD = ["HS-live-money", "HS-release-deploy", "HS-secrets", "HS-runtime-takeover",
        "HS-gpu-unapproved", "HS-pull-over-25gb-unapproved"]


class PromotionRulesTest(unittest.TestCase):
    def test_file_loads_and_hard_stops_are_the_decided_five_classes(self) -> None:
        rules = pr.load_rules(ROOT)
        self.assertEqual(rules["hard_stops"], HARD)
        self.assertEqual(set(rules["rules"]), set(pr.CHECKS))
        self.assertEqual(rules["launch"][0], "R-not-excluded")
        for track in pr.TRACKS:
            ids = pr.rule_ids(rules, "stage", track, "I3")
            for rid in HARD + ["R-value-gate", "R-modularity-gate", "R-main-receipt"]:
                self.assertIn(rid, ids, track)
        security_i3 = pr.rule_ids(rules, "stage", "security", "I3")
        for rid in ("S-sandlock-trial-clean", "S-profile-readonly", "S-wiring", "S-ci-green"):
            self.assertIn(rid, security_i3)
        self.assertNotIn("S-wiring", pr.rule_ids(rules, "stage", "default", "I4"))

    def test_mismatch_between_file_and_checks_fails_closed(self) -> None:
        good = json.loads((ROOT / "data" / "promotion-rules.json").read_text(encoding="utf-8"))
        breaks = []
        extra = json.loads(json.dumps(good))
        extra["rules"]["R-made-up"] = {"modes": ["apply"], "check": "x"}
        breaks.append(extra)
        missing = json.loads(json.dumps(good))
        del missing["rules"]["S-wiring"]
        breaks.append(missing)
        undeclared = json.loads(json.dumps(good))
        undeclared["stage"]["default"]["I3"].append("R-nope")
        breaks.append(undeclared)
        soft = json.loads(json.dumps(good))
        soft["rules"]["HS-secrets"].pop("hard_stop")
        breaks.append(soft)
        for broken in breaks:
            with tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / "data").mkdir()
                (root / "data" / "promotion-rules.json").write_text(json.dumps(broken), encoding="utf-8")
                with self.assertRaises(pr.RuleError):
                    pr.load_rules(root)
                (root / "data" / "stages").mkdir()
                (root / "data" / "stages" / "x.json").write_text(json.dumps({"name": "x", "integration_stage": "I0", "uses": "format logs"}), encoding="utf-8")
                out = subprocess.run([sys.executable, str(ROOT / "scripts" / "catalog_auto_raise.py"), "--root", str(root), "--launch-check", "x"],
                                     capture_output=True, text=True, timeout=30)
                self.assertNotEqual(out.returncode, 0)
                self.assertNotIn("launch", out.stdout)

    def test_doc_and_skills_name_every_rule(self) -> None:
        rules = pr.load_rules(ROOT)
        doc = (ROOT / "docs" / "ops" / "promotion-rules.md").read_text(encoding="utf-8")
        skill = (ROOT / "bootstrap/grok-cli/skills/catalog-apply-and-ceiling/SKILL.md").read_text(encoding="utf-8")
        for rid in rules["rules"]:
            self.assertIn(f"`{rid}`", doc, rid)
        for rid in HARD + ["S-sandlock-trial-clean", "S-profile-readonly", "S-wiring", "S-ci-green"]:
            self.assertIn(rid, skill, rid)
        self.assertNotIn("GATE.json", skill.replace("There is no GATE.json", ""))

    def test_ledger_entry_is_not_appended_twice(self) -> None:
        rules = pr.load_rules(ROOT)
        card: dict = {}
        results = [("R-evidence", True, "ok"), ("R-tier-ceiling", False, "tier_ceiling I1 caps I2")]
        first = pr.ledger_entry(rules, "stage", "I1", "I2", "refuse", results, "2026-11-10", "eval/x/VERDICT.json")
        self.assertTrue(pr.append_ledger(card, first))
        again = pr.ledger_entry(rules, "stage", "I1", "I2", "refuse", results, "2026-11-11", "eval/x/VERDICT.json")
        self.assertFalse(pr.append_ledger(card, again))
        self.assertEqual(card["promotion_history"][0]["failed"], [{"rule": "R-tier-ceiling", "detail": "tier_ceiling I1 caps I2"}])
        self.assertEqual(card["promotion_history"][0]["rules"], "data/promotion-rules.json@v1")

    def test_cli_prints_one_line_per_rule(self) -> None:
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "promotion_rules.py"), "--slug", "bumblebee", "--mode", "scan", "--target", "I3"],
                             capture_output=True, text=True, timeout=60, cwd=ROOT)
        self.assertIn(out.returncode, (0, 3), out.stderr)
        lines = out.stdout.splitlines()
        self.assertEqual(lines[0], "track security")
        self.assertTrue(all(line.split("\t")[0] in ("pass", "fail") for line in lines[1:]), out.stdout)


if __name__ == "__main__":
    unittest.main()
