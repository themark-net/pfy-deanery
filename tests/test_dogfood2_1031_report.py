"""The dogfood2 report matches its receipts, and a planted mismatch fails.

How this fails: a row's status, exit code, or review disagrees with
receipt.json, the median line disagrees with the walls, or a human-accept
PASS commit does not carry the Built-by trailer for that receipt.
How we recover: fix the report row or the trailer, then rerun the checker.
The planted mismatch is only under this worktree's tmp/.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CHECK = REPO / "eval" / "dogfood2-1031" / "check_reports.py"
DOGFOOD = REPO / "eval" / "dogfood2-1031"
SCRATCH = REPO / "tmp" / "dogfood2-check-tests"


def _run(root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECK), str(root), str(REPO)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=False,
    )


class Dogfood2ReportTests(unittest.TestCase):
    def test_real_tree_matches_receipts_and_trailers(self) -> None:
        proc = _run(DOGFOOD)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK runs=8", proc.stdout)

    def test_planted_status_mismatch_fails(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            src = DOGFOOD / "06-daemon-stop-timeout" / "receipt.json"
            dest_dir = root / "06-daemon-stop-timeout"
            dest_dir.mkdir()
            payload = json.loads(src.read_text(encoding="utf-8"))
            payload["status"] = "FAIL"
            (dest_dir / "receipt.json").write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
            report = (DOGFOOD / "REPORT.md").read_text(encoding="utf-8")
            # Keep the other rows out so this fixture is one run.
            kept = [
                line
                for line in report.splitlines()
                if not line.startswith("| 0") or line.startswith("| 06-")
            ]
            text = "\n".join(kept) + "\n"
            text = text.replace("- runs: 8\n", "- runs: 1\n")
            text = text.replace("- gate_pass_rate: 7/8\n", "- gate_pass_rate: 1/1\n")
            text = text.replace("- review_accept_rate: 7/8\n", "- review_accept_rate: 1/1\n")
            text = text.replace("- human_accept_rate: 7/8\n", "- human_accept_rate: 1/1\n")
            text = text.replace("- median_wall_s: 529\n", "- median_wall_s: 301\n")
            (root / "REPORT.md").write_text(text, encoding="utf-8")
            proc = _run(root)
            blob = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 1, blob)
            self.assertIn("06-daemon-stop-timeout", proc.stderr)
            self.assertIn("status report=PASS receipt=FAIL", proc.stderr)
            self.assertNotIn("OK runs=", proc.stdout)

    def test_planted_trailer_mismatch_fails(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as raw:
            root = Path(raw)
            src_dir = DOGFOOD / "06-daemon-stop-timeout"
            dest = root / "06-daemon-stop-timeout"
            dest.mkdir()
            shutil.copy(src_dir / "receipt.json", dest / "receipt.json")
            report = (DOGFOOD / "REPORT.md").read_text(encoding="utf-8")
            kept = [
                line
                for line in report.splitlines()
                if not line.startswith("| 0") or line.startswith("| 06-")
            ]
            text = "\n".join(kept) + "\n"
            text = text.replace("| 072c7cd |", "| 31a863c |")
            text = text.replace("- runs: 8\n", "- runs: 1\n")
            text = text.replace("- gate_pass_rate: 7/8\n", "- gate_pass_rate: 1/1\n")
            text = text.replace("- review_accept_rate: 7/8\n", "- review_accept_rate: 1/1\n")
            text = text.replace("- human_accept_rate: 7/8\n", "- human_accept_rate: 1/1\n")
            text = text.replace("- median_wall_s: 529\n", "- median_wall_s: 301\n")
            (root / "REPORT.md").write_text(text, encoding="utf-8")
            proc = _run(root)
            blob = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 1, blob)
            self.assertIn("06-daemon-stop-timeout", proc.stderr)
            self.assertIn("trailer", proc.stderr)
            self.assertNotIn("OK runs=", proc.stdout)


if __name__ == "__main__":
    unittest.main()
