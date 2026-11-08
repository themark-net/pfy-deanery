#!/usr/bin/env python3
"""Drive the ponytail pack probe with a stub smoke. No network and no model.

A stub that only mentions ponytail must not count as a load assertion.
A stub that prints an OK source line for ponytail must.
The paths-pack count must still pass when the ponytail directory is absent,
and must fail when the claude pack is short. That is the recover pair for
treating a missing pack as a gate.
"""

from __future__ import annotations

import os
import stat
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "eval" / "evq1107" / "ponytail-skills-pack" / "probe.py"


def _stub(path: Path, body: str) -> None:
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class PonytailPackProbeTests(unittest.TestCase):
    def test_loose_mention_is_not_a_load_assertion(self) -> None:
        work = ROOT / "tmp" / "ponytail-skills-pack-stub"
        work.mkdir(parents=True, exist_ok=True)
        stub = work / "verify"
        _stub(
            stub,
            "echo 'note: ponytail not in this smoke'\necho '  OK source adr'\n",
        )
        loose = subprocess.run(
            ["python3", str(PROBE), "--count-verify", str(stub)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False,
        )
        self.assertEqual(loose.returncode, 0, loose.stdout + loose.stderr)
        self.assertIn("asserted=0", loose.stdout.splitlines())

        _stub(stub, "echo '  OK source ponytail'\n")
        exact = subprocess.run(
            ["python3", str(PROBE), "--count-verify", str(stub)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False,
        )
        self.assertEqual(exact.returncode, 0, exact.stdout + exact.stderr)
        self.assertIn("asserted=1", exact.stdout.splitlines())

    def test_missing_pack_does_not_fail_the_paths_count(self) -> None:
        proc = subprocess.run(
            ["python3", str(PROBE), "--s7-fixture"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        lines = proc.stdout.splitlines()
        self.assertIn("s7_missing_passes=1", lines)
        self.assertIn("s7_short_claude_fails=1", lines)


if __name__ == "__main__":
    unittest.main()
