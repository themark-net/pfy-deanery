"""AgentDescent real-HOME snap_dir must see mode, symlink retargets, and unreadable files.

No model and no network. The fingerprint is the guard in examples/agentdescent-trial/harness.py.
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "examples/agentdescent-trial/harness.py"


def load():
    spec = importlib.util.spec_from_file_location("ad_snap_harness", HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def restore_mtime(path: Path, st) -> None:
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns), follow_symlinks=False)


class SnapDirTests(unittest.TestCase):
    def setUp(self):
        self.h = load()
        self.td = tempfile.TemporaryDirectory(prefix="ad-snap-")
        self.addCleanup(self._cleanup)
        self.work = Path(self.td.name) / "watch"
        self.work.mkdir()

    def _cleanup(self):
        root = Path(self.td.name)
        for path in sorted(root.rglob("*"), reverse=True):
            try:
                if path.is_symlink() or path.is_file():
                    path.chmod(0o644)
            except OSError:
                pass
        self.td.cleanup()

    def test_missing_path_is_none(self):
        self.assertIsNone(self.h.snap_dir(self.work / "missing"))

    def test_small_file_bytes_still_show_when_mtime_is_restored(self):
        target = self.work / "note.txt"
        target.write_text("hello", encoding="utf-8")
        before = self.h.snap_dir(self.work)
        st = target.lstat()
        target.write_text("hallo", encoding="utf-8")
        restore_mtime(target, st)
        self.assertNotEqual(before, self.h.snap_dir(self.work))

    def test_chmod_shows_when_mtime_is_restored(self):
        target = self.work / "note.txt"
        target.write_text("hello", encoding="utf-8")
        before = self.h.snap_dir(self.work)
        st = target.lstat()
        target.chmod(0o600)
        restore_mtime(target, st)
        self.assertNotEqual(before, self.h.snap_dir(self.work))

    def test_symlink_retarget_shows_and_outside_bytes_do_not(self):
        outside = Path(self.td.name) / "outside"
        outside.mkdir()
        left = outside / "left-target"
        right = outside / "rite-target"
        left.write_text("aaaa", encoding="utf-8")
        right.write_text("bbbb", encoding="utf-8")
        link = self.work / "alias"
        link.symlink_to(left)
        before = self.h.snap_dir(self.work)
        st = link.lstat()
        link.unlink()
        link.symlink_to(right)
        restore_mtime(link, st)
        retargeted = self.h.snap_dir(self.work)
        self.assertNotEqual(before, retargeted)
        right.write_text("cccc", encoding="utf-8")
        self.assertEqual(retargeted, self.h.snap_dir(self.work))

    def test_symlinked_root_retarget_shows(self):
        first = self.work / "tree-a"
        second = self.work / "tree-b"
        first.mkdir()
        second.mkdir()
        (first / "a.txt").write_text("same", encoding="utf-8")
        (second / "a.txt").write_text("same", encoding="utf-8")
        link = self.work / "root-link"
        link.symlink_to(first, target_is_directory=True)
        before = self.h.snap_dir(link)
        st = link.lstat()
        link.unlink()
        link.symlink_to(second, target_is_directory=True)
        restore_mtime(link, st)
        self.assertNotEqual(before, self.h.snap_dir(link))

    def test_unreadable_file_is_recorded_and_does_not_raise(self):
        st = self.work.lstat()
        hidden = self.work / "secret"
        hidden.write_text("x", encoding="utf-8")
        hidden.chmod(0)
        restore_mtime(self.work, st)
        try:
            snapped = self.h.snap_dir(self.work)
        finally:
            hidden.chmod(0o644)
        self.assertIsNotNone(snapped)
        self.assertIn("secret", snapped)

    def test_large_file_mtime_still_shows_without_reading_a_body_hash(self):
        target = self.work / "blob"
        target.write_bytes(b"x" * (self.h.HASH_MAX + 1))
        before = self.h.snap_dir(self.work)
        st = target.lstat()
        os.utime(target, ns=(st.st_atime_ns, st.st_mtime_ns + 1000))
        after = self.h.snap_dir(self.work)
        self.assertNotEqual(before, after)
        self.assertNotIn("sha:", after["blob"])
