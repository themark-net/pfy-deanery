"""smoke_140_142.tree_hash must not follow a symlink out of the fixture tree.

fixtures_untouched uses this hash. is_file() follows links, so a mode-000
target raises and an outside edit looks like a fixture change. A symlink
must contribute its readlink text. A regular-file tree must keep today's
digest. smoke_143_145 imports this function, so the row framing stays.
"""
from __future__ import annotations

import hashlib
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tree_hash():
    sys.path.insert(0, str(ROOT / "examples" / "x-intake-local"))
    import smoke_140_142 as module
    return module.tree_hash


def _digest(root: Path) -> str:
    rows = []
    for path in root.rglob("*"):
        if path.is_symlink():
            rows.append((path, os.readlink(path).encode()))
        elif path.is_file():
            rows.append((path, path.read_bytes()))
    h = hashlib.sha256()
    for path, data in sorted(rows, key=lambda item: item[0]):
        h.update(str(path.relative_to(root)).encode() + b"\0" + data + b"\0")
    return h.hexdigest()


class Smoke140TreeHashSymlinkTests(unittest.TestCase):
    def test_regular_digest_stays_and_symlink_does_not_follow(self) -> None:
        tree_hash = _tree_hash()
        scratch = ROOT / "tmp" / "selfhost2-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="hash140-", dir=scratch) as td:
            root = Path(td)
            regular = root / "regular"
            (regular / "sub").mkdir(parents=True)
            (regular / "a.txt").write_bytes(b"hello")
            (regular / "sub" / "b.txt").write_bytes(b"world")
            self.assertEqual(tree_hash(regular), _digest(regular))

            outside = root / "outside"
            outside.mkdir()
            secret = outside / "secret"
            secret.write_bytes(b"secret-bytes")
            secret.chmod(0)
            other = outside / "rite-secret"
            other.write_bytes(b"other-bytes")
            linked = root / "linked"
            linked.mkdir()
            link = linked / "a.txt"
            link.symlink_to(secret)
            try:
                first = tree_hash(linked)
            finally:
                secret.chmod(stat.S_IRUSR | stat.S_IWUSR)
            self.assertEqual(first, _digest(linked))
            self.assertNotEqual(first, hashlib.sha256(
                b"a.txt\0secret-bytes\0"
            ).hexdigest())
            secret.write_bytes(b"edited-outside")
            self.assertEqual(tree_hash(linked), first)
            link.unlink()
            link.symlink_to(other)
            retargeted = tree_hash(linked)
            self.assertNotEqual(retargeted, first)
            self.assertEqual(retargeted, _digest(linked))
            (linked / "gone.txt").symlink_to(outside / "missing")
            self.assertEqual(tree_hash(linked), _digest(linked))


if __name__ == "__main__":
    unittest.main()
