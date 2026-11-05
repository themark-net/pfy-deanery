"""home_sig stays stricter than tree_sig on mtime, and the docstring says so.

An mtime-only touch changes home_sig and does not change tree_sig. The
home_sig docstring must not claim tree_sig was left as is.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    local = ROOT / "examples" / "x-intake-local"
    sys.path.insert(0, str(local))
    try:
        spec122 = importlib.util.spec_from_file_location("home_doc_122", local / "smoke_122_124.py")
        m122 = importlib.util.module_from_spec(spec122)
        assert spec122 is not None and spec122.loader is not None
        spec122.loader.exec_module(m122)
        spec128 = importlib.util.spec_from_file_location("home_doc_128", local / "smoke_128_130.py")
        m128 = importlib.util.module_from_spec(spec128)
        assert spec128 is not None and spec128.loader is not None
        spec128.loader.exec_module(m128)
    finally:
        sys.path.remove(str(local))
    return m128.home_sig, m122.tree_sig


class HomeSigDocTests(unittest.TestCase):
    def test_doc_does_not_say_tree_sig_was_left_as_is_and_mtime_stays_stricter(self) -> None:
        home_sig, tree_sig = _load()
        doc = home_sig.__doc__ or ""
        self.assertNotIn("left as is", doc)
        self.assertIn("mtime", doc)
        scratch = ROOT / "tmp" / "selfhost-1031-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="home-sig-doc-", dir=scratch) as td:
            root = Path(td)
            note = root / "note.txt"
            note.write_text("hello", encoding="utf-8")
            os.chmod(note, 0o644)
            tree_before = tree_sig(root)
            home_before = home_sig(root)
            self.assertIsNotNone(tree_before)
            self.assertIsNotNone(home_before)
            os.utime(note, (2_100_000_000, 2_100_000_000))
            self.assertEqual(tree_sig(root), tree_before, "mtime-only touch changed tree_sig")
            self.assertNotEqual(home_sig(root), home_before, "mtime-only touch left home_sig unchanged")


if __name__ == "__main__":
    unittest.main()
