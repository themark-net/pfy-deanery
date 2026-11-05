"""Each x-intake walk lists a symlink and does not enter a linked directory.

How this fails: a walk follows a directory symlink, so a file that lives
only behind that link shows up, or a symlink entry itself is missing.
How we recover: list the symlink and do not descend into it.
"""
from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "examples" / "x-intake-local"
SITES = (
    "smoke_112_114",
    "smoke_115_116",
    "smoke_117_118",
    "smoke_119_121",
    "smoke_148",
    "smoke_149",
)


class WalkNoFollowTests(unittest.TestCase):
    def test_each_site_lists_symlinks_and_skips_the_linked_file(self) -> None:
        if str(LOCAL) not in sys.path:
            sys.path.insert(0, str(LOCAL))
        with tempfile.TemporaryDirectory(prefix="pfy-walk-nofollow-") as raw:
            base = Path(raw)
            root = base / "tree"
            root.mkdir()
            (root / "file").write_text("a\n", encoding="utf-8")
            (root / "subdir").mkdir()
            (root / "subdir" / "child").write_text("b\n", encoding="utf-8")
            (root / "link_file").symlink_to("file")
            linked = base / "linked"
            linked.mkdir()
            (linked / "hidden.txt").write_text("c\n", encoding="utf-8")
            (root / "link_dir").symlink_to(linked, target_is_directory=True)
            expect = ["file", "link_dir", "link_file", "subdir", "subdir/child"]
            for name in SITES:
                with self.subTest(name):
                    mod = __import__(name)
                    got = sorted(
                        path.relative_to(root).as_posix()
                        for path in mod.walk_nofollow(root)
                    )
                    self.assertEqual(got, expect)
                    self.assertNotIn("link_dir/hidden.txt", got)

    def test_one_shared_helper(self) -> None:
        # One walk, not a copy per smoke: every site gets the same function.
        if str(LOCAL) not in sys.path:
            sys.path.insert(0, str(LOCAL))
        import xintake_walk

        for name in SITES + ("smoke",):
            with self.subTest(name):
                self.assertIs(__import__(name).walk_nofollow, xintake_walk.walk_nofollow)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root reads a mode-000 directory")
    def test_unreadable_subdirectory_is_reported(self) -> None:
        # How this fails: os.walk drops a directory it cannot list, so its
        # files vanish from the walk with no sign. Recover: report it.
        if str(LOCAL) not in sys.path:
            sys.path.insert(0, str(LOCAL))
        import xintake_walk

        with tempfile.TemporaryDirectory(prefix="pfy-walk-unreadable-") as raw:
            root = Path(raw) / "tree"
            locked = root / "locked"
            locked.mkdir(parents=True)
            (locked / "inside.txt").write_text("x\n", encoding="utf-8")
            locked.chmod(0)
            try:
                errors: list[OSError] = []
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    got = xintake_walk.walk_nofollow(root, errors=errors)
            finally:
                locked.chmod(0o700)
            self.assertIn(locked, got)
            self.assertEqual([Path(e.filename) for e in errors], [locked])
            self.assertIn("cannot read %s" % locked, err.getvalue())


if __name__ == "__main__":
    unittest.main()
