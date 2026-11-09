"""Browse shows the stage card, including a parenthetical TOOLS.md name.

Fail: the Active Catalog cell `**adr-tools** (optional)` slugs to
adr-tools-optional, so browse leaves the stage blank, and a stale
tools.json stage (codebase-memory-mcp I2) hides the card (I3).
Recovery: the bold name joins the card, and the card stage replaces the
json stage. Display name stays the full cell.
"""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from pfylib.stage_registry import load_stages, write_tool

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "pfy_catalog_ask_queue_209",
        ROOT / "scripts" / "pfy_catalog_ask_queue_209.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CatalogBrowseStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_parenthetical_name_and_stale_json_follow_the_card(self):
        md = """
## Active Catalog

| Tool | Primary Cat | GitHub | S1 | S2 | S3 | S4 | Overall | Tier | Key Tags | Notes |
|------|-------------|--------|----|----|----|----|---------|------|----------|-------|
| **widget** (optional) | Pipeline | https://example.com/widget | 1 | 1 | 1 | 1 | 1 | B | #pipe | optional cli |
| **other** | Agents | https://example.com/other | 1 | 1 | 1 | 1 | 1 | B | #a | plain |
"""
        with tempfile.TemporaryDirectory(prefix="browse-stage-") as tmp:
            root = Path(tmp)
            (root / "TOOLS.md").write_text(md, encoding="utf-8")
            (root / "data").mkdir()
            (root / "data" / "tools.json").write_text(
                json.dumps(
                    {
                        "tools": [
                            {
                                "name": "widget (optional)",
                                "integration_stage": "I0",
                                "github": "https://example.com/widget",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            write_tool(root, "widget", {"integration_stage": "I1", "github": "https://example.com/widget"})
            write_tool(root, "other", {"integration_stage": "I2"})
            rows = {r["name"]: r for r in self.mod.load_catalog(root)}
        self.assertEqual(set(rows), {"widget (optional)", "other"})
        self.assertEqual(rows["widget (optional)"]["stage"], "I1")
        self.assertEqual(rows["other"]["stage"], "I2")

    def test_live_catalog_rows_show_the_stage_card(self):
        rows = {r["name"]: r for r in self.mod.load_catalog(ROOT)}
        cards = load_stages(ROOT)["tools"]
        self.assertEqual(rows["adr-tools (optional)"]["stage"], cards["adr-tools"]["integration_stage"])
        self.assertEqual(rows["codebase-memory-mcp"]["stage"], cards["codebase-memory-mcp"]["integration_stage"])
        self.assertNotEqual(rows["adr-tools (optional)"]["stage"], "")
        names = [r["name"] for r in self.mod.load_catalog(ROOT)]
        self.assertEqual(len(names), len(set(names)))
