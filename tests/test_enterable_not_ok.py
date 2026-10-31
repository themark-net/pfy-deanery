"""A failed launch must drop stale enterable steps.

The not-ok branch of arm_launch_env_session strips enterable and session
ids and then returns without storing that list. Callers still see the old ids.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    path = ROOT / "scripts" / "pfy_enterable_162.py"
    spec = importlib.util.spec_from_file_location("pfy_enterable_162_not_ok", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class EnterableNotOkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _load()

    def test_not_ok_drops_stale_enterable_step(self):
        """Fail: ok false leaves id enterable or session on next_steps.
        Recovery: store the stripped list before the early return.
        A status step that is not enterable or session stays.
        open_fn must not run, because the launch already failed."""
        called = []

        def open_fn():
            called.append("open")
            raise AssertionError("open_fn must not run when ok is false")

        out = self.mod.arm_launch_env_session(
            {
                "ok": False,
                "live": "FAIL",
                "next_steps": [
                    {"id": "enterable", "label": "old", "value": "old"},
                    {"id": "session", "label": "old session", "value": "old session"},
                    {"id": "status", "label": "keep", "value": "keep"},
                ],
            },
            open_fn,
        )
        self.assertEqual(called, [])
        ids = [step.get("id") for step in out.get("next_steps") or []]
        self.assertNotIn("enterable", ids)
        self.assertNotIn("session", ids)
        self.assertEqual(ids, ["status"])
        self.assertEqual(out.get("session_reach"), "FAIL")
        self.assertIs(out.get("enterable"), False)

    def test_ok_path_still_records_enterable(self):
        """The not-ok fix must not clear a successful enterable step."""
        out = self.mod.arm_launch_env_session(
            {
                "ok": True,
                "live": "PASS",
                "what": "env",
                "copy": "PASS env",
                "next_steps": [{"id": "status", "label": "keep", "value": "keep"}],
            },
            lambda: {"ok": True, "session_reach": "READY", "pid": "9"},
        )
        ids = [step.get("id") for step in out.get("next_steps") or []]
        self.assertIn("enterable", ids)
        self.assertIn("status", ids)
        self.assertIs(out.get("enterable"), True)
        self.assertEqual(out.get("session_reach"), "READY")


if __name__ == "__main__":
    unittest.main()
