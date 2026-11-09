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

    def test_part_names_without_levels_are_not_coverage(self) -> None:
        bare = run("--parts", "track,catalog,evaluate,integrate")
        self.assertEqual(bare.returncode, 2, bare.stdout + bare.stderr)
        self.assertIn("coverage level required", bare.stderr)
        self.assertIn("track=partial,catalog=partial", bare.stderr)
        self.assertNotIn("supersede_candidate", bare.stdout)

        recovered = run("--parts", "track=partial,catalog=partial,evaluate=none,integrate=none")
        self.assertEqual(recovered.returncode, 0, recovered.stderr)
        body = json.loads(recovered.stdout)
        self.assertEqual(body["parts"], ["track", "catalog"])
        self.assertEqual(body["coverage"]["evaluate"], "none")
        self.assertEqual(body["coverage"]["integrate"], "none")
        self.assertTrue(body["supersede_candidate"])
        self.assertEqual(body["suite"], ["track", "catalog", "evaluate", "integrate"])

    def test_none_does_not_count_as_coverage(self) -> None:
        one = run("--parts", "track=none,catalog=full,evaluate=none,integrate=none")
        self.assertEqual(one.returncode, 0, one.stderr)
        body = json.loads(one.stdout)
        self.assertEqual(body["parts"], ["catalog"])
        self.assertFalse(body["supersede_candidate"])

        unknown = run("--parts", "local=full")
        self.assertEqual(unknown.returncode, 2, unknown.stdout)
        self.assertIn("unknown part: local", unknown.stderr)
        self.assertIn("integrate is the local-first part", unknown.stderr)

        bad_level = run("--parts", "track=yes,catalog=partial")
        self.assertEqual(bad_level.returncode, 2)
        self.assertIn("must be one of none, partial, full", bad_level.stderr)

    def test_watchlist_candidate_uses_levels_not_key_count(self) -> None:
        data = copy.deepcopy(self.data)
        data["candidate_min_parts"] = 3
        data["projects"] = [data["projects"][0]]
        data["projects"][0]["coverage"] = {
            "track": "full",
            "catalog": "partial",
            "evaluate": "none",
            "integrate": "none",
        }
        res = run("--file", self.write(data), "--today", "2026-11-08")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("candidate:", res.stdout)

        data["projects"][0]["coverage"]["integrate"] = "partial"
        res = run("--file", self.write(data), "--today", "2026-11-08")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("candidate: Flux (Nairon-AI)", res.stdout)
        self.assertIn("integrate=partial", res.stdout)
        self.assertIn("evaluate=none", res.stdout)

    def test_coverage_list_is_rejected_and_an_object_recovers(self) -> None:
        data = copy.deepcopy(self.data)
        data["projects"][0]["coverage"] = ["track", "catalog", "evaluate", "integrate"]
        res = run("--file", self.write(data), "--today", "2026-11-08")
        self.assertEqual(res.returncode, 1)
        self.assertIn("coverage must be an object", res.stderr)
        self.assertNotIn("candidate: Flux", res.stdout)

        data["projects"][0]["coverage"] = {
            "track": "partial",
            "catalog": "partial",
            "evaluate": "none",
            "integrate": "none",
        }
        res = run("--file", self.write(data), "--today", "2026-11-08")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("candidate: Flux (Nairon-AI)", res.stdout)

    def test_full_suite_recovers_when_verdict_is_replace_us(self) -> None:
        data = copy.deepcopy(self.data)
        data["projects"][0]["coverage"] = {
            part: "full" for part in ("track", "catalog", "evaluate", "integrate")
        }
        data["projects"][0]["verdict"] = "replace_us"
        res = run("--file", self.write(data), "--today", "2026-11-08")
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("candidate: Flux (Nairon-AI)", res.stdout)
        self.assertNotIn("STOP", res.stderr)

    def test_min_parts_must_be_an_integer(self) -> None:
        data = copy.deepcopy(self.data)
        data["candidate_min_parts"] = "2"
        res = run("--file", self.write(data), "--today", "2026-11-08")
        self.assertEqual(res.returncode, 1)
        self.assertIn("candidate_min_parts must be an integer", res.stderr)
        self.assertNotIn("Traceback", res.stderr)

    def test_declared_suite_must_stay_the_four_parts(self) -> None:
        data = copy.deepcopy(self.data)
        del data["parts"]["evaluate"]
        data["parts"]["local"] = "local-first as its own key"
        res = run("--file", self.write(data), "--today", "2026-11-08")
        self.assertEqual(res.returncode, 1)
        self.assertIn("parts must describe the suite", res.stderr)


if __name__ == "__main__":
    unittest.main()
