"""Browse shows the stage card, including a parenthetical TOOLS.md name.

Fail: the Active Catalog cell `**adr-tools** (optional)` slugs to
adr-tools-optional, so browse leaves the stage blank, and a stale
tools.json stage (codebase-memory-mcp I2) hides the card (I3).
A stage card that intake wrote is also missing, because browse kept only
the Active Catalog table.
Recovery: the bold name joins the card, and the card stage replaces the
json stage. Display name stays the full cell. An unmatched stage card is
listed after those rows. integration_stage is not written. A bad stage
file hides card stages until that file is removed; the table names stay.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
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
        self.assertIn("Pipeline", rows["adr-tools (optional)"]["category"])
        self.assertNotIn("adr-tools", rows)
        # Under another heading in TOOLS.md. The card is the browse row.
        self.assertEqual(rows["Auto-Company"]["stage"], cards["Auto-Company"]["integration_stage"])
        self.assertEqual(rows["Auto-Company"]["category"], "")
        self.assertEqual(rows["Auto-Company"]["github"], cards["Auto-Company"]["github"])
        self.assertEqual(rows["LiveKit"]["stage"], cards["LiveKit"]["integration_stage"])
        names = [r["name"] for r in self.mod.load_catalog(ROOT)]
        self.assertEqual(len(names), len(set(names)))
        self.assertLess(names.index("adr-tools (optional)"), names.index("Auto-Company"))
        self.assertLess(names.index("adr-tools (optional)"), names.index("LiveKit"))

    def test_fresh_stage_card_is_listed_and_the_table_stays(self):
        md = """
## Active Catalog

| Tool | Primary Cat | GitHub | S1 | S2 | S3 | S4 | Overall | Tier | Key Tags | Notes |
|------|-------------|--------|----|----|----|----|---------|------|----------|-------|
| **widget** (optional) | Pipeline | https://example.com/widget | 1 | 1 | 1 | 1 | 1 | B | #pipe | optional cli |
| **other** | Agents | https://example.com/other | 1 | 1 | 1 | 1 | 1 | B | #a | plain |

## Autonomous AI Companies

| Tool | Primary Cat | GitHub | C1 Org |
|------|-------------|--------|--------|
| **Auto-Company** | Autonomous AI Companies | https://example.com/auto | 5 |
| **ghost** | Autonomous AI Companies | https://example.com/ghost | 1 |
"""
        with tempfile.TemporaryDirectory(prefix="browse-stage-only-") as tmp:
            root = Path(tmp)
            state = root / "state"
            state.mkdir()
            (root / "TOOLS.md").write_text(md, encoding="utf-8")
            before = (root / "TOOLS.md").read_text(encoding="utf-8")
            write_tool(root, "widget", {"integration_stage": "I1", "github": "https://example.com/widget"})
            write_tool(root, "other", {"integration_stage": "I2"})
            write_tool(
                root,
                "gum",
                {
                    "integration_stage": "I0",
                    "github": "https://github.com/charmbracelet/gum",
                    "tier_ceiling": "I1",
                },
            )
            write_tool(
                root,
                "Auto-Company",
                {
                    "integration_stage": "I1",
                    "github": "https://github.com/MaxMiksa/Auto-Company",
                },
            )
            gum_path = root / "data" / "stages" / "gum.json"
            gum_before = gum_path.read_text(encoding="utf-8")
            rows = self.mod.load_catalog(root)
            names = [r["name"] for r in rows]
            by = {r["name"]: r for r in rows}
            self.assertEqual(names[:2], ["other", "widget (optional)"])
            self.assertEqual(by["widget (optional)"]["stage"], "I1")
            self.assertEqual(by["widget (optional)"]["category"], "Pipeline")
            self.assertEqual(by["other"]["stage"], "I2")
            self.assertNotIn("widget", names)
            self.assertNotIn("ghost", names)
            self.assertEqual(by["gum"]["stage"], "I0")
            self.assertEqual(by["gum"]["status"], "incomplete")
            self.assertEqual(by["gum"]["github"], "https://github.com/charmbracelet/gum")
            self.assertEqual(by["gum"]["category"], "")
            self.assertNotIn("s1", by["gum"])
            self.assertEqual(by["Auto-Company"]["stage"], "I1")
            self.assertEqual(by["Auto-Company"]["category"], "")
            self.assertEqual(by["Auto-Company"]["github"], "https://github.com/MaxMiksa/Auto-Company")
            self.assertLess(names.index("widget (optional)"), names.index("Auto-Company"))
            self.assertLess(names.index("Auto-Company"), names.index("gum"))
            self.assertEqual(gum_path.read_text(encoding="utf-8"), gum_before)
            self.assertEqual((root / "TOOLS.md").read_text(encoding="utf-8"), before)
            asked = self.mod.ask_implement(
                root, state, name="gum", attached="grok", pid_alive=lambda p: True
            )
            self.assertFalse(asked.get("ok"))
            self.assertTrue(asked.get("skipped") or asked.get("live") == "SKIP")
            self.assertEqual(gum_path.read_text(encoding="utf-8"), gum_before)
            env = {
                "PFY_ROOT": str(root),
                "PFY_STATE_DIR": str(state),
            }
            old = {k: os.environ.get(k) for k in env}
            os.environ.update(env)
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rc = self.mod.cmd_browse([])
            finally:
                for key, val in old.items():
                    if val is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = val
            text = buf.getvalue()
            self.assertEqual(rc, 0)
            self.assertIn("gum\tI0\tincomplete", text)
            self.assertIn("widget (optional)\tI1", text)
            self.assertNotIn("ghost", text)
            self.assertEqual(gum_path.read_text(encoding="utf-8"), gum_before)

    def test_bad_stage_file_keeps_table_names_until_it_is_removed(self):
        md = """
## Active Catalog

| Tool | Primary Cat | GitHub | S1 | S2 | S3 | S4 | Overall | Tier | Key Tags | Notes |
|------|-------------|--------|----|----|----|----|---------|------|----------|-------|
| **widget** | Pipeline | https://example.com/widget | 1 | 1 | 1 | 1 | 1 | B | #pipe | plain |
"""
        with tempfile.TemporaryDirectory(prefix="browse-stage-bad-") as tmp:
            root = Path(tmp)
            (root / "TOOLS.md").write_text(md, encoding="utf-8")
            write_tool(root, "widget", {"integration_stage": "I1", "github": "https://example.com/widget"})
            write_tool(root, "gum", {"integration_stage": "I0", "github": "https://github.com/charmbracelet/gum"})
            gum_path = root / "data" / "stages" / "gum.json"
            gum_before = gum_path.read_text(encoding="utf-8")
            broken = root / "data" / "stages" / "broken.json"
            broken.write_text("{", encoding="utf-8")
            hidden = {r["name"]: r for r in self.mod.load_catalog(root)}
            self.assertIn("widget", hidden)
            self.assertEqual(hidden["widget"]["category"], "Pipeline")
            self.assertEqual(hidden["widget"]["stage"], "")
            self.assertNotIn("gum", hidden)
            self.assertEqual(gum_path.read_text(encoding="utf-8"), gum_before)
            broken.unlink()
            back = {r["name"]: r for r in self.mod.load_catalog(root)}
            self.assertEqual(back["widget"]["stage"], "I1")
            self.assertEqual(back["gum"]["stage"], "I0")
            self.assertEqual(gum_path.read_text(encoding="utf-8"), gum_before)
