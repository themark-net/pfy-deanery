"""PFY_TMP defaults must not land on host /tmp/pfy (tmp-cleanup leak; pfy-deanery #9)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from pfylib.paths import pfy_tmp


class PfyTmpDefaultTests(unittest.TestCase):
    def test_explicit_pfy_tmp_wins(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = {"PFY_TMP": td, "XDG_CACHE_HOME": "/tmp/should-not-win", "HOME": "/tmp/should-not-win-home"}
            with mock.patch.dict(os.environ, env, clear=False):
                for key in ("XDG_CACHE_HOME",):
                    pass
                self.assertEqual(pfy_tmp(), Path(td))

    def test_xdg_cache_home_is_used_when_unset(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env = {"XDG_CACHE_HOME": td, "HOME": "/tmp/should-not-win-home"}
            with mock.patch.dict(os.environ, env, clear=False):
                os.environ.pop("PFY_TMP", None)
                self.assertEqual(pfy_tmp(), Path(td) / "pfy" / "tmp")

    def test_default_is_under_home_cache_not_tmp_pfy(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            home.mkdir()
            env = {"HOME": str(home)}
            with mock.patch.dict(os.environ, env, clear=False):
                os.environ.pop("PFY_TMP", None)
                os.environ.pop("XDG_CACHE_HOME", None)
                got = pfy_tmp()
                self.assertEqual(got, home / ".cache" / "pfy" / "tmp")
                self.assertNotEqual(got, Path("/tmp/pfy"))

    def test_committed_sources_do_not_default_pfy_tmp_to_tmp_pfy(self) -> None:
        root = Path(__file__).resolve().parents[1]
        skip = {".git", "tmp", ".venv", "node_modules", "__pycache__"}
        bad: list[str] = []
        needles = (
            'get("PFY_TMP", "/tmp/pfy")',
            "get('PFY_TMP', '/tmp/pfy')",
            'PFY_TMP:=${TMPDIR:-/tmp}/pfy',
            'PFY_TMP:=${TMPDIR:-/tmp}/pfy"',
        )
        for path in root.rglob("*"):
            if not path.is_file() or any(part in skip for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if any(n in text for n in needles):
                bad.append(str(path.relative_to(root)))
        self.assertEqual(bad, [], "PFY_TMP must not default to /tmp/pfy")


if __name__ == "__main__":
    unittest.main()
