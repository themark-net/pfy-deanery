#!/usr/bin/env python3
"""tool_cache.sh creates the three cache dirs and refuses a non-directory.

How this fails: a file sits where bin, tools, or uv-cache must be a
directory, and a later install writes through it. Or check creates nothing
and the next lookup misses a path that should exist.
Recovery: check creates missing directories, prints that the known binaries
are absent, and exits 1 when a path exists and is not a directory.
A bad argument exits 2. This test uses PFY_TOOL_CACHE, not the real home.
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "tool_cache.sh"


class ToolCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pfy-tools-"))
        self.cache = self.tmp / "cache"
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.tmp / "home")
        self.env["PFY_TOOL_CACHE"] = str(self.cache)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_check_creates_dirs_and_rejects_a_file(self) -> None:
        created = subprocess.run(
            [str(SCRIPT), "check"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        blob = created.stdout + created.stderr
        self.assertEqual(created.returncode, 0, blob)
        for name in ("bin", "tools", "uv-cache"):
            self.assertTrue((self.cache / name).is_dir(), name)
            self.assertIn(f"ok {self.cache / name}", created.stdout)
        self.assertIn("bin skillspector absent", created.stdout)
        self.assertIn("bin codebase-memory-mcp absent", created.stdout)
        self.assertIn("venv skillspector absent", created.stdout)

        stub = self.cache / "bin" / "skillspector"
        stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
        (self.cache / "tools" / "skillspector").mkdir()
        present = subprocess.run(
            [str(SCRIPT)],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(present.returncode, 0, present.stderr)
        self.assertIn("bin skillspector executable", present.stdout)
        self.assertIn("venv skillspector present", present.stdout)

        uv = self.cache / "uv-cache"
        shutil.rmtree(uv)
        uv.write_text("not a directory", encoding="utf-8")
        blocked = subprocess.run(
            [str(SCRIPT), "check"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(blocked.returncode, 1, blocked.stdout + blocked.stderr)
        self.assertIn("not a directory", blocked.stderr)
        self.assertTrue(uv.is_file())

        usage = subprocess.run(
            [str(SCRIPT), "nope"],
            env=self.env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(usage.returncode, 2, usage.stderr)
        self.assertIn("usage:", usage.stderr)


if __name__ == "__main__":
    unittest.main()
