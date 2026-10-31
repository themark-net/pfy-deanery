"""Stage facts come from the catalog table. Potential stays a handoff judgment."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("catalog_stage_eval", ROOT / "scripts" / "catalog_stage_eval.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CatalogStageEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_every_tools_md_row_has_handoff_keys(self):
        rows = self.mod.parse_tools_md((ROOT / "TOOLS.md").read_text(encoding="utf-8"))
        handoff = json.loads((ROOT / "data" / "catalog_stage_handoff.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(rows), 50)
        self.assertEqual(len(rows), len(handoff))
        names = {r["name"] for r in self.mod.evaluations()}
        self.assertEqual(names, set(handoff))
        self.assertIn("Kolibri-1", names)

    def test_posture_and_ceiling_are_not_promotions(self):
        by = {r["name"]: r for r in self.mod.evaluations()}
        self.assertIn("not_integrated", by["Graphify"]["posture"])
        self.assertEqual(by["Graphify"]["tier_ceiling"], "I0")
        self.assertEqual(by["Graphify"]["integration_stage"], "I0")
        self.assertEqual(by["AgenC"]["tier_ceiling"], "I0")
        self.assertEqual(by["codebase-memory-mcp"]["tier_ceiling"], "I3")
        self.assertEqual(by["codebase-memory-mcp"]["integration_stage"], "I2")
        self.assertIn("make:smoke-codebase-memory", by["codebase-memory-mcp"]["evidence"])

    def test_kolibri_facts_match_the_catalog_and_stage_stays_i0(self):
        stages = json.loads((ROOT / "data" / "tool_integration_stages.json").read_text(encoding="utf-8"))
        card = stages["tools"]["Kolibri-1"]
        ev = {r["name"]: r for r in self.mod.evaluations()}["Kolibri-1"]
        self.assertEqual(card["integration_stage"], "I0")
        self.assertEqual(card["catalog_tier"], ev["tier"])
        self.assertEqual(card["catalog_overall"], ev["overall"])
        self.assertEqual(card["catalog_tags"], ev["tags"])
        self.assertEqual(card["catalog_github"], ev["github"])
        self.assertEqual(card["posture"], ev["posture"])
        self.assertEqual(card["evidence"], ev["evidence"])
        self.assertEqual(card["tier_ceiling"], ev["tier_ceiling"])
        self.assertEqual(card["potential"], ev["handoff"]["potential"])

    def test_blind_apply_would_drop_live_receipts_so_disk_keeps_them(self):
        """--apply copies recomputed facts over the card. Those facts omit the
        live ATG and harness2 receipts and would replace measured-probe with
        the older handoff potential. Recovery: restore the card from git and
        do not re-apply. Update this test only after evidence_for keeps the
        receipt path."""
        stages = json.loads((ROOT / "data" / "tool_integration_stages.json").read_text(encoding="utf-8"))
        by = {r["name"]: r for r in self.mod.evaluations()}
        atg = stages["tools"]["Atomic Task Graph (ATG)"]
        harness = stages["tools"]["harness2"]
        atg_receipt = "receipt:pipelines/dogfood/atg-compile/receipt-live-qwen36-35b.json"
        harness_receipt = "pipelines/dogfood/harness2-local/receipt.json"
        proposed_atg = by["Atomic Task Graph (ATG)"]
        proposed_harness = by["harness2"]
        self.assertIn(atg_receipt, atg["evidence"])
        self.assertNotIn(atg_receipt, proposed_atg["evidence"])
        self.assertEqual(atg["potential"], "measured-probe")
        self.assertEqual(proposed_atg["handoff"]["potential"], "ambiguous")
        self.assertEqual(atg["integration_stage"], "I2")
        self.assertEqual(atg["tier_ceiling"], "I2")
        self.assertEqual(proposed_atg["tier_ceiling"], "I1")
        self.assertIn(harness_receipt, harness["evidence"])
        self.assertNotIn(harness_receipt, proposed_harness["evidence"])
        self.assertEqual(harness["integration_stage"], "I1")
        self.assertNotEqual(stages["last_updated"], "2026-09-25")


if __name__ == "__main__":
    unittest.main()
