"""PFY_TMP defaults to this checkout's tmp/, never a host /tmp path (pfy-deanery #9)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pfylib.paths import pfy_tmp, pfy_root


class PfyTmpDefaultTests(unittest.TestCase):
    def test_explicit_pfy_tmp_wins(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = {"PFY_TMP": td, "PFY_ROOT": "/should-not-win", "XDG_CACHE_HOME": "/tmp/should-not-win"}
            with mock.patch.dict(os.environ, env, clear=False):
                self.assertEqual(pfy_tmp(), Path(td))

    def test_pfy_root_tmp_is_used_when_unset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = {"PFY_ROOT": td, "XDG_CACHE_HOME": "/tmp/should-not-win", "HOME": "/tmp/should-not-win-home"}
            with mock.patch.dict(os.environ, env, clear=False):
                os.environ.pop("PFY_TMP", None)
                self.assertEqual(pfy_tmp(), Path(td) / "tmp")

    def test_default_is_repo_tmp_even_when_xdg_cache_is_under_tmp(self) -> None:
        """CI tmp-cleanup plants XDG_CACHE_HOME under /tmp; mkdir there is a leak."""
        with tempfile.TemporaryDirectory(prefix="pfy-xdg-", dir="/tmp") as td:
            cache = Path(td) / "cache"
            cache.mkdir()
            env = {"XDG_CACHE_HOME": str(cache), "HOME": td}
            with mock.patch.dict(os.environ, env, clear=False):
                os.environ.pop("PFY_TMP", None)
                os.environ.pop("PFY_ROOT", None)
                got = pfy_tmp()
                self.assertEqual(got, pfy_root() / "tmp")
                self.assertNotEqual(got, Path("/tmp") / "pfy")
                host = Path("/tmp").resolve()
                try:
                    got.resolve().relative_to(host)
                    in_tmp = True
                except ValueError:
                    in_tmp = False
                self.assertFalse(in_tmp, f"default {got} must not sit under host /tmp")

    def test_committed_sources_do_not_default_pfy_tmp_to_host_tmp(self) -> None:
        root = Path(__file__).resolve().parents[1]
        skip = {".git", "tmp", ".venv", "node_modules", "__pycache__"}
        here = Path(__file__).resolve()
        bad: list[str] = []
        # Built from parts so this file is not itself a hit.
        needles = (
            "get(" + '"PFY_TMP", "/tmp/' + 'pfy")',
            "get(" + "'PFY_TMP', '/tmp/" + "pfy')",
            "PFY_TMP:=${TMPDIR:-/tmp}/" + "pfy",
            "XDG_CACHE_HOME:-${HOME}/.cache}/pfy/tmp",
        )
        for path in root.rglob("*"):
            if not path.is_file() or any(part in skip for part in path.parts):
                continue
            if path.resolve() == here:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if any(n in text for n in needles):
                bad.append(str(path.relative_to(root)))
        self.assertEqual(bad, [], "PFY_TMP must not default to a host /tmp path")


if __name__ == "__main__":
    unittest.main()
