"""Stage facts come from the catalog table. Potential stays a handoff judgment."""
from __future__ import annotations

import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from pfylib.stage_registry import load_stages, write_registry, write_tool

ROOT = Path(__file__).resolve().parents[1]


def _stage_snapshot() -> dict[str, bytes]:
    base = ROOT / "data" / "stages"
    return {p.name: p.read_bytes() for p in sorted(base.glob("*.json"))}


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
        stages = load_stages(ROOT)
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

    def test_apply_keeps_live_receipts_and_does_not_rewind(self):
        """Fail: --apply drops a receipt whose file still exists, rewinds
        last_updated to 2026-09-25, lowers the ATG tier ceiling, or replaces
        measured-probe with the older handoff potential.
        Recovery: keep file-backed receipt evidence, keep the existing stamp,
        do not lower tier_ceiling, and do not replace a potential the card
        already has. A receipt path whose file is missing is not kept.
        The real stage files on disk must be unchanged."""
        mod = self.mod
        real_files = _stage_snapshot()
        stages = load_stages(ROOT)
        atg_receipt = "receipt:pipelines/dogfood/atg-compile/receipt-live-qwen36-35b.json"
        harness_receipt = "pipelines/dogfood/harness2-local/receipt.json"
        missing = "receipt:pipelines/dogfood/atg-compile/does-not-exist.json"
        self.assertTrue((ROOT / atg_receipt.split(":", 1)[1]).is_file())
        self.assertTrue((ROOT / harness_receipt).is_file())
        self.assertFalse((ROOT / missing.split(":", 1)[1]).exists())
        stages["tools"]["Atomic Task Graph (ATG)"]["evidence"].append(missing)
        before_stamp = stages["last_updated"]
        self.assertNotEqual(before_stamp, "2026-09-25")
        for card in stages["tools"].values():
            card["last_updated"] = before_stamp
        saved = (mod.STAGES_ROOT, mod.HANDOFF_PATH, mod.METHODS_PATH)
        try:
            with tempfile.TemporaryDirectory(prefix="stage-apply-") as td:
                tdir = Path(td)
                handoff_path = tdir / "handoff.json"
                methods_path = tdir / "methods.json"
                write_registry(tdir, {k: v for k, v in stages.items() if k not in ("tools", "last_updated")})
                for name, card in stages["tools"].items():
                    write_tool(tdir, name, card)
                shutil.copy(ROOT / "data" / "catalog_stage_handoff.json", handoff_path)
                methods_src = ROOT / "data" / "catalog_stage_methods.json"
                if methods_src.is_file():
                    shutil.copy(methods_src, methods_path)
                else:
                    methods_path.write_text("{}\n", encoding="utf-8")
                mod.STAGES_ROOT = tdir
                mod.HANDOFF_PATH = handoff_path
                mod.METHODS_PATH = methods_path
                self.assertEqual(mod.apply(), 0)
                got = load_stages(tdir)
                registry = json.loads((tdir / "data" / "stages" / "_registry.json").read_text(encoding="utf-8"))
                self.assertNotIn("last_updated", registry)
                for path in (tdir / "data" / "stages").glob("*.json"):
                    self.assertNotIn("2026-09-25", path.read_text(encoding="utf-8"))
        finally:
            mod.STAGES_ROOT, mod.HANDOFF_PATH, mod.METHODS_PATH = saved
        atg = got["tools"]["Atomic Task Graph (ATG)"]
        harness = got["tools"]["harness2"]
        self.assertIn(atg_receipt, atg["evidence"])
        self.assertNotIn(missing, atg["evidence"])
        self.assertEqual(atg["potential"], "measured-probe")
        self.assertEqual(atg["tier_ceiling"], "I2")
        self.assertEqual(atg["integration_stage"], "I2")
        self.assertIn(harness_receipt, harness["evidence"])
        self.assertEqual(harness["integration_stage"], "I1")
        self.assertEqual(got["last_updated"], before_stamp)
        by = {row["name"]: row for row in mod.evaluations()}
        self.assertIn(atg_receipt, by["Atomic Task Graph (ATG)"]["evidence"])
        self.assertIn(harness_receipt, by["harness2"]["evidence"])
        self.assertEqual(_stage_snapshot(), real_files)


if __name__ == "__main__":
    unittest.main()
