"""Loop Launch fills empty toolsets/harness instead of FAIL review incomplete."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LIVE = lambda: (
    "http://127.0.0.1:11434/v1",
    {"engine": "openai-compat", "status": "ready", "base_url": "http://127.0.0.1:11434/v1"},
)


class LaunchComposeDefaultTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pfy-compose-"))
        self.state = self.tmp / "state"
        self.state.mkdir()
        self.wiz = _load("pfy_launch_wizard_225", ROOT / "scripts" / "pfy_launch_wizard_225.py")
        self.wiz._probe_ft = lambda: False

    def _ready_lane(self):
        rt = self.wiz.probe_runtime(self.state, live_openai_base=LIVE)
        self.assertTrue(rt.get("ok"), rt)
        ln = self.wiz.set_lane(self.state, "local", live_openai_base=LIVE)
        self.assertTrue(ln.get("ok"), ln)

    def test_catalog_skip_keeps_prior_toolset(self):
        self._ready_lane()
        bare = self.wiz.set_toolset(
            self.state, "bare", ROOT=ROOT, which=lambda *a: "", live_openai_base=LIVE
        )
        self.assertTrue(bare.get("ok"), bare)
        skipped = self.wiz.set_toolset(
            self.state, "catalog", ROOT=ROOT, which=lambda *a: "", live_openai_base=LIVE
        )
        self.assertEqual(skipped.get("live"), "SKIP")
        self.assertEqual(self.wiz.load_comp(self.state).get("toolsets"), "bare")

    def test_empty_toolsets_and_harness_review_after_defaults(self):
        self._ready_lane()
        comp = self.wiz.load_comp(self.state)
        comp["toolsets"] = ""
        comp["harness"] = ""
        comp["step"] = "harness"
        self.wiz.save_comp(self.state, comp)
        filled = self.wiz.ensure_compose_defaults(
            self.state,
            toolsets=("orchestration", "code-graph", "bare"),
            harness="grok",
            live_openai_base=LIVE,
            ROOT=ROOT,
            which=lambda *a: "",
        )
        self.assertTrue(filled.get("ok"), filled)
        rev = self.wiz.review(self.state, live_openai_base=LIVE)
        self.assertTrue(rev.get("ok"), rev)
        self.assertNotIn("incomplete", rev.get("copy") or "")
        self.assertEqual(rev.get("toolsets"), "orchestration")
        self.assertEqual(rev.get("harness"), "grok")

    def test_loop_toolset_order_prefers_later_module(self):
        os.environ["PFY_STATE_DIR"] = str(self.state)
        (self.state / "loop-modules.json").write_text(
            json.dumps(
                {
                    "enabled": ["jev", "code-graph", "orchestration", "catalog-ask"],
                    "task": "hard",
                }
            ),
            encoding="utf-8",
        )
        board = _load("pfy_board_launch_defaults", ROOT / "scripts" / "pfy-board.py")
        self.assertEqual(
            board._loop_toolset_order(),
            ["orchestration", "code-graph", "bare"],
        )


if __name__ == "__main__":
    unittest.main()
