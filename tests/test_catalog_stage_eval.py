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

    def test_fifty_rows_and_handoff_keys(self):
        rows = self.mod.parse_tools_md((ROOT / "TOOLS.md").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 50)
        handoff = json.loads((ROOT / "data" / "catalog_stage_handoff.json").read_text(encoding="utf-8"))
        names = {r["name"] for r in self.mod.evaluations()}
        self.assertEqual(names, set(handoff))

    def test_posture_and_ceiling_are_not_promotions(self):
        by = {r["name"]: r for r in self.mod.evaluations()}
        self.assertIn("not_integrated", by["Graphify"]["posture"])
        self.assertEqual(by["Graphify"]["tier_ceiling"], "I0")
        self.assertEqual(by["Graphify"]["integration_stage"], "I0")
        self.assertEqual(by["AgenC"]["tier_ceiling"], "I0")
        self.assertEqual(by["codebase-memory-mcp"]["tier_ceiling"], "I3")
        self.assertEqual(by["codebase-memory-mcp"]["integration_stage"], "I2")
        self.assertIn("make:smoke-codebase-memory", by["codebase-memory-mcp"]["evidence"])


if __name__ == "__main__":
    unittest.main()
