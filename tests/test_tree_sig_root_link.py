"""A symlinked root must change smoke_122_124.tree_sig on retarget.

Two directories hold the same bytes. Pointing the path itself at the other
directory must change the signature. A content edit under that directory
must still change the signature. An mtime-only touch of the symlink must
not. A missing path still returns None.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tree_sig():
    local = ROOT / "examples" / "x-intake-local"
    path = local / "smoke_122_124.py"
    spec = importlib.util.spec_from_file_location("tree_sig_root_link_122", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.path.insert(0, str(local))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(local))
    return module.tree_sig


class TreeSigRootLinkTests(unittest.TestCase):
    def test_symlinked_root_retarget_changes_signature_and_entries_remain(self) -> None:
        tree_sig = _tree_sig()
        scratch = ROOT / "tmp" / "selfhost-1031-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="tree-sig-root-", dir=scratch) as td:
            base = Path(td)
            a = base / "A"
            b = base / "B"
            a.mkdir()
            b.mkdir()
            note_a = a / "note.txt"
            note_b = b / "note.txt"
            note_a.write_text("hello", encoding="utf-8")
            note_b.write_text("hello", encoding="utf-8")
            link = base / "L"
            os.symlink(a, link)
            before = tree_sig(link)
            self.assertIsNotNone(before)
            link.unlink()
            os.symlink(b, link)
            self.assertNotEqual(
                tree_sig(link),
                before,
                "retarget of a symlinked root to identical bytes left the signature unchanged",
            )
            link.unlink()
            os.symlink(a, link)
            self.assertEqual(tree_sig(link), before)
            note_a.write_text("hellp", encoding="utf-8")
            self.assertNotEqual(
                tree_sig(link),
                before,
                "content edit under the symlinked root left the signature unchanged",
            )
            note_a.write_text("hello", encoding="utf-8")
            self.assertEqual(tree_sig(link), before)
            os.utime(link, (2_100_000_000, 2_100_000_000), follow_symlinks=False)
            self.assertEqual(tree_sig(link), before, "mtime-only touch of the symlinked root changed the signature")
            self.assertIsNone(tree_sig(base / "missing"))


if __name__ == "__main__":
    unittest.main()
