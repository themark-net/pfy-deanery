"""Phase seconds on a cloud build receipt, and the gates those seconds cover.

Fail: a slow gate is stored as 0, a phase is missing, or the commit recheck
is billed to the parent so the overhead ranking double-counts it.
Recover: the receipt names each phase, gate seconds cover the sleep, and
the gate process still runs once per check.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCRATCH = ROOT / "tmp" / "phase-clock-tests"
CLOUD = ROOT / "scripts" / "pfy_build_cloud.py"
PHASES = ("preflight", "worktree", "agent", "gate", "review", "commit")
# Four serial checks (before, after, flake, recheck) each sleep this long.
# Three checks stay under the assertion. Dropping one check fails the test.
GATE_SLEEP = 0.35
GATE_FLOOR = 1.15


def _run(argv, cwd, env=None, timeout=60):
    merged = os.environ.copy()
    merged["TMPDIR"] = str(SCRATCH)
    merged["PYTHONDONTWRITEBYTECODE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        argv,
        cwd=cwd,
        env=merged,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )


def _git(repo, *args):
    return _run(["git", *args], repo)


def _write_exe(path: Path, body: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _init_repo(path: Path) -> Path:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    init = _git(path, "init", "-b", "main")
    if init.returncode != 0:
        raise RuntimeError(init.stderr)
    _git(path, "config", "user.email", "phase-clock@example.com")
    _git(path, "config", "user.name", "phase-clock")
    (path / "README.md").write_text("fixture\n", encoding="utf-8")
    (path / ".gitignore").write_text("tmp/\npipelines/\n", encoding="utf-8")
    _git(path, "add", "README.md", ".gitignore")
    committed = _git(path, "commit", "-m", "init")
    if committed.returncode != 0:
        raise RuntimeError(committed.stderr)
    return path


def _gate_script(counter: Path, sleep: float, code: int) -> str:
    return (
        "#!/usr/bin/env python3\n"
        "import time\n"
        "from pathlib import Path\n"
        "p = Path(%r)\n"
        "n = int(p.read_text(encoding='utf-8') or '0') if p.exists() else 0\n"
        "p.write_text(str(n + 1), encoding='utf-8')\n"
        "time.sleep(%r)\n"
        "raise SystemExit(%d)\n" % (str(counter), sleep, code)
    )


def _grok_script(review_sleep: float, agent_sleep: float) -> str:
    return (
        "#!/usr/bin/env python3\n"
        "import sys, time\n"
        "from pathlib import Path\n"
        "blob = '\\n'.join(sys.argv)\n"
        "if 'PFY-CLOUD-REVIEW' in blob:\n"
        "    time.sleep(%r)\n"
        "    print('verdict: accept')\n"
        "    raise SystemExit(0)\n"
        "time.sleep(%r)\n"
        "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
        "raise SystemExit(0)\n" % (review_sleep, agent_sleep)
    )


class PhaseClockNestingTests(unittest.TestCase):
    def test_nested_gate_is_not_also_billed_to_commit(self) -> None:
        # Fail: the recheck gate is added to commit as well as gate, so the
        # receipt ranks commit too high and hides the suite rerun.
        # Recover: parent time pauses while the child runs.
        from pfylib.build_phase_clock import PhaseClock

        class Manual:
            def __init__(self) -> None:
                self.t = 0.0

            def __call__(self) -> float:
                return self.t

        clock_time = Manual()
        clock = PhaseClock(monotonic=clock_time)
        with clock.phase("commit"):
            clock_time.t = 2.0
            with clock.phase("gate"):
                clock_time.t = 5.0
            clock_time.t = 7.0
        report = clock.report()
        self.assertEqual(report["commit"], 4.0)
        self.assertEqual(report["gate"], 3.0)
        self.assertEqual(report["agent"], 0.0)
        self.assertLessEqual(sum(report.values()), clock.wall_seconds() + 0.001)


class CloudPhaseReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)
        self.counter = self.side / "gate-count"
        self.receipt_dir = self.side / "receipt"

    def tearDown(self) -> None:
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _build(self, gate_code: int, extra: list[str]) -> subprocess.CompletedProcess:
        gate = _write_exe(
            self.side / "gate.py",
            _gate_script(self.counter, GATE_SLEEP, gate_code),
        )
        grok = _write_exe(self.side / "grok.py", _grok_script(0.25, 0.30))
        return _run(
            [
                sys.executable,
                str(CLOUD),
                "add kept value",
                "--repo",
                str(self.repo),
                "--base",
                "HEAD",
                "--retries",
                "0",
                "--timeout",
                "30",
                "--test-cmd",
                "%s %s" % (sys.executable, gate),
                "--grok-cmd",
                str(grok),
                "--receipt-dir",
                str(self.receipt_dir),
                *extra,
            ],
            self.repo,
            timeout=60,
        )

    def _payload(self) -> dict:
        return json.loads((self.receipt_dir / "receipt.json").read_text(encoding="utf-8"))

    def _count(self) -> int:
        if not self.counter.exists():
            return 0
        return int(self.counter.read_text(encoding="utf-8") or "0")

    def test_pass_records_six_phases_and_runs_four_gates(self) -> None:
        proc = self._build(0, [])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._payload()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertEqual(payload["reason"], "ok")
        phases = payload["phases"]
        self.assertEqual(tuple(phases.keys()), PHASES)
        for name in PHASES:
            self.assertIsInstance(phases[name], (int, float), name)
            self.assertGreaterEqual(phases[name], 0.0, name)
        self.assertGreaterEqual(phases["gate"], GATE_FLOOR, phases)
        self.assertGreaterEqual(phases["agent"], 0.25, phases)
        self.assertGreaterEqual(phases["review"], 0.2, phases)
        self.assertGreater(phases["worktree"], 0.0, phases)
        self.assertGreater(phases["preflight"], 0.0, phases)
        self.assertGreater(phases["commit"], 0.0, phases)
        self.assertEqual(self._count(), 4, payload)
        self.assertGreaterEqual(payload["wall_seconds"], phases["gate"])
        self.assertLessEqual(sum(phases.values()), payload["wall_seconds"] + 0.05)

    def test_red_gate_still_records_time_for_the_gates_that_ran(self) -> None:
        # Fail: a red gate skips the receipt phases, so a slow failure looks free.
        # Recover: the two gates that ran are timed, and the run stays FAIL.
        proc = self._build(1, [])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._payload()
        self.assertEqual(payload["status"], "FAIL")
        self.assertEqual(payload["reason"], "tests")
        self.assertIsNone(payload["branch"])
        self.assertGreaterEqual(payload["phases"]["gate"], 0.6, payload["phases"])
        self.assertEqual(self._count(), 2, payload)
        self.assertLess(payload["phases"]["review"], 0.05, payload["phases"])

    def test_skipped_review_still_runs_four_gates(self) -> None:
        # Fail: --no-review also skips the flake gate or the commit recheck.
        # Recover: review seconds stay 0 and the gate still runs four times.
        proc = self._build(0, ["--no-review"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._payload()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertEqual(payload["review"]["verdict"], "skipped")
        self.assertEqual(payload["phases"]["review"], 0.0, payload["phases"])
        self.assertGreaterEqual(payload["phases"]["gate"], GATE_FLOOR, payload["phases"])
        self.assertEqual(self._count(), 4, payload)
