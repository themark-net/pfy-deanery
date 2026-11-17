"""An unreadable directory must change a tree signature, not be skipped.

Fail: os.walk / walk_nofollow drops a directory it cannot list, so
tree_digest (and tree_sig) of a tree with a locked dir that holds a file
matches the same tree without that dir.
Recover: onerror records the unlistable path into the digest / signature.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "scripts" / "pfy_build_local.py"
WALK = ROOT / "examples" / "x-intake-local"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load %s" % path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


LOCAL_MOD = _load(LOCAL, "pfy_build_local_walk_onerror")


def _locked_tree(root: Path) -> Path:
    (root / "visible.txt").write_text("ok\n", encoding="utf-8")
    locked = root / "locked"
    locked.mkdir()
    (locked / "secret.txt").write_text("hidden\n", encoding="utf-8")
    locked.chmod(0)
    return locked


def _can_list(path: Path) -> bool:
    try:
        os.listdir(path)
        return True
    except OSError:
        return False


class WalkOnerrorSignature(unittest.TestCase):
    def test_tree_digest_changes_when_a_subdir_is_unreadable(self):
        with tempfile.TemporaryDirectory(prefix="pfy-walk-digest-") as raw:
            root = Path(raw) / "tree"
            root.mkdir()
            locked = _locked_tree(root)
            try:
                if _can_list(locked):
                    self.skipTest("this user can still list a chmod 000 directory")
                locked_digest = LOCAL_MOD.tree_digest(root)
            finally:
                locked.chmod(0o700)
            visible_only = Path(raw) / "visible-only"
            visible_only.mkdir()
            (visible_only / "visible.txt").write_text("ok\n", encoding="utf-8")
            self.assertNotEqual(locked_digest, LOCAL_MOD.tree_digest(visible_only))
            self.assertNotEqual(locked_digest, LOCAL_MOD.tree_digest(root))

    def test_tree_sig_includes_walk_errors(self):
        sys.path.insert(0, str(WALK))
        try:
            from smoke_119_121 import tree_sig
            from xintake_walk import record_walk_errors, walk_nofollow
        finally:
            if str(WALK) in sys.path:
                sys.path.remove(str(WALK))
        with tempfile.TemporaryDirectory(prefix="pfy-walk-sig-") as raw:
            root = Path(raw) / "tree"
            root.mkdir()
            locked = _locked_tree(root)
            try:
                if _can_list(locked):
                    self.skipTest("this user can still list a chmod 000 directory")
                errors: list[OSError] = []
                walk_nofollow(root, errors=errors)
                self.assertTrue(errors)
                folded = hashlib.sha256(b"probe")
                record_walk_errors(folded, errors)
                self.assertNotEqual(folded.hexdigest(), hashlib.sha256(b"probe").hexdigest())
                locked_sig = tree_sig(root)
            finally:
                locked.chmod(0o700)
            visible_only = Path(raw) / "visible-only"
            visible_only.mkdir()
            (visible_only / "visible.txt").write_text("ok\n", encoding="utf-8")
            self.assertIsNotNone(locked_sig)
            self.assertNotEqual(locked_sig, tree_sig(visible_only))


if __name__ == "__main__":
    unittest.main()
