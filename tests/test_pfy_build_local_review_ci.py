#!/usr/bin/env python3
"""Review tests must run when bwrap is hidden, the way ubuntu-24.04 CI is.

The G0 job on ubuntu-24.04 runs unittest discover without a working bwrap.
Confinement tests in other modules skip. The review module must not: it uses
the stub opencode and the stub HTTP reviewer, and it has no model.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = ROOT / "tmp" / "review-ci-parity"


def _path_without_bwrap(dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    seen: set[str] = set()
    for entry in os.environ.get("PATH", "").split(":"):
        folder = Path(entry)
        if not folder.is_dir():
            continue
        for item in folder.iterdir():
            if item.name == "bwrap" or item.name in seen:
                continue
            if not item.is_file() or not os.access(item, os.X_OK):
                continue
            seen.add(item.name)
            (dest / item.name).symlink_to(item)


class ReviewCiParityTests(unittest.TestCase):
    def test_review_module_runs_with_bwrap_hidden_and_skips_nothing(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        path_dir = SCRATCH / "nobwrap-path"
        work = SCRATCH / "tmp"
        work.mkdir(parents=True, exist_ok=True)
        self.addCleanup(shutil.rmtree, path_dir, True)
        _path_without_bwrap(path_dir)
        probe = subprocess.run(
            ["python3", "-c", "import shutil; raise SystemExit(0 if shutil.which('bwrap') else 1)"],
            env={**os.environ, "PATH": str(path_dir)},
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertNotEqual(probe.returncode, 0, "bwrap is still on the hidden PATH")
        env = os.environ.copy()
        env["PATH"] = str(path_dir)
        env["TMPDIR"] = str(work)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        for key in ("PFY_LOCAL_BUILD_MODEL", "OLLAMA_HOST"):
            env.pop(key, None)
        proc = subprocess.run(
            ["python3", "-m", "unittest", "tests.test_pfy_build_local_review"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        tail = (proc.stderr or "")[-4000:]
        self.assertEqual(proc.returncode, 0, tail)
        match = re.search(r"^Ran (\d+) tests in ", proc.stderr or "", re.M)
        self.assertIsNotNone(match, tail)
        ran = int(match.group(1))
        self.assertGreaterEqual(ran, 17, tail)
        self.assertNotRegex(proc.stderr or "", r"skipped=\d+")
        self.assertNotIn("bwrap-missing", proc.stderr or "")
        lines = [line.strip() for line in (proc.stderr or "").splitlines() if line.strip()]
        self.assertEqual(lines[-1], "OK", tail)
        (SCRATCH / "result.txt").write_text("ran=%s skipped=0\n" % ran, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
