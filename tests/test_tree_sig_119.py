"""smoke_119_121.tree_sig must see bytes, mode, and symlink retargets.

An mtime-only touch must not change the signature. A same-size edit that
restores mtime must. A chmod and a symlink retarget must, and an outside
target must not be followed. A missing path returns None.
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
    path = local / "smoke_119_121.py"
    spec = importlib.util.spec_from_file_location("tree_sig_119_port", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.path.insert(0, str(local))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(local))
    return module.tree_sig


class TreeSig119Tests(unittest.TestCase):
    def test_content_mode_and_symlink_not_mtime(self) -> None:
        tree_sig = _tree_sig()
        self.assertIsNone(tree_sig(Path("/this/path/is/not/on/disk/mvp2-t2")))
        scratch = ROOT / "tmp" / "selfhost-1031-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="tree-sig-119-", dir=scratch) as td:
            root = Path(td)
            note = root / "note.txt"
            note.write_text("hello", encoding="utf-8")
            os.chmod(note, 0o644)
            before = tree_sig(root)
            self.assertIsNotNone(before)
            stamp = note.stat().st_mtime_ns
            os.utime(note, ns=(stamp + 10**9, stamp + 10**9))
            self.assertEqual(tree_sig(root), before, "mtime-only touch changed the signature")
            note.write_text("hellp", encoding="utf-8")
            os.utime(note, ns=(stamp, stamp))
            self.assertNotEqual(tree_sig(root), before, "same-size edit with restored mtime was invisible")
            note.write_text("hello", encoding="utf-8")
            os.chmod(note, 0o644)
            os.utime(note, ns=(stamp, stamp))
            self.assertEqual(tree_sig(root), before)
            os.chmod(note, 0o600)
            self.assertNotEqual(tree_sig(root), before, "chmod left the signature unchanged")
            os.chmod(note, 0o644)
            self.assertEqual(tree_sig(root), before)
            other = root / "other.txt"
            other.write_text("hello", encoding="utf-8")
            os.chmod(other, 0o644)
            link = root / "link"
            os.symlink("note.txt", link)
            linked = tree_sig(root)
            link.unlink()
            os.symlink("other.txt", link)
            self.assertNotEqual(
                tree_sig(root),
                linked,
                "retarget to identical bytes left the signature unchanged",
            )
            link.unlink()
            os.symlink("note.txt", link)
            self.assertEqual(tree_sig(root), linked)
            note.write_text("hellp", encoding="utf-8")
            self.assertNotEqual(
                tree_sig(root),
                linked,
                "content edit of the in-tree linked file left the signature unchanged",
            )
            note.write_text("hello", encoding="utf-8")
            os.chmod(note, 0o644)
            os.utime(note, ns=(stamp, stamp))
            self.assertEqual(tree_sig(root), linked)
            outside = scratch / "outside-119.txt"
            outside.write_text("hello", encoding="utf-8")
            try:
                os.symlink(outside, root / "out")
                mid = tree_sig(root)
                outside.write_text("hellp", encoding="utf-8")
                self.assertEqual(
                    tree_sig(root),
                    mid,
                    "editing an outside target changed the signature, so the link was followed",
                )
            finally:
                outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
