"""Behavior of the three mtime-based tree_sig copies named in the 2026-10-16 handoff.

How this fails: a signature that uses size and mtime, ignores mode, or follows a
symlink treats a same-size content edit, a chmod, or a retarget as unchanged.
How we recover: hash streamed file bytes, lstat mode, and the symlink text,
and do not follow links. The same checks run against each copy.
"""
from __future__ import annotations

import importlib
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XDIR = ROOT / "examples" / "x-intake-local"
if str(XDIR) not in sys.path:
    sys.path.insert(0, str(XDIR))

MODULES = ("smoke_119_121", "smoke_112_114", "smoke_115_116")


def _load(name: str):
    return importlib.import_module(name)


class TreeSigCopiesTests(unittest.TestCase):
    def _sigs(self, path: Path) -> list:
        return [_load(name).tree_sig(path) for name in MODULES]

    def test_missing_path_is_none(self) -> None:
        missing = Path("/no/such/pfy-tree-sig-copies")
        for sig in self._sigs(missing):
            self.assertIsNone(sig)

    def test_same_size_content_edit_changes_sig(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-tsig-") as raw:
            root = Path(raw)
            target = root / "f"
            target.write_bytes(b"aaaa")
            before = self._sigs(root)
            os.utime(target, (1_700_000_000, 1_700_000_000))
            stamped = self._sigs(root)
            target.write_bytes(b"bbbb")
            os.utime(target, (1_700_000_000, 1_700_000_000))
            after = self._sigs(root)
            for left, mid, right in zip(before, stamped, after):
                self.assertEqual(left, mid)
                self.assertNotEqual(mid, right)

    def test_chmod_only_changes_sig(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-tsig-") as raw:
            root = Path(raw)
            target = root / "f"
            target.write_bytes(b"same-bytes")
            target.chmod(0o644)
            before = self._sigs(root)
            target.chmod(0o755)
            after = self._sigs(root)
            for left, right in zip(before, after):
                self.assertNotEqual(left, right)

    def test_symlink_retarget_changes_sig_without_following(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-tsig-") as raw:
            parent = Path(raw)
            root = parent / "tree"
            root.mkdir()
            outside = parent / "outside"
            outside.mkdir()
            payload = outside / "secret"
            payload.write_bytes(b"secret-bytes")
            other = outside / "other"
            other.write_bytes(b"secret-bytes")
            os.utime(payload, (1_700_000_000, 1_700_000_000))
            os.utime(other, (1_700_000_000, 1_700_000_000))
            link = root / "link"
            link.symlink_to(payload)
            before = self._sigs(root)
            payload.write_bytes(b"secret-bytes-edited")
            edited = self._sigs(root)
            payload.write_bytes(b"secret-bytes")
            os.utime(payload, (1_700_000_000, 1_700_000_000))
            link.unlink()
            link.symlink_to(other)
            retargeted = self._sigs(root)
            for left, mid, right in zip(before, edited, retargeted):
                self.assertEqual(left, mid)
                self.assertNotEqual(left, right)

    def test_unreadable_file_is_not_dropped(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pfy-tsig-") as raw:
            root = Path(raw)
            empty = self._sigs(root)
            hidden = root / "hidden"
            hidden.write_bytes(b"cannot-read")
            hidden.chmod(0)
            try:
                marked = self._sigs(root)
            finally:
                hidden.chmod(stat.S_IRUSR | stat.S_IWUSR)
            for left, right in zip(empty, marked):
                self.assertNotEqual(left, right)


if __name__ == "__main__":
    unittest.main()
