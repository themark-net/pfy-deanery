"""Cloud quote includes opt-in flake re-runs, and cloud warns on fixed ports.

Fail: --flake-runs N leaves the pre-spend wall on the daily figure and the
receipt estimate.flake_runs at 0, or a cloud PASS hides a literal non-zero
bind. Recover: the cost line names the re-runs at $0 (they are tests), the
cloud wall minutes grow, the receipt records the count and the longer wall,
and a port warning is printed without failing the build. Port 0 stays quiet.
Omitting the flag, passing 0, or setting PFY_BUILD_FLAKE_RUNS does not grow
the cloud quote.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import unittest
from pathlib import Path

from tests.test_pfy_build_cloud import CLOUD, SCRATCH, _drop_external_worktrees, _git, _init_repo, _run, _write_exe

_PORT_FILE = """\
import socket


def bind_fixed():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 15439))


def bind_ephemeral():
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))


def listen_fixed(sock):
    sock.listen(15439)


def listen_backlog(sock):
    sock.listen(0)
"""

_GREEN = """\
print("GATE-OK")
raise SystemExit(0)
"""

_WALL = re.compile(r"^cloud wall: (\d+) min-(\d+) min", re.M)


def _wall_minutes(text: str) -> tuple[int, int]:
    match = _WALL.search(text)
    if match is None:
        raise AssertionError("cloud wall line missing:\n%s" % text)
    return int(match.group(1)), int(match.group(2))


class CloudFlakeQuoteTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)
        self.home = self.side / "home"
        self.home.mkdir()
        self.grok_home = self.side / "grok"
        self.grok_home.mkdir()
        self.no_history = self.side / "no-history"
        self.no_history.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _env(self, history: Path | None = None) -> dict:
        return {
            "HOME": str(self.home),
            "GROK_HOME": str(self.grok_home),
            "PFY_COST_HISTORY_ROOT": str(history or self.no_history),
            "PFY_BUILD_YES": "1",
            "CI": "",
        }

    def _dry(self, extra: list[str], env: dict | None = None):
        receipt = self.side / ("receipt-" + "-".join(extra) if extra else "receipt-plain")
        if receipt.exists():
            shutil.rmtree(receipt)
        argv = [
            sys.executable,
            str(CLOUD),
            "add the feature",
            "--repo",
            str(self.repo),
            "--receipt-dir",
            str(receipt),
            "--dry-run",
            "--no-review",
            "--retries",
            "0",
            *extra,
        ]
        proc = _run(argv, self.repo, env=env or self._env(), timeout=30)
        text = (proc.stdout or "") + (proc.stderr or "")
        data = json.loads((receipt / "receipt.json").read_text(encoding="utf-8"))
        return proc, text, data

    def test_flake_runs_show_on_the_quote_and_the_receipt(self) -> None:
        # Fail: the banner wall matches the daily quote and estimate.flake_runs
        # stays 0, so the operator approves a spend that hides the re-runs.
        # Recover: dollars stay the model quote, the cost line says the re-runs
        # are tests at $0, the wall minutes grow, and the receipt stores the count.
        plain_proc, plain_text, plain = self._dry([])
        self.assertEqual(plain_proc.returncode, 0, plain_text)
        flagged_proc, flagged_text, flagged = self._dry(["--flake-runs", "2"])
        self.assertEqual(flagged_proc.returncode, 0, flagged_text)
        self.assertEqual(plain["estimate"]["flake_runs"], 0, plain)
        self.assertEqual(flagged["estimate"]["flake_runs"], 2, flagged)
        self.assertEqual(flagged["estimate"]["usd"], plain["estimate"]["usd"])
        self.assertEqual(flagged["estimate"]["alternative"]["flake_runs"], 0)
        self.assertGreater(flagged["estimate"]["wall_low_s"], plain["estimate"]["wall_low_s"])
        self.assertGreater(flagged["estimate"]["wall_high_s"], plain["estimate"]["wall_high_s"])
        self.assertIn("flake-gate re-run", flagged["estimate"]["wall_basis"])
        plain_low, plain_high = _wall_minutes(plain_text)
        flag_low, flag_high = _wall_minutes(flagged_text)
        self.assertGreater(flag_low, plain_low, flagged_text)
        self.assertGreater(flag_high, plain_high, flagged_text)
        self.assertIn("2 flake-gate re-run", flagged_text)
        self.assertIn("(tests, $0)", flagged_text)
        self.assertNotIn("flake-gate re-run", plain_text)

        skipped_proc, skipped_text, skipped = self._dry(["--flake-runs", "0"])
        self.assertEqual(skipped_proc.returncode, 0, skipped_text)
        self.assertEqual(skipped["estimate"]["flake_runs"], 0)
        self.assertEqual(_wall_minutes(skipped_text), (plain_low, plain_high), skipped_text)

        leaked_proc, leaked_text, leaked = self._dry(
            [],
            env={**self._env(), "PFY_BUILD_FLAKE_RUNS": "2"},
        )
        self.assertEqual(leaked_proc.returncode, 0, leaked_text)
        self.assertEqual(leaked["estimate"]["flake_runs"], 0, leaked)
        self.assertEqual(_wall_minutes(leaked_text), (plain_low, plain_high), leaked_text)
        self.assertNotIn("flake", leaked)

    def test_history_wall_still_grows_when_flake_runs_is_set(self) -> None:
        # Fail: a past cloud wall replaces the static floor and the extra
        # re-runs disappear from the minutes. Recover: the quoted minutes sit
        # above that history, and the receipt still records flake_runs.
        hist_root = self.side / "history"
        stamp = hist_root / "pipelines" / "dogfood" / "build-cloud" / "old"
        stamp.mkdir(parents=True)
        (stamp / "receipt.json").write_text(
            json.dumps({"wall_seconds": 600, "status": "PASS"}),
            encoding="utf-8",
        )
        env = self._env(hist_root)
        plain_proc, plain_text, plain = self._dry([], env=env)
        flagged_proc, flagged_text, flagged = self._dry(["--flake-runs", "2"], env=env)
        self.assertEqual(plain_proc.returncode, 0, plain_text)
        self.assertEqual(flagged_proc.returncode, 0, flagged_text)
        self.assertEqual(plain["estimate"]["wall_low_s"], 600, plain)
        self.assertGreater(flagged["estimate"]["wall_low_s"], 600, flagged)
        self.assertGreater(flagged["estimate"]["wall_high_s"], plain["estimate"]["wall_high_s"])
        self.assertEqual(flagged["estimate"]["flake_runs"], 2)
        self.assertEqual(flagged["estimate"]["usd"], plain["estimate"]["usd"])
        plain_low, plain_high = _wall_minutes(plain_text)
        flag_low, flag_high = _wall_minutes(flagged_text)
        self.assertGreater(flag_low, plain_low, flagged_text)
        self.assertGreater(flag_high, plain_high, flagged_text)
        self.assertIn("flake-gate re-run", flagged_text)


class CloudFixedPortTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)
        (self.side / "home").mkdir()
        (self.side / "grok").mkdir()
        (self.side / "no-history").mkdir()
        self.receipt_dir = self.side / "receipt"
        tests = self.repo / "tests"
        tests.mkdir()
        (tests / "test_ports.py").write_text(_PORT_FILE, encoding="utf-8")
        added = _git(self.repo, "add", "tests/test_ports.py")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "add port samples")
        self.assertEqual(committed.returncode, 0, committed.stderr)

    def tearDown(self) -> None:
        _drop_external_worktrees(self.repo)
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def test_literal_port_is_warned_and_the_build_still_passes(self) -> None:
        # Fail: the cloud receipt has no fixed_ports warning, so a literal
        # bind ships quietly. Recover: stderr and the receipt name port 15439,
        # port 0 is absent, and status stays PASS.
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "Path('src').mkdir(exist_ok=True)\n"
            "Path('src/feature.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        gate = _write_exe(self.side / "gate.py", "#!/usr/bin/env python3\n" + _GREEN)
        argv = [
            sys.executable,
            str(CLOUD),
            "add the feature",
            "--repo",
            str(self.repo),
            "--receipt-dir",
            str(self.receipt_dir),
            "--timeout",
            "30",
            "--retries",
            "0",
            "--no-review",
            "--test-cmd",
            "%s %s" % (sys.executable, gate),
            "--grok-cmd",
            str(grok),
        ]
        proc = _run(
            argv,
            self.repo,
            env={
                "HOME": str(self.side / "home"),
                "GROK_HOME": str(self.side / "grok"),
                "PFY_COST_HISTORY_ROOT": str(self.side / "no-history"),
                "PFY_BUILD_YES": "1",
            },
            timeout=90,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        data = json.loads((self.receipt_dir / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(proc.returncode, 0, text)
        self.assertEqual(data["status"], "PASS", text)
        ports = data.get("fixed_ports") or []
        self.assertTrue(any(item.get("port") == 15439 for item in ports), data)
        self.assertFalse(any(item.get("port") == 0 for item in ports), ports)
        warned = " ".join(data.get("warnings") or [])
        self.assertIn("15439", warned)
        self.assertIn("tests/test_ports.py", warned)
        self.assertNotIn("port 0", warned)
        self.assertIn("fixed listen port 15439", text)
        self.assertNotIn("fixed listen port 0", text)


if __name__ == "__main__":
    unittest.main()
