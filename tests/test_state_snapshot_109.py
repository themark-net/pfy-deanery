"""state_snapshot in smoke_109_111 misses writes that keep the same mtime.

How this fails: the value is the newest mtime, so a same-size edit with the
mtime restored, a chmod, and an unreadable file stamped like the directory
all compare equal to the previous snapshot.
How we recover: one value per path, None when missing. The value includes
streamed file bytes, lstat mode, and symlink text, and it does not follow
links. mtime is not part of the value. An unreadable file is not dropped.
"""
from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
XDIR = ROOT / "examples" / "x-intake-local"
if str(XDIR) not in sys.path:
    sys.path.insert(0, str(XDIR))

STAMP = (1_700_000_000, 1_700_000_000)


def _snap(paths):
    return importlib.import_module("smoke_109_111").state_snapshot(paths)


class StateSnapshot109Tests(unittest.TestCase):
    def test_content_chmod_unreadable_and_symlink(self) -> None:
        missing = Path("/no/such/pfy-state-snapshot-109")
        self.assertIsNone(_snap([missing])[str(missing)])
        with tempfile.TemporaryDirectory(prefix="pfy-snap109-") as raw:
            root = Path(raw) / "tree"
            root.mkdir()
            target = root / "f"
            target.write_bytes(b"aaaa")
            os.utime(root, STAMP)
            os.utime(target, STAMP)
            before = _snap([root])[str(root)]

            os.utime(target, (1_800_000_000, 1_800_000_000))
            os.utime(target, STAMP)
            self.assertEqual(_snap([root])[str(root)], before)

            target.write_bytes(b"bbbb")
            os.utime(root, STAMP)
            os.utime(target, STAMP)
            self.assertNotEqual(_snap([root])[str(root)], before)

            target.chmod(0o644)
            chmod_before = _snap([root])[str(root)]
            target.chmod(0o755)
            self.assertNotEqual(_snap([root])[str(root)], chmod_before)

            outside = Path(raw) / "outside"
            outside.mkdir()
            payload = outside / "secret"
            payload.write_bytes(b"secret-bytes")
            os.utime(payload, STAMP)
            link = root / "link"
            link.symlink_to(payload)
            os.utime(root, STAMP)
            linked = _snap([root])[str(root)]
            payload.write_bytes(b"secret-bytes-edited")
            os.utime(payload, STAMP)
            self.assertEqual(_snap([root])[str(root)], linked)

            empty = Path(raw) / "empty"
            empty.mkdir()
            os.utime(empty, STAMP)
            hidden_root = Path(raw) / "hidden-root"
            hidden_root.mkdir()
            hidden = hidden_root / "hidden"
            hidden.write_bytes(b"cannot-read")
            hidden.chmod(0)
            os.utime(hidden_root, STAMP)
            try:
                os.utime(hidden, STAMP)
            except OSError:
                pass
            try:
                self.assertNotEqual(
                    _snap([hidden_root])[str(hidden_root)],
                    _snap([empty])[str(empty)],
                )
            finally:
                hidden.chmod(0o644)


if __name__ == "__main__":
    unittest.main()
