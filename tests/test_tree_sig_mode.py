"""chmod must change smoke_122_124.tree_sig. An mtime-only touch must not.

The parked tester note says permission-only changes are a blind spot. A
same-size content edit must still change the signature, and touching mtime
must not, so the fix cannot swap the content hash for an mtime hash.
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
    spec = importlib.util.spec_from_file_location("tree_sig_mode_122", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.path.insert(0, str(local))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(local))
    return module.tree_sig


class TreeSigModeTests(unittest.TestCase):
    def test_chmod_changes_signature_mtime_and_restored_content_do_not(self) -> None:
        tree_sig = _tree_sig()
        scratch = ROOT / "tmp" / "selfhost-1031-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="tree-sig-mode-", dir=scratch) as td:
            root = Path(td)
            note = root / "note.txt"
            note.write_text("hello", encoding="utf-8")
            os.chmod(note, 0o644)
            before = tree_sig(root)
            note.write_text("hellp", encoding="utf-8")
            self.assertNotEqual(tree_sig(root), before)
            note.write_text("hello", encoding="utf-8")
            os.chmod(note, 0o644)
            self.assertEqual(tree_sig(root), before)
            os.utime(note, (2_100_000_000, 2_100_000_000))
            self.assertEqual(tree_sig(root), before, "mtime-only touch changed the signature")
            os.chmod(note, 0o600)
            self.assertNotEqual(tree_sig(root), before, "chmod left the signature unchanged")
            os.chmod(note, 0o644)
            self.assertEqual(tree_sig(root), before)


if __name__ == "__main__":
    unittest.main()
