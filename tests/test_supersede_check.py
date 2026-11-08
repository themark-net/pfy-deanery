"""Behavior tests for scripts/supersede_check.py (data/supersede-watchlist.json)."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "supersede_check.py"
WATCHLIST = ROOT / "data" / "supersede-watchlist.json"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, check=False)


class SupersedeCheck(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(WATCHLIST.read_text(encoding="utf-8"))
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write(self, data: dict) -> str:
        path = Path(self.tmp.name) / "w.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return str(path)

    def test_committed_watchlist_passes(self) -> None:
        newest = max(p["last_checked"] for p in self.data["projects"])
        res = run("--today", newest)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("candidate: Flux (Nairon-AI)", res.stdout)

    def test_full_suite_project_forces_stop(self) -> None:
        data = copy.deepcopy(self.data)
        data["projects"][0]["coverage"] = {p: "full" for p in ("track", "catalog", "evaluate", "integrate")}
        data["projects"][0]["verdict"] = "watch"
        res = run("--file", self.write(data), "--today", "2026-11-08")
        self.assertEqual(res.returncode, 1)
        self.assertIn("STOP and decide", res.stderr)

    def test_replace_us_without_full_coverage_fails(self) -> None:
        data = copy.deepcopy(self.data)
        data["projects"][-1]["verdict"] = "replace_us"
        res = run("--file", self.write(data), "--today", "2026-11-08")
        self.assertEqual(res.returncode, 1)
        self.assertIn("replace_us needs all four parts full", res.stderr)

    def test_stale_reported_not_fatal(self) -> None:
        res = run("--today", "2027-06-01")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("stale: AgenC", res.stdout)

    def test_bad_level_and_unreadable_file_fail(self) -> None:
        data = copy.deepcopy(self.data)
        data["projects"][0]["coverage"]["track"] = "yes"
        self.assertEqual(run("--file", self.write(data)).returncode, 1)
        self.assertEqual(run("--file", str(Path(self.tmp.name) / "missing.json")).returncode, 1)

    def test_intake_hook_flags_two_parts(self) -> None:
        self.assertTrue(json.loads(run("--parts", "track,evaluate").stdout)["supersede_candidate"])
        self.assertFalse(json.loads(run("--parts", "integrate").stdout)["supersede_candidate"])
        self.assertEqual(run("--parts", "vibes").returncode, 2)


if __name__ == "__main__":
    unittest.main()
