"""Loop and Engine model controls stay prefilled and route compare through the CLI gate.

Fail: the view invents a cloud default, or Run it spends without the confirm
step. Recovery: rows show the committed local model, and the first click only
returns the price line.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import model_choice as mc  # noqa: E402
from tests._model_choice_isolation import begin as iso_begin, end as iso_end  # noqa: E402


def _load_gui():
    spec = importlib.util.spec_from_file_location("pfy_gui_model_choice", ROOT / "scripts" / "pfy-gui.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class GuiModelChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.gui = _load_gui()

    def setUp(self) -> None:
        self.tmp, self.iso_saved = iso_begin(prefix="pfy-gui-model-")
        self._home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.tmp / "home")
        (self.tmp / "home").mkdir()
        self.calls: list[dict] = []
        self._transport = mc._TRANSPORT
        mc._TRANSPORT = self._refuse

    def tearDown(self) -> None:
        mc._TRANSPORT = self._transport
        if self._home is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._home
        iso_end(self.tmp, self.iso_saved)

    def _refuse(self, req: dict) -> dict:
        self.calls.append(req)
        raise AssertionError("provider called")

    def test_loop_text_prefills_local_and_names_compare(self) -> None:
        body = self.gui.loop_text(
            {"modules": [], "hedge": {}},
            "SKIP",
            "(none)",
            "(none)",
            "gui",
            "",
        )
        block = body.split("WORK CLASS", 1)[0]
        self.assertIn("TASK MODELS", block)
        self.assertIn("catalog-fit", block)
        self.assertIn("local", block)
        self.assertIn("qwen3.6:35b", block)
        self.assertIn("Compare last local", block)
        self.assertNotIn("grok-4.7", block.split("compare", 1)[0])

    def test_compare_control_returns_the_price_line_and_does_not_call(self) -> None:
        result = self.gui.confirm_compare(
            yes=False,
            isatty=False,
            root=ROOT,
            out=str(self.tmp / "out.json"),
        )
        self.assertFalse(result.get("ran"))
        self.assertIn("grok-4.7", result.get("line") or "")
        self.assertIn("docs.x.ai/docs/models", result["line"])
        self.assertIn("fetched 2026-11-11", result["line"])
        self.assertIn("Run it? [y/N]", result["line"])
        self.assertEqual(self.calls, [])
        if "older than 45 days" in result["line"]:
            self.assertEqual(result.get("blocked"), "stale price")
            self.assertFalse(result.get("needs_confirm"))
        else:
            self.assertTrue(result.get("needs_confirm"), result)
            self.assertEqual(result.get("blocked"), "no TTY")

    def test_html_and_script_route_confirm_through_the_server(self) -> None:
        doc = mc.gui_document(root=ROOT, probe=False, local_tags=[])
        html = doc["html"]
        self.assertIn("catalog-fit", html)
        self.assertIn('value="local:qwen3.6:35b" selected', html)
        self.assertIn('data-spec="local:', html)
        self.assertIn("cloud", html)
        page = (ROOT / "gui" / "operator" / "frontend" / "index.html").read_text(encoding="utf-8")
        self.assertEqual(page.count("Compare last local catalog-fit run"), 2)
        self.assertIn('id=task-models', page)
        self.assertIn('id=task-models-engine', page)
        script = (ROOT / "gui" / "operator" / "frontend" / "app-ui.js").read_text(encoding="utf-8")
        self.assertIn("confirm:false", script)
        self.assertIn("confirm:true", script)
        self.assertIn("max_usd:compareOffer.cost_usd", script)
        self.assertNotIn("per 1M", script)
        self.assertNotIn("price_in", script)
        board = (ROOT / "scripts" / "pfy-board.py").read_text(encoding="utf-8")
        self.assertIn('path == "/model-choice"', board)
        self.assertIn("gui_document", board)
        self.assertIn("gui_set", board)
        self.assertIn("gui_compare", board)
        gui_src = (ROOT / "scripts" / "pfy-gui.py").read_text(encoding="utf-8")
        self.assertIn('txt += "\\n" + task_model_block()', gui_src)
        self.assertIn('"cmp"', gui_src)

    def test_set_is_explicit_and_run_it_still_obeys_the_cap(self) -> None:
        saved = mc.gui_set({"task": "catalog-fit", "spec": "cloud:grok-4.7"}, root=ROOT)
        self.assertTrue(saved["ok"])
        backend, model, source = mc.resolve("catalog-fit", root=ROOT)
        self.assertEqual((backend, model, source), ("cloud", "grok-4.7", "user"))
        preview = mc.gui_compare(
            {"task": "catalog-fit", "against": "grok-4.7", "confirm": False},
            root=ROOT,
        )
        self.assertTrue(preview.get("needs_confirm"))
        self.assertEqual(self.calls, [])
        blocked = mc.gui_compare(
            {
                "task": "catalog-fit",
                "against": "grok-4.7",
                "confirm": True,
                "max_usd": 0.0001,
            },
            root=ROOT,
        )
        self.assertFalse(blocked.get("ran"))
        self.assertIn("exceeds", blocked.get("blocked") or blocked.get("line") or "")
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
