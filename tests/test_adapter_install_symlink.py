"""install_skill_tree must copy a symlink, not the target bytes.

shutil.copytree follows links. A mode-000 target raises, and a readable
target is copied into the install. After tree_hash stores readlink text,
that copy also fails the hash check. The installed tree must keep the
link, a regular tree must still install cleanly, and a second install of
an unchanged tree must not rewrite.
"""
from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from pfylib.adapters.base import MARKER, MARKER_NAME, install_skill_tree

ROOT = Path(__file__).resolve().parents[1]


class AdapterInstallSymlinkTests(unittest.TestCase):
    def test_symlink_is_copied_and_regular_tree_stays_clean(self) -> None:
        scratch = ROOT / "tmp" / "selfhost2-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="adapter-install-", dir=scratch) as td:
            root = Path(td)
            regular = root / "regular-src"
            (regular / "sub").mkdir(parents=True)
            (regular / "a.txt").write_bytes(b"hello")
            (regular / "sub" / "b.txt").write_bytes(b"world")
            dest = root / "regular-dest"
            wrote, _digest = install_skill_tree(regular, dest)
            self.assertTrue(wrote)
            self.assertEqual((dest / "a.txt").read_bytes(), b"hello")
            self.assertEqual((dest / MARKER_NAME).read_bytes(), MARKER)
            again, _again = install_skill_tree(regular, dest)
            self.assertFalse(again)

            outside = root / "outside"
            outside.mkdir()
            secret = outside / "secret.txt"
            secret.write_bytes(b"secret-bytes")
            secret.chmod(0)
            src = root / "link-src"
            src.mkdir()
            link = src / "a.txt"
            link.symlink_to(secret)
            installed = root / "link-dest"
            try:
                wrote, _digest = install_skill_tree(src, installed)
            finally:
                secret.chmod(stat.S_IRUSR | stat.S_IWUSR)
            self.assertTrue(wrote)
            got = installed / "a.txt"
            self.assertTrue(got.is_symlink(), "install copied the target bytes")
            self.assertEqual(os.readlink(got), os.readlink(link))
            self.assertEqual(secret.read_bytes(), b"secret-bytes")
            secret.write_bytes(b"edited-outside")
            again, _again = install_skill_tree(src, installed)
            self.assertFalse(again)
            self.assertTrue(got.is_symlink())
            self.assertEqual(secret.read_bytes(), b"edited-outside")


if __name__ == "__main__":
    unittest.main()
