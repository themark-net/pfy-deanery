"""A symlink retarget must change smoke_122_124.tree_sig without following.

Two in-tree files hold the same bytes. Pointing the symlink at the other
file must change the signature. A content edit of that in-tree file must
still change the signature, because the file is its own entry. Editing an
outside target must not, and an mtime-only touch of the symlink must not.
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
    spec = importlib.util.spec_from_file_location("tree_sig_symlink_122", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.path.insert(0, str(local))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(local))
    return module.tree_sig


class TreeSigSymlinkTests(unittest.TestCase):
    def test_retarget_changes_signature_and_outside_target_is_not_followed(self) -> None:
        tree_sig = _tree_sig()
        scratch = ROOT / "tmp" / "selfhost-1031-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="tree-sig-link-", dir=scratch) as td:
            root = Path(td)
            a = root / "a.txt"
            b = root / "b.txt"
            link = root / "link"
            a.write_text("hello", encoding="utf-8")
            b.write_text("hello", encoding="utf-8")
            os.chmod(a, 0o644)
            os.chmod(b, 0o644)
            os.symlink("a.txt", link)
            before = tree_sig(root)
            self.assertIsNotNone(before)
            link.unlink()
            os.symlink("b.txt", link)
            self.assertNotEqual(
                tree_sig(root),
                before,
                "retarget to identical bytes left the signature unchanged",
            )
            link.unlink()
            os.symlink("a.txt", link)
            self.assertEqual(tree_sig(root), before)
            a.write_text("hellp", encoding="utf-8")
            self.assertNotEqual(
                tree_sig(root),
                before,
                "content edit of the in-tree linked file left the signature unchanged",
            )
            a.write_text("hello", encoding="utf-8")
            os.chmod(a, 0o644)
            self.assertEqual(tree_sig(root), before)
            os.chmod(a, 0o600)
            self.assertNotEqual(
                tree_sig(root),
                before,
                "chmod of the in-tree linked file left the signature unchanged",
            )
            os.chmod(a, 0o644)
            self.assertEqual(tree_sig(root), before)
            outside = root.parent / "outside-target.txt"
            outside.write_text("hello", encoding="utf-8")
            try:
                os.symlink(outside, root / "out")
                mid = tree_sig(root)
                self.assertNotEqual(mid, before)
                outside.write_text("hellp", encoding="utf-8")
                self.assertEqual(
                    tree_sig(root),
                    mid,
                    "editing an outside target changed the signature, so the link was followed",
                )
                outside.write_text("hello", encoding="utf-8")
                self.assertEqual(tree_sig(root), mid)
                os.utime(link, (2_100_000_000, 2_100_000_000), follow_symlinks=False)
                self.assertEqual(
                    tree_sig(root),
                    mid,
                    "mtime-only touch of the symlink changed the signature",
                )
            finally:
                outside.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
