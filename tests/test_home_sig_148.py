"""smoke_148.home_sig must see bytes, mode, and symlink retargets.

An mtime-only touch must still change the signature. A same-size edit that
restores mtime must too. A chmod and a symlink retarget must, and an outside
target must not be followed. A missing watched path stays None. An unreadable
file must not raise.
"""
from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _home_sig():
    path = ROOT / "examples" / "x-intake-local" / "smoke_148.py"
    spec = importlib.util.spec_from_file_location("home_sig_148", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.home_sig


class HomeSig148Tests(unittest.TestCase):
    def test_content_mode_and_symlink_keep_mtime(self) -> None:
        home_sig = _home_sig()
        scratch = ROOT / "tmp" / "selfhost-1031-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="home-sig-148-", dir=scratch) as td:
            home = Path(td)
            self.assertIsNone(home_sig(home)[".skillspector"])
            note = home / ".skillspector" / "note.txt"
            note.parent.mkdir()
            note.write_text("hello", encoding="utf-8")
            os.chmod(note, 0o644)
            before = home_sig(home)
            self.assertIsNotNone(before[".skillspector"])
            stamp = note.stat().st_mtime_ns
            os.utime(note, ns=(stamp + 10**9, stamp + 10**9))
            self.assertNotEqual(home_sig(home), before, "mtime-only touch left the signature unchanged")
            note.write_text("hello", encoding="utf-8")
            os.utime(note, ns=(stamp, stamp))
            self.assertEqual(home_sig(home), before)
            note.write_text("hellp", encoding="utf-8")
            os.utime(note, ns=(stamp, stamp))
            self.assertNotEqual(home_sig(home), before, "same-size edit with restored mtime was invisible")
            note.write_text("hello", encoding="utf-8")
            os.chmod(note, 0o644)
            os.utime(note, ns=(stamp, stamp))
            self.assertEqual(home_sig(home), before)
            os.chmod(note, 0o600)
            self.assertNotEqual(home_sig(home), before, "chmod left the signature unchanged")
            os.chmod(note, 0o644)
            os.utime(note, ns=(stamp, stamp))
            self.assertEqual(home_sig(home), before)
            other = home / ".skillspector" / "other.txt"
            other.write_text("hello", encoding="utf-8")
            os.chmod(other, 0o644)
            os.utime(other, ns=(stamp, stamp))
            link = home / ".skillspector" / "link"
            os.symlink("note.txt", link)
            linked = home_sig(home)
            link.unlink()
            os.symlink("other.txt", link)
            self.assertNotEqual(home_sig(home), linked, "retarget to identical bytes left the signature unchanged")
            link.unlink()
            os.symlink("note.txt", link)
            self.assertEqual(home_sig(home), linked)
            outside = scratch / "outside-148.txt"
            outside.write_text("hello", encoding="utf-8")
            try:
                os.symlink(outside, home / ".skillspector" / "out")
                mid = home_sig(home)
                outside.write_text("hellp", encoding="utf-8")
                self.assertEqual(
                    home_sig(home), mid,
                    "editing an outside target changed the signature, so the link was followed",
                )
            finally:
                outside.unlink(missing_ok=True)
            blocked = home / ".skillspector" / "blocked.txt"
            blocked.write_text("secret", encoding="utf-8")
            blocked.chmod(0)
            try:
                signed = home_sig(home)
                self.assertIsNotNone(signed[".skillspector"])
                blocked.chmod(0o644)
                self.assertNotEqual(home_sig(home), signed, "restoring a readable mode left the signature unchanged")
            finally:
                blocked.chmod(0o644)


if __name__ == "__main__":
    unittest.main()
