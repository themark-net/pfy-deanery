"""remove_created_file and restore_file must not follow a symlink.

Both treat a symlink as a normal file. file_sha then reads the target, and
a matching hash can unlink the link or write through it. A symlink must
return warn, including a mode-000 target and a missing target, and the
target bytes must stay. A regular file with a matching hash still removes
or restores.
"""
from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import unittest
from pathlib import Path

from pfylib.adapters.base import remove_created_file, restore_file

ROOT = Path(__file__).resolve().parents[1]


class AdapterSymlinkFileOpsTests(unittest.TestCase):
    def test_symlink_is_left_and_regular_file_still_updates(self) -> None:
        scratch = ROOT / "tmp" / "selfhost2-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="adapter-ops-", dir=scratch) as td:
            root = Path(td)
            body = b"plain config\n"
            live = root / "live.toml"
            live.write_bytes(body)
            sha = hashlib.sha256(body).hexdigest()
            self.assertEqual(remove_created_file(live, sha, "item", "toml"), "removed")
            self.assertFalse(live.exists())

            live.write_bytes(body)
            backup = root / "live.toml.pfy.backup"
            backup.write_bytes(b"backup config\n")
            self.assertEqual(restore_file(live, str(backup), sha), "restored")
            self.assertEqual(live.read_bytes(), b"backup config\n")
            self.assertFalse(backup.exists())

            outside = root / "outside.toml"
            outside.write_bytes(body)
            outside.chmod(0)
            link = root / "link.toml"
            link.symlink_to(outside)
            try:
                self.assertEqual(remove_created_file(link, sha, "item", "toml"), "warn")
                self.assertTrue(link.is_symlink())
                self.assertEqual(os.readlink(link), str(outside))
            finally:
                outside.chmod(stat.S_IRUSR | stat.S_IWUSR)
            self.assertEqual(outside.read_bytes(), body)

            backup.write_bytes(b"backup config\n")
            self.assertEqual(restore_file(link, str(backup), sha), "warn")
            self.assertTrue(link.is_symlink())
            self.assertEqual(outside.read_bytes(), body)
            self.assertTrue(backup.is_file())

            broken = root / "broken.toml"
            broken.symlink_to(root / "missing.toml")
            self.assertEqual(remove_created_file(broken, sha, "item", "toml"), "warn")
            self.assertTrue(broken.is_symlink())


if __name__ == "__main__":
    unittest.main()
