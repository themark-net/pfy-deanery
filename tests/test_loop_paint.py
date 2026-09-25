"""Loop paint: modules + local/cloud hedge (not a harness picker)."""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pfylib import loop_paint, registry  # noqa: E402


class LoopPaintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pfylib-loop-"))
        self.state = self.tmp / "state"
        self._saved = {k: os.environ.get(k) for k in ("PFY_STATE_DIR", "PFY_CLOUD_BUDGET", "DEPLOY_PROFILE", "GAB_API_KEY")}
        os.environ["PFY_STATE_DIR"] = str(self.state)
        os.environ.pop("PFY_CLOUD_BUDGET", None)
        os.environ.pop("DEPLOY_PROFILE", None)
        os.environ.pop("GAB_API_KEY", None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_fields_lists_every_toolset_and_hedge_split(self):
        local = {"engine": "freetoken", "base_url": "http://127.0.0.1:1919/v1", "status": "ready"}
        f = loop_paint.fields(state=self.state, root_dir=ROOT, local=local)
        ids = [m["id"] for m in f["modules"]]
        self.assertEqual(ids, registry.toolset_ids(ROOT))
        self.assertTrue(any(m["status"] == "implemented" for m in f["modules"]))
        self.assertTrue(any(m["status"] == "partial" for m in f["modules"]))
        # A module is stub only when every harness cell is stub (none of today's
        # gathered toolsets are all-stub — T-0121 wired remaining planners).
        self.assertFalse(any(m["status"] == "stub" for m in f["modules"]))
        h = f["hedge"]
        self.assertTrue(h["local_ready"])
        self.assertEqual(h["lane"], "local")
        self.assertEqual(h["routes"]["interactive"]["lane"], "local")
        self.assertIn("your machine", h["route"])
        self.assertTrue(h["local_meaning"])
        self.assertIn(h["routes"]["hard"]["lane"], ("local", "cloud", None))

    def test_toggle_rejects_stub_and_enables_implementable(self):
        r = loop_paint.toggle("jev", True, state=self.state, root_dir=ROOT)
        self.assertTrue(r["ok"], r)
        self.assertIn("jev", r["enabled"])
        r = loop_paint.toggle("orchestration", True, state=self.state, root_dir=ROOT)
        self.assertTrue(r["ok"], r)
        orig = registry.toolset
        def fake_toolset(tid, root=None):
            if tid == "ghost":
                return {"id": "ghost", "implementation": {"grok": {"status": "stub", "how": "no config surface"}}}
            return orig(tid, root)
        registry.toolset = fake_toolset
        try:
            r = loop_paint.toggle("ghost", True, state=self.state, root_dir=ROOT)
        finally:
            registry.toolset = orig
        self.assertFalse(r["ok"])
        self.assertEqual(r["live"], "STUB")
        self.assertNotIn("ghost", loop_paint.load_selection(self.state)["enabled"])

    def test_best_status_is_harness_agnostic(self):
        self.assertEqual(loop_paint._best_status({"g": {"status": "implemented"}, "x": {"status": "stub"}}), "implemented")
        self.assertEqual(loop_paint._best_status({"g": {"status": "partial"}, "x": {"status": "stub"}}), "partial")
        self.assertEqual(loop_paint._best_status({"g": {"status": "stub"}, "x": {"status": "stub"}}), "stub")
        self.assertEqual(loop_paint._best_status({}), "stub")

    def test_hedge_without_local_and_without_budget_fails_honestly(self):
        local = {"engine": "none", "base_url": "", "status": "missing"}
        f = loop_paint.fields(state=self.state, root_dir=ROOT, local=local)
        self.assertFalse(f["hedge"]["ok"])
        self.assertFalse(f["hedge"]["local_ready"])
        self.assertIn("PFY_CLOUD_BUDGET", f["hedge"]["next_step"] or f["hedge"]["copy"])
        self.assertIn("Not ready", f["hedge"]["route"])

    def test_hedge_cloud_when_local_missing_and_budget_set(self):
        os.environ["PFY_CLOUD_BUDGET"] = "3"
        local = {"engine": "none", "base_url": "", "status": "missing"}
        f = loop_paint.fields(state=self.state, root_dir=ROOT, local=local)
        self.assertEqual(f["hedge"]["lane"], "cloud")
        self.assertEqual(f["hedge"]["routes"]["interactive"]["lane"], "cloud")
        self.assertEqual(f["hedge"]["routes"]["hard"]["lane"], "cloud")

    def test_set_task_persists(self):
        r = loop_paint.set_task("hard", state=self.state)
        self.assertTrue(r["ok"], r)
        self.assertEqual(loop_paint.load_selection(self.state)["task"], "hard")
        f = loop_paint.fields(state=self.state, root_dir=ROOT, local={"engine": "none", "base_url": "", "status": "missing"})
        self.assertEqual(f["modules_task"], "hard")

    def test_agent_paint_is_for_the_selected_agent(self):
        loop_paint.set_agent("grok", state=self.state)
        f = loop_paint.fields(state=self.state, root_dir=ROOT, local={"engine": "none", "base_url": "", "status": "missing"})
        by = {m["id"]: m for m in f["modules"]}
        self.assertEqual(by["jev"]["agent_paint"], "wired")
        self.assertEqual(f["plan"], "Open grok with no toolsets yet")
        self.assertFalse(f["launch_ready"])
        loop_paint.toggle("jev", True, state=self.state, root_dir=ROOT)
        loop_paint.set_agent("hermes", state=self.state)
        f = loop_paint.fields(state=self.state, root_dir=ROOT, local={"engine": "none", "base_url": "", "status": "missing"})
        by = {m["id"]: m for m in f["modules"]}
        self.assertEqual(by["jev"]["agent_paint"], "partial")
        self.assertIn("Open Hermes with jev", f["plan"])
        self.assertTrue(f["launch_ready"])
        loop_paint.set_agent("gab", state=self.state)
        f = loop_paint.fields(state=self.state, root_dir=ROOT, local={"engine": "none", "base_url": "", "status": "missing"})
        self.assertIn("not wired for Gab", f["plan"])
        self.assertFalse(f["launch_ready"])

    def test_apply_enabled_empty_is_noop(self):
        out = loop_paint.apply_enabled(hid="grok", state=self.state, root_dir=ROOT, yes=True)
        self.assertEqual(out, [])


if __name__ == "__main__":
    unittest.main()
