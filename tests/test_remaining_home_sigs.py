"""Remaining real-HOME signatures still hash size and mtime.

How this fails: smoke_117_118.tree_sig and the home_sig helpers in smoke_148
and smoke_149 ignore a same-size content edit and a chmod, and they follow a
symlink, so an edit outside the watched tree changes the signature.
How we recover: hash streamed bytes, lstat mode, and symlink text, and do not
follow links. mtime is not part of the signature. home_sig keeps one value per
watched path.
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

STAMP = (1_700_000_000, 1_700_000_000)


def _mod(name: str):
    return importlib.import_module(name)


class RemainingHomeSigTests(unittest.TestCase):
    def test_tree_sig_content_chmod_and_link(self) -> None:
        sig = _mod("smoke_117_118").tree_sig
        self.assertIsNone(sig(Path("/no/such/pfy-remaining-home-sig")))
        with tempfile.TemporaryDirectory(prefix="pfy-hsig-") as raw:
            root = Path(raw) / "tree"
            root.mkdir()
            target = root / "f"
            target.write_bytes(b"aaaa")
            before = sig(root)
            os.utime(target, STAMP)
            self.assertEqual(sig(root), before)
            target.write_bytes(b"bbbb")
            os.utime(target, STAMP)
            self.assertNotEqual(sig(root), before)
            target.chmod(0o644)
            chmod_before = sig(root)
            target.chmod(0o755)
            self.assertNotEqual(sig(root), chmod_before)

            outside = Path(raw) / "outside"
            outside.mkdir()
            payload = outside / "secret"
            other = outside / "other"
            payload.write_bytes(b"secret-bytes")
            other.write_bytes(b"secret-bytes")
            os.utime(payload, STAMP)
            os.utime(other, STAMP)
            link = root / "link"
            link.symlink_to(payload)
            linked = sig(root)
            payload.write_bytes(b"secret-bytes-edited")
            self.assertEqual(sig(root), linked)
            payload.write_bytes(b"secret-bytes")
            os.utime(payload, STAMP)
            link.unlink()
            link.symlink_to(other)
            self.assertNotEqual(sig(root), linked)

            empty = Path(raw) / "empty"
            empty.mkdir()
            hidden_root = Path(raw) / "hidden-root"
            hidden_root.mkdir()
            hidden = hidden_root / "hidden"
            hidden.write_bytes(b"cannot-read")
            hidden.chmod(0)
            try:
                self.assertNotEqual(sig(hidden_root), sig(empty))
            finally:
                hidden.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def test_home_sig_ignores_mtime_and_sees_content_mode_and_links(self) -> None:
        cases = (
            ("smoke_148", ".skillspector"),
            ("smoke_149", ".mempalace"),
        )
        for mod_name, watched in cases:
            home_sig = _mod(mod_name).home_sig
            with tempfile.TemporaryDirectory(prefix="pfy-hsig-") as raw:
                home = Path(raw) / "home"
                watched_dir = home / watched
                watched_dir.mkdir(parents=True)
                missing = home_sig(home / "nope")
                self.assertIsNone(missing[watched])
                target = watched_dir / "f"
                target.write_bytes(b"aaaa")
                before = home_sig(home)
                os.utime(target, STAMP)
                self.assertEqual(home_sig(home), before, mod_name)
                target.write_bytes(b"bbbb")
                os.utime(target, STAMP)
                self.assertNotEqual(home_sig(home), before, mod_name)
                target.chmod(0o644)
                chmod_before = home_sig(home)
                target.chmod(0o755)
                self.assertNotEqual(home_sig(home), chmod_before, mod_name)

                outside = Path(raw) / "outside"
                outside.mkdir()
                payload = outside / "secret"
                other = outside / "other"
                payload.write_bytes(b"secret-bytes")
                other.write_bytes(b"secret-bytes")
                os.utime(payload, STAMP)
                os.utime(other, STAMP)
                link = watched_dir / "link"
                link.symlink_to(payload)
                linked = home_sig(home)
                payload.write_bytes(b"secret-bytes-edited")
                self.assertEqual(home_sig(home), linked, mod_name)
                payload.write_bytes(b"secret-bytes")
                os.utime(payload, STAMP)
                link.unlink()
                link.symlink_to(other)
                self.assertNotEqual(home_sig(home), linked, mod_name)


if __name__ == "__main__":
    unittest.main()
