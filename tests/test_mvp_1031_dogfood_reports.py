#!/usr/bin/env python3
"""Behavior checks for the dogfood report checker.

How this fails: a run directory whose receipt status or exit code disagrees
with REPORT.md, or a receipt that contains a secret-like string, makes
check_reports.py exit 1.
How we recover: fix the report row or redact the receipt, then rerun the
checker. The planted mismatch lives only in a temp directory under tmp/.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tests._ops import OPS, require  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
CHECK = OPS / "eval" / "mvp-1031" / "dogfood" / "check_reports.py"
DOGFOOD = OPS / "eval" / "mvp-1031" / "dogfood"
SCRATCH = REPO / "tmp" / "dogfood-check-tests"

REPORT_HEAD = """# Dogfood report fixture

## Runs

| dir | status | exit_code | gate | review | human | wall_s | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
"""


def _report(rows: list[tuple[str, str, str]]) -> str:
    lines = [REPORT_HEAD.rstrip("\n")]
    for name, status, code in rows:
        lines.append(
            "| %s | %s | %s | pass | accept | yes | 1 | ok |" % (name, status, code)
        )
    lines.append("")
    return "\n".join(lines) + "\n"


def _receipt(status: str, exit_code: int, extra: str = "") -> str:
    payload = {
        "schema": "pfy-cloud-build/1",
        "status": status,
        "reason": "ok" if status == "PASS" else status.lower(),
        "exit_code": exit_code,
    }
    text = json.dumps(payload, indent=2) + "\n"
    if extra:
        text += extra
        if not extra.endswith("\n"):
            text += "\n"
    return text


def setUpModule() -> None:
    require(CHECK)


class DogfoodReportCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self._tmp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _run(self, root: Path | None = None) -> subprocess.CompletedProcess[str]:
        target = self.root if root is None else root
        return subprocess.run(
            [sys.executable, str(CHECK), str(target)],
            cwd=REPO,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_matching_receipt_exits_0(self) -> None:
        self._write("REPORT.md", _report([("01-link-fix", "PASS", "0")]))
        self._write("01-link-fix/receipt.json", _receipt("PASS", 0))
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK runs=1", proc.stdout)

    def test_status_mismatch_exits_1(self) -> None:
        # Planted fail case: the report says PASS and the receipt says FAIL.
        self._write("REPORT.md", _report([("01-mismatch", "PASS", "0")]))
        self._write("01-mismatch/receipt.json", _receipt("FAIL", 0))
        proc = self._run()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("01-mismatch", proc.stderr)
        self.assertIn("report=PASS", proc.stderr)
        self.assertIn("receipt=FAIL", proc.stderr)
        self.assertNotIn("OK runs=", proc.stdout)

    def test_exit_code_mismatch_exits_1(self) -> None:
        self._write("REPORT.md", _report([("02-exit", "FAIL", "1")]))
        self._write("02-exit/receipt.json", _receipt("FAIL", 4))
        proc = self._run()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("02-exit", proc.stderr)
        self.assertIn("exit_code", proc.stderr)
        self.assertIn("report=1", proc.stderr)
        self.assertIn("receipt=4", proc.stderr)

    def test_secret_like_receipt_exits_1_without_echoing_the_value(self) -> None:
        planted = "Bea" + "rer " + "dogfoodfakevalue99"
        self._write("REPORT.md", _report([("03-secret", "BLOCKED", "4")]))
        self._write(
            "03-secret/receipt.json",
            _receipt("BLOCKED", 4, extra="note: %s\n" % planted),
        )
        proc = self._run()
        combined = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 1)
        self.assertIn("03-secret", proc.stderr)
        self.assertIn("secret-like", proc.stderr)
        self.assertNotIn("dogfoodfakevalue99", combined)
        self.assertNotIn(planted, combined)

    def test_missing_receipt_exits_1(self) -> None:
        self._write("REPORT.md", _report([("04-absent", "FAIL", "1")]))
        (self.root / "04-absent").mkdir()
        proc = self._run()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("04-absent", proc.stderr)
        self.assertIn("missing receipt.json", proc.stderr)

    def test_run_dir_omitted_from_report_exits_1(self) -> None:
        self._write("REPORT.md", _report([]))
        self._write("05-orphan/receipt.json", _receipt("PASS", 0))
        proc = self._run()
        self.assertEqual(proc.returncode, 1)
        self.assertIn("05-orphan", proc.stderr)
        self.assertIn("missing from REPORT", proc.stderr)

    def test_real_dogfood_tree_matches_its_report(self) -> None:
        proc = self._run(DOGFOOD)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK runs=", proc.stdout)


if __name__ == "__main__":
    unittest.main()
