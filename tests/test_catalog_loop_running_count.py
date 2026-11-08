"""Running-cap count for integrate2 pid files.

A pid file counts only when <slug>.dispatched is beside it.
The same pid counts once. scheduler.pid and scheduler.launch.pid do not.
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _exe(path: Path, body: str) -> None:
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class RunningCountTest(unittest.TestCase):
    def test_scheduler_pids_do_not_count_and_one_pid_counts_once(self) -> None:
        scheduler = None
        lane = None
        try:
            scheduler = subprocess.Popen(["sleep", "60"])
            lane = subprocess.Popen(["sleep", "60"])
            with tempfile.TemporaryDirectory() as raw:
                state = Path(raw)
                integrate2 = state / "integrate2"
                integrate2.mkdir()
                (integrate2 / "scheduler.pid").write_text(f"{scheduler.pid}\n", encoding="utf-8")
                (integrate2 / "scheduler.launch.pid").write_text(
                    f"{scheduler.pid}\n",
                    encoding="utf-8",
                )
                (integrate2 / "lane-one.pid").write_text(f"{lane.pid}\n", encoding="utf-8")
                (integrate2 / "lane-one.dispatched").write_text("lane\n", encoding="utf-8")
                (integrate2 / "lane-one-again.pid").write_text(f"{lane.pid}\n", encoding="utf-8")
                (integrate2 / "lane-one-again.dispatched").write_text(
                    "lane\n",
                    encoding="utf-8",
                )
                launch_log = state / "launches.log"
                check = state / "supersede_check"
                runner = state / "systemd-run"
                _exe(check, "#!/bin/sh\nexit 0\n")
                _exe(runner, "#!/bin/sh\nprintf '%s\\n' launched >> \"$PFY_LAUNCH_LOG\"\n")
                env = os.environ.copy()
                for key in (
                    "PFY_INTEGRATE_ROOT",
                    "PFY_INTEGRATE2_ROOT",
                    "PFY_EVQ_ROOT",
                    "PFY_LOOP_WT",
                    "PFY_LOOP_STATE",
                    "PFY_LOOP_IN_WORKTREE",
                    "PFY_CATALOG_STATE_DIR",
                    "PFY_CATALOG_OFFLINE",
                ):
                    env.pop(key, None)
                env.update({
                    "PFY_SUPERSEDE_CHECK": str(check),
                    "PFY_SYSTEMD_RUN": str(runner),
                    "PFY_LAUNCH_LOG": str(launch_log),
                    "PFY_CATALOG_STATE_DIR": str(state),
                    "PFY_CATALOG_OFFLINE": "1",
                })
                proc = subprocess.run(
                    ["bash", str(ROOT / "scripts" / "catalog_loop.sh"), "tick"],
                    cwd=ROOT,
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=90,
                    check=False,
                )
                self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
                latest = json.loads((state / "loop.latest.json").read_text(encoding="utf-8"))
                running = latest["running"]
                self.assertEqual(len(running), 1)
                self.assertEqual(running[0]["slug"], "lane-one-again")
                self.assertEqual(running[0]["pid"], lane.pid)
                self.assertEqual(running[0]["source"], "integrate2")
                self.assertEqual(latest["slots"], 3)
        finally:
            for proc in (scheduler, lane):
                if proc is not None and proc.poll() is None:
                    proc.kill()
                    proc.wait()
