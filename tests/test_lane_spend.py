"""Behavior of `./pfy lanes spend` against fixture Grok session dirs.

Spend is local and read-only: usage.json ticks and updates.jsonl for sessions
that are still open. No network and no auth files.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _encode(cwd: str) -> str:
    return urllib.parse.quote(cwd, safe="")


def _ticks(usd: str) -> int:
    """usd is a decimal string. 1 USD = 1e10 ticks."""
    from decimal import Decimal

    return int(Decimal(usd) * Decimal("10000000000"))


class LaneSpendTests(unittest.TestCase):
    def setUp(self):
        # Hosted checkouts do not have gitignored tmp/.
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.tmp = Path(tempfile.mkdtemp(prefix="lane-spend-", dir=str(ROOT / "tmp")))
        self.sessions = self.tmp / "sessions"
        self.sessions.mkdir()
        self.env_base = os.environ.copy()
        self.env_base["HOME"] = str(self.tmp)
        self.env_base["PFY_STATE_DIR"] = str(self.tmp / "state")
        self.env_base.pop("GROK_HOME", None)
        self.env_base.pop("PFY_LANE_USD_PER_POINT", None)
        self.env_base.pop("PFY_LANE_SPEND_THRESHOLD", None)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_pfy(self, *args, extra_env=None):
        env = dict(self.env_base)
        if extra_env:
            env.update(extra_env)
        return subprocess.run(
            [str(ROOT / "pfy"), *args],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def spend(self, *args, extra_env=None):
        return self.run_pfy("lanes", "spend", *args, extra_env=extra_env)

    def session(self, cwd: str, sid: str) -> Path:
        path = self.sessions / _encode(cwd) / sid
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_usage(self, cwd, sid, ticks, updated_at=None, tokens=None):
        folder = self.session(cwd, sid)
        session = {"costUsdTicks": ticks}
        if tokens is not None:
            session["totalTokens"] = tokens
        body = {"sessionId": sid, "session": session}
        if updated_at is not None:
            body["updatedAt"] = updated_at
        (folder / "usage.json").write_text(json.dumps(body), encoding="utf-8")
        return folder

    def write_updates(self, cwd, sid, lines):
        folder = self.session(cwd, sid)
        chunks = []
        for line in lines:
            chunks.append(line if isinstance(line, str) else json.dumps(line))
        (folder / "updates.jsonl").write_text("\n".join(chunks) + "\n", encoding="utf-8")
        return folder

    def usage_line(self, timestamp, **usage):
        return {
            "method": "session/update",
            "params": {"update": {"sessionUpdate": "usage", "usage": usage}},
            "timestamp": timestamp,
        }

    def test_done_spend_groups_worktrees(self):
        when = "2026-11-15T12:00:00Z"
        self.write_usage("/tmp/dev/alpha-lane", "s1", _ticks("1.25"), when)
        self.write_usage("/tmp/dev/alpha-lane", "s2", _ticks("2.00"), when)
        self.write_usage("/tmp/dev/beta-lane", "s3", _ticks("0.50"), when)
        self.write_usage("/tmp/other-lane", "s4", _ticks("0.25"), when)
        proc = self.spend("--sessions", str(self.sessions), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        by_lane = {row["lane"]: row for row in report["lanes"]}
        self.assertAlmostEqual(by_lane["alpha-lane"]["done_usd"], 3.25, places=4)
        self.assertAlmostEqual(by_lane["beta-lane"]["done_usd"], 0.50, places=4)
        self.assertAlmostEqual(by_lane["other-lane"]["done_usd"], 0.25, places=4)
        self.assertEqual(by_lane["alpha-lane"]["cwd"], "/tmp/dev/alpha-lane")
        self.assertAlmostEqual(report["total_done_usd"], 4.0, places=4)
        self.assertAlmostEqual(report["total_live_usd"], 0.0, places=4)
        self.assertAlmostEqual(report["total_usd"], 4.0, places=4)
        self.assertFalse(report["stop"])
        self.assertIn("no baseline; threshold not applied", report["message"])
        text = self.spend("--sessions", str(self.sessions))
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertIn("TOTAL done $4.00 + live~$0.00 = ~$4.00", text.stdout)
        self.assertIn("alpha-lane", text.stdout)
        self.assertIn("other-lane", text.stdout)

    def test_finished_session_is_not_added_twice(self):
        # Fail: usage.json and updates.jsonl for one session are summed together.
        # Recovery: a readable usage.json is the whole session.
        cwd = "/tmp/dev/lane-1115"
        self.write_usage(cwd, "both", _ticks("1.00"), "2026-11-15T12:00:00Z")
        self.write_updates(
            cwd,
            "both",
            [self.usage_line(1_763_200_000, costUsdTicks=_ticks("50.00"), totalTokens=9)],
        )
        proc = self.spend("--sessions", str(self.sessions), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        self.assertEqual([row["id"] for row in report["sessions"]], ["both"])
        self.assertEqual(report["sessions"][0]["status"], "done")
        self.assertEqual(report["sessions"][0]["source"], "usage.json")
        self.assertAlmostEqual(report["total_usd"], 1.0, places=4)

    def test_inflight_estimates_tokens_and_prefers_ticks(self):
        # Fail: an open session with no usage.json is dropped, or the first
        # updates line wins, or tokens are priced even when ticks are present.
        # Recovery: max ticks win; otherwise max totalTokens at $0.062 / 1M;
        # input+output is used only when totalTokens is absent.
        cwd = "/tmp/dev/gamma-lane"
        stamp = 1_763_200_000
        self.write_usage(cwd, "done", _ticks("1.00"), "2026-11-15T12:00:00Z")
        self.write_updates(
            cwd,
            "est",
            [
                "not-json",
                [],
                self.usage_line(stamp, totalTokens=1_000_000),
                self.usage_line(stamp + 10, totalTokens=2_000_000),
            ],
        )
        self.write_updates(
            cwd,
            "ticks",
            [
                self.usage_line(stamp, totalTokens=100, costUsdTicks=_ticks("0.10")),
                self.usage_line(stamp + 5, totalTokens=50_000_000, costUsdTicks=_ticks("1.25")),
            ],
        )
        self.write_updates(
            cwd,
            "parts",
            [self.usage_line(stamp, inputTokens=500_000, outputTokens=500_000)],
        )
        proc = self.spend("--sessions", str(self.sessions), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        by_id = {row["id"]: row for row in report["sessions"]}
        self.assertEqual(by_id["est"]["status"], "live-est")
        self.assertTrue(by_id["est"]["estimated"])
        self.assertEqual(by_id["est"]["tokens"], 2_000_000)
        self.assertAlmostEqual(by_id["est"]["usd"], 0.124, places=6)
        self.assertEqual(by_id["ticks"]["status"], "live")
        self.assertFalse(by_id["ticks"]["estimated"])
        self.assertAlmostEqual(by_id["ticks"]["usd"], 1.25, places=4)
        self.assertEqual(by_id["parts"]["status"], "live-est")
        self.assertEqual(by_id["parts"]["tokens"], 1_000_000)
        self.assertAlmostEqual(by_id["parts"]["usd"], 0.062, places=6)
        self.assertAlmostEqual(report["total_done_usd"], 1.0, places=4)
        self.assertAlmostEqual(report["total_live_usd"], 1.436, places=4)
        text = self.spend("--sessions", str(self.sessions))
        self.assertIn("TOTAL done $1.00 + live~$1.44 = ~$2.44", text.stdout)

    def test_malformed_recovers_and_keeps_siblings(self):
        # Fail: one bad usage.json aborts the report or drops the sibling lane.
        # Recovery: keep the good session, use updates.jsonl when it has spend,
        # and record the session that has neither.
        cwd = "/tmp/dev/delta-lane"
        self.write_usage(cwd, "good", _ticks("2.00"), "2026-11-15T12:00:00Z")
        bad = self.session(cwd, "recovered")
        (bad / "usage.json").write_text("{not-json", encoding="utf-8")
        self.write_updates(
            cwd,
            "recovered",
            [self.usage_line(1_763_200_000, costUsdTicks=_ticks("1.00"), totalTokens=10)],
        )
        dead = self.session(cwd, "dead")
        (dead / "usage.json").write_text("{still-not-json", encoding="utf-8")
        self.session(cwd, "empty")
        proc = self.spend("--sessions", str(self.sessions), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        by_id = {row["id"]: row for row in report["sessions"]}
        self.assertEqual(by_id["good"]["status"], "done")
        self.assertAlmostEqual(by_id["good"]["usd"], 2.0, places=4)
        self.assertEqual(by_id["recovered"]["status"], "live")
        self.assertAlmostEqual(by_id["recovered"]["usd"], 1.0, places=4)
        self.assertEqual(by_id["dead"]["status"], "malformed")
        self.assertAlmostEqual(by_id["dead"]["usd"], 0.0, places=4)
        self.assertEqual(by_id["empty"]["status"], "missing")
        self.assertAlmostEqual(report["total_usd"], 3.0, places=4)
        blob = " ".join(report["problems"])
        self.assertIn("recovered", blob)
        self.assertIn("malformed usage.json", blob)
        self.assertIn("dead", blob)
        self.assertNotIn("Traceback", proc.stderr)

    def test_filters_glob_and_since(self):
        self.write_usage(
            "/tmp/dev/lane-1115",
            "old",
            _ticks("5.00"),
            "2026-11-14T00:00:00Z",
        )
        self.write_usage(
            "/tmp/dev/lane-1115",
            "new",
            _ticks("1.00"),
            "2026-11-15T12:00:00.987654321Z",
        )
        self.write_usage(
            "/tmp/dev/lane-1114",
            "other",
            _ticks("9.00"),
            "2026-11-15T12:00:00Z",
        )
        old_ts = int(datetime(2026, 11, 10, tzinfo=timezone.utc).timestamp())
        self.write_updates(
            "/tmp/dev/lane-1115",
            "stale-live",
            [self.usage_line(old_ts, totalTokens=1_000_000)],
        )
        proc = self.spend(
            "--sessions",
            str(self.sessions),
            "--glob",
            "*1115*",
            "--since",
            "2026-11-15T00:00:00Z",
            "--json",
        )
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        self.assertEqual([row["id"] for row in report["sessions"]], ["new"])
        self.assertAlmostEqual(report["total_usd"], 1.0, places=4)
        self.assertGreaterEqual(report["excluded_by_since"], 2)
        self.assertNotIn("lane-1114", json.dumps(report["lanes"]))

    def test_projection_stops_at_threshold(self):
        # Fail: spend before the baseline is added again, or 75% is treated as safe.
        # Recovery: only dollars at or after the baseline move the percent,
        # and the process exits 1 with a STOP line the scheduler can read.
        cwd = "/tmp/dev/lane-1115"
        self.write_usage(cwd, "before", _ticks("44.00"), "2026-11-14T23:59:59.123456789Z")
        self.write_usage(cwd, "after", _ticks("22.00"), "2026-11-15T12:00:00.987654321+00:00")
        touched = self.write_usage(cwd, "old-mtime", _ticks("4.40"))
        os.utime(touched / "usage.json", (1_577_836_800, 1_577_836_800))
        common = [
            "--sessions",
            str(self.sessions),
            "--baseline-time",
            "2026-11-15T08:00:00Z",
        ]
        proc = self.spend(*common, "--baseline-percent", "70", "--json")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertTrue(report["stop"])
        self.assertAlmostEqual(report["total_usd"], 70.40, places=2)
        self.assertAlmostEqual(report["since_baseline_usd"], 22.0, places=4)
        self.assertAlmostEqual(report["added_points"], 5.0, places=4)
        self.assertAlmostEqual(report["projected_percent"], 75.0, places=4)
        self.assertEqual(report["message"], "STOP projected 75.00% is at or above threshold 75.00%")
        self.assertIn(report["message"], proc.stderr)
        self.assertFalse(proc.stdout.lstrip().startswith("STOP"))
        by_id = {row["id"]: row for row in report["sessions"]}
        self.assertFalse(by_id["before"]["in_baseline_delta"])
        self.assertTrue(by_id["after"]["in_baseline_delta"])
        self.assertFalse(by_id["old-mtime"]["in_baseline_delta"])

        under = self.spend(*common, "--baseline-percent", "69")
        self.assertEqual(under.returncode, 0, under.stderr + under.stdout)
        self.assertIn("under threshold 75.00% (projected 74.00%)", under.stdout)
        self.assertIn("STOP projected 74.00% is at or above threshold 74.00%", 
                      self.spend(*common, "--baseline-percent", "69", "--threshold", "74").stdout)

        already = self.spend(
            "--sessions",
            str(self.sessions),
            "--since",
            "2099-01-01T00:00:00Z",
            "--baseline-percent",
            "75",
            "--baseline-time",
            "2099-01-01T00:00:00Z",
            "--json",
        )
        self.assertEqual(already.returncode, 1, already.stdout + already.stderr)
        self.assertAlmostEqual(json.loads(already.stdout)["projected_percent"], 75.0, places=4)
        self.assertAlmostEqual(json.loads(already.stdout)["since_baseline_usd"], 0.0, places=4)

    def test_usd_per_point_is_configurable(self):
        self.write_usage("/tmp/dev/lane-1115", "s", _ticks("4.40"), "2026-11-15T12:00:00Z")
        base = [
            "--sessions",
            str(self.sessions),
            "--baseline-percent",
            "0",
            "--baseline-time",
            "2026-11-15T00:00:00Z",
            "--json",
        ]
        default = json.loads(self.spend(*base).stdout)
        self.assertAlmostEqual(default["usd_per_point"], 4.40, places=4)
        self.assertAlmostEqual(default["projected_percent"], 1.0, places=4)
        custom = json.loads(self.spend(*base, "--usd-per-point", "2.20").stdout)
        self.assertAlmostEqual(custom["projected_percent"], 2.0, places=4)
        from_env = json.loads(
            self.spend(*base, extra_env={"PFY_LANE_USD_PER_POINT": "2.20"}).stdout
        )
        self.assertAlmostEqual(from_env["projected_percent"], 2.0, places=4)
        flag_wins = json.loads(
            self.spend(
                *base,
                "--usd-per-point",
                "4.40",
                extra_env={"PFY_LANE_USD_PER_POINT": "2.20"},
            ).stdout
        )
        self.assertAlmostEqual(flag_wins["projected_percent"], 1.0, places=4)

    def test_missing_root_and_empty_root(self):
        empty = self.spend("--sessions", str(self.sessions), "--json")
        self.assertEqual(empty.returncode, 0, empty.stderr)
        report = json.loads(empty.stdout)
        self.assertEqual(report["sessions"], [])
        self.assertAlmostEqual(report["total_usd"], 0.0, places=4)
        self.assertIn("no sessions", empty.stdout)
        (self.sessions / "not-a-worktree.txt").write_text("ignore", encoding="utf-8")
        still = self.spend("--sessions", str(self.sessions))
        self.assertEqual(still.returncode, 0, still.stderr)
        self.assertIn("TOTAL done $0.00 + live~$0.00 = ~$0.00", still.stdout)

        absent = self.spend("--sessions", str(self.tmp / "nope"))
        self.assertEqual(absent.returncode, 2, absent.stdout)
        self.assertIn("sessions dir not found", absent.stderr)

        untouched = self.spend("--json")
        self.assertEqual(untouched.returncode, 0, untouched.stderr + untouched.stdout)
        self.assertEqual(json.loads(untouched.stdout)["sessions"], [])

        home = self.tmp / "grok-home"
        target = home / "sessions"
        target.mkdir(parents=True)
        self.sessions = target
        self.write_usage("/tmp/dev/from-home", "s", _ticks("0.10"), "2026-11-15T12:00:00Z")
        proc = self.spend("--json", extra_env={"GROK_HOME": str(home)})
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        report = json.loads(proc.stdout)
        self.assertEqual(report["lanes"][0]["lane"], "from-home")
        self.assertAlmostEqual(report["total_usd"], 0.10, places=4)

    def test_bad_args_exit_2(self):
        # Fail: a half baseline still prints a percent and exits 0.
        # Recovery: exit 2 and do not pretend a projection was made.
        half = self.spend("--sessions", str(self.sessions), "--baseline-percent", "40")
        self.assertEqual(half.returncode, 2, half.stdout)
        self.assertIn("baseline-percent and baseline-time are both required", half.stderr)
        self.assertNotIn("projected", half.stdout)
        bad_time = self.spend("--sessions", str(self.sessions), "--since", "yesterday")
        self.assertEqual(bad_time.returncode, 2)
        self.assertIn("bad time", bad_time.stderr)
        zero = self.spend("--sessions", str(self.sessions), "--usd-per-point", "0")
        self.assertEqual(zero.returncode, 2)
        self.assertIn("usd-per-point must be positive", zero.stderr)
        negative = self.spend("--sessions", str(self.sessions), "--threshold", "-1")
        self.assertEqual(negative.returncode, 2)
        self.assertIn("threshold must be zero or positive", negative.stderr)
        bare = self.run_pfy("lanes")
        self.assertEqual(bare.returncode, 2)

    def test_read_only_skips_secrets_and_outside_links(self):
        # Fail: the scan opens auth.json or follows a symlink out of the root
        # and adds that spend. Recovery: only usage.json and updates.jsonl that
        # resolve inside the sessions root are summed, and nothing is written.
        cwd = "/tmp/dev/lane-1115"
        folder = self.write_usage(cwd, "real", _ticks("1.00"), "2026-11-15T12:00:00Z")
        canaries = {
            folder / "auth.json": "SECRET-LANE-AUTH-9f3a\n",
            folder / "chat.json": "SECRET-LANE-CHAT-9f3a\n",
            self.sessions.parent / "config.toml": "SECRET-LANE-CONFIG-9f3a\n",
            self.sessions.parent / "auth.json": "SECRET-LANE-HOMEAUTH-9f3a\n",
        }
        for path, text in canaries.items():
            path.write_text(text, encoding="utf-8")
        outside = self.tmp / "outside-spend" / "hidden"
        outside.mkdir(parents=True)
        (outside / "usage.json").write_text(
            json.dumps({"session": {"costUsdTicks": _ticks("50.00"), "note": "SECRET-LANE-OUTSIDE-9f3a"}}),
            encoding="utf-8",
        )
        link = self.sessions / _encode("/tmp/dev/evil-lane")
        link.symlink_to(self.tmp / "outside-spend")
        before = self._snapshot(self.sessions)
        proc = self.spend("--sessions", str(self.sessions), "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        blob = proc.stdout + proc.stderr
        for text in canaries.values():
            self.assertNotIn(text.strip(), blob)
        self.assertNotIn("SECRET-LANE-OUTSIDE-9f3a", blob)
        self.assertNotIn("auth.json", blob)
        report = json.loads(proc.stdout)
        self.assertAlmostEqual(report["total_usd"], 1.0, places=4)
        self.assertEqual(self._snapshot(self.sessions), before)

    def test_help_and_module_entry(self):
        help_proc = self.run_pfy("help")
        self.assertEqual(help_proc.returncode, 0, help_proc.stderr)
        self.assertIn("pfy lanes spend", help_proc.stdout)
        self.assertIn("threshold", help_proc.stdout)
        module = subprocess.run(
            [sys.executable, "-m", "pfylib", "lanes", "spend", "--sessions", str(self.sessions), "--json"],
            cwd=str(ROOT),
            env=self.env_base,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(module.returncode, 0, module.stderr)
        self.assertEqual(json.loads(module.stdout)["total_usd"], 0)

    def test_docs_name_the_stop_rule(self):
        text = (ROOT / "docs" / "modules" / "lane-spend.md").read_text(encoding="utf-8")
        for phrase in (
            "4.40",
            "75",
            "usage.json",
            "updates.jsonl",
            "costUsdTicks",
            "--baseline-percent",
            "auth.json",
            "0.062",
        ):
            self.assertIn(phrase, text, phrase)
        self.assertIn("pfy lanes spend", (ROOT / "docs" / "modules" / "pfy.md").read_text(encoding="utf-8"))
        self.assertIn("lane-spend.md", (ROOT / "docs" / "modules" / "README.md").read_text(encoding="utf-8"))

    def _snapshot(self, root: Path):
        rows = []
        for path in sorted(root.rglob("*")):
            rel = str(path.relative_to(root))
            if path.is_symlink():
                rows.append((rel, "link", os.readlink(path)))
            elif path.is_file():
                stat = path.stat()
                rows.append((rel, "file", stat.st_mtime_ns, stat.st_size, path.read_bytes()))
            else:
                rows.append((rel, "dir"))
        return rows


if __name__ == "__main__":
    unittest.main()
