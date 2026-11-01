"""Adapter tree hashes must not follow symlinks or read outside the tree.

pfylib.adapters.base.tree_hash and desired_skill_hash treat a symlink as
is_file() and then read the target. A link to a mode-000 file raises, and
an edit outside the tree changes the hash. A symlink must contribute its
readlink text under the same row framing as a regular file, and a regular
tree must keep today's digest (no mode field).
"""
from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import unittest
from pathlib import Path

from pfylib.adapters.base import MARKER, MARKER_NAME, desired_skill_hash, tree_hash

ROOT = Path(__file__).resolve().parents[1]


def _digest(rows: list[tuple[str, bytes]]) -> str:
    h = hashlib.sha256()
    for rel, data in sorted(rows):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(data)
        h.update(b"\0")
    return h.hexdigest()


class AdapterTreeHashSymlinkTests(unittest.TestCase):
    def test_regular_digest_stays_and_symlink_does_not_follow(self) -> None:
        scratch = ROOT / "tmp" / "selfhost2-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="adapter-hash-", dir=scratch) as td:
            root = Path(td)
            regular = root / "regular"
            (regular / "sub").mkdir(parents=True)
            (regular / "a.txt").write_bytes(b"hello")
            (regular / "sub" / "b.txt").write_bytes(b"world")
            expect = _digest([("a.txt", b"hello"), ("sub/b.txt", b"world")])
            self.assertEqual(tree_hash(regular), expect)
            owned = regular / MARKER_NAME
            owned.write_bytes(b"not-the-marker")
            self.assertEqual(
                desired_skill_hash(regular),
                _digest([("a.txt", b"hello"), ("sub/b.txt", b"world"), (MARKER_NAME, MARKER)]),
            )
            owned.unlink()

            outside = root / "outside"
            outside.mkdir()
            secret = outside / "secret"
            secret.write_bytes(b"secret-bytes")
            secret.chmod(0)
            other = outside / "other-secret"
            other.write_bytes(b"other-bytes")
            link_tree = root / "linked"
            link_tree.mkdir()
            link = link_tree / "a.txt"
            link.symlink_to(secret)
            try:
                first = tree_hash(link_tree)
            finally:
                secret.chmod(stat.S_IRUSR | stat.S_IWUSR)
            self.assertEqual(first, _digest([("a.txt", os.readlink(link).encode("utf-8"))]))
            self.assertNotEqual(first, _digest([("a.txt", b"secret-bytes")]))
            secret.write_bytes(b"edited!!")
            self.assertEqual(tree_hash(link_tree), first)
            link.unlink()
            link.symlink_to(other)
            self.assertNotEqual(tree_hash(link_tree), first)
            self.assertEqual(
                desired_skill_hash(link_tree),
                _digest([(MARKER_NAME, MARKER), ("a.txt", os.readlink(link).encode("utf-8"))]),
            )
            missing = link_tree / "gone.txt"
            missing.symlink_to(outside / "no-such-file")
            self.assertEqual(
                tree_hash(link_tree),
                _digest([
                    ("a.txt", os.readlink(link).encode("utf-8")),
                    ("gone.txt", os.readlink(missing).encode("utf-8")),
                ]),
            )


if __name__ == "__main__":
    unittest.main()
