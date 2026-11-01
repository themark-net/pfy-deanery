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
import signal
import subprocess
import sys
import time
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
# These sleeps are the custom --test-cmd path, which stays serial.
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


_INTERVAL_SUITE = """\
import fcntl
import os
import subprocess
import time
import unittest
from pathlib import Path


class DailyGate(unittest.TestCase):
    def test_daily_gate(self):
        start = time.monotonic()
        kind = "extract"
        if Path(".git").exists():
            here = os.path.realpath(os.getcwd())
            top = subprocess.check_output(
                ["git", "rev-parse", "--show-toplevel"], text=True
            ).strip()
            # The recheck extract has its own repo so git cannot walk up
            # to the caller. That directory is still the extract gate.
            if os.path.realpath(top) == here and os.path.basename(here).startswith("recheck-"):
                kind = "extract"
            else:
                subprocess.check_call(["git", "status", "--porcelain"])
                kind = "git"
        time.sleep(0.4)
        end = time.monotonic()
        log = Path(os.environ["PFY_GATE_LOG"])
        with open(log, "a", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.write("%s %s %s %s\\n" % (start, end, os.getpid(), kind))
"""

_SIGNAL_SUITE = """\
import fcntl
import os
import time
import unittest
from pathlib import Path


class DailyGate(unittest.TestCase):
    def test_daily_gate(self):
        log = Path(os.environ["PFY_GATE_LOG"])
        with open(log, "a", encoding="utf-8") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            handle.write(str(os.getpid()) + "\\n")
            handle.flush()
        n = len(log.read_text(encoding="utf-8").split())
        if n <= 1:
            return
        time.sleep(8)
"""


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

    def _build(
        self,
        gate_code: int,
        extra: list[str],
        env: dict | None = None,
        gate_body: str | None = None,
        grok_body: str | None = None,
        proc_timeout: float = 60,
        use_default: bool = False,
    ) -> subprocess.CompletedProcess:
        grok = _write_exe(self.side / "grok.py", grok_body or _grok_script(0.25, 0.30))
        argv = [
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
            "--grok-cmd",
            str(grok),
            "--receipt-dir",
            str(self.receipt_dir),
        ]
        if not use_default:
            gate = _write_exe(
                self.side / "gate.py",
                gate_body or _gate_script(self.counter, GATE_SLEEP, gate_code),
            )
            argv.extend(["--test-cmd", "%s %s" % (sys.executable, gate)])
        argv.extend(extra)
        return _run(argv, self.repo, env=env, timeout=proc_timeout)

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
        # Review overlaps the recheck gate. Each phase keeps its own
        # seconds, so the sum may pass the wall by about that overlap.
        self.assertGreaterEqual(payload["wall_seconds"] + 0.05, phases["gate"])
        self.assertGreaterEqual(payload["wall_seconds"] + 0.05, phases["review"])
        self.assertLessEqual(
            sum(phases.values()),
            payload["wall_seconds"] + min(phases["review"], phases["gate"]) + 0.05,
        )

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
        # before and after. A red custom gate does not start the flake gate.
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
        # No review call, so nothing overlaps the recheck. The sum stays
        # inside the wall.
        self.assertLessEqual(sum(payload["phases"].values()), payload["wall_seconds"] + 0.05)

    def _commit_suite(self, body: str) -> None:
        tests = self.repo / "tests"
        tests.mkdir(exist_ok=True)
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_slow.py").write_text(body, encoding="utf-8")
        added = _git(self.repo, "add", "tests")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "slow gate")
        self.assertEqual(committed.returncode, 0, committed.stderr)

    def _rows(self, log: Path) -> list[tuple[float, float, str]]:
        rows = []
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            start, end, _pid, kind = line.split()
            rows.append((float(start), float(end), kind))
        return rows

    def _pair_count(self, rows: list[tuple[float, float, str]]) -> int:
        found = 0
        for index, left in enumerate(rows):
            for right in rows[index + 1 :]:
                if left[0] < right[1] and right[0] < left[1]:
                    found += 1
        return found

    def test_post_change_gates_overlap_and_all_four_still_run(self) -> None:
        # Fail: the flake gate waits for the first post-change gate, so a
        # long default suite is paid twice on the wall clock.
        # Recover: those two gates overlap, git status runs in each worktree,
        # and the clean extract still runs as its own gate. The extract
        # has a nested git repo so a walk-up cannot see the caller.
        log = self.side / "gate-log"
        self._commit_suite(_INTERVAL_SUITE)
        proc = self._build(
            0,
            ["--no-review"],
            env={"PFY_GATE_LOG": str(log)},
            use_default=True,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        rows = self._rows(log)
        self.assertEqual(len(rows), 4, log.read_text(encoding="utf-8") if log.exists() else text)
        git_rows = sorted((row for row in rows if row[2] == "git"), key=lambda row: row[0])
        extract_rows = [row for row in rows if row[2] == "extract"]
        self.assertEqual(len(git_rows), 3, rows)
        self.assertEqual(len(extract_rows), 1, rows)
        early = git_rows[0]
        later = git_rows[1:]
        for row in later:
            self.assertFalse(early[0] < row[1] and row[0] < early[1], rows)
        self.assertEqual(self._pair_count(later), 1, rows)
        self.assertEqual(self._pair_count(rows), 1, rows)

    def test_serial_switch_keeps_four_gates_without_overlap(self) -> None:
        # Fail: the escape hatch drops a gate, or still overlaps them.
        # Recover: PFY_BUILD_SERIAL_GATES=1 runs the same four gates in order,
        # including git status on the worktrees and the clean extract.
        log = self.side / "gate-log"
        self._commit_suite(_INTERVAL_SUITE)
        proc = self._build(
            0,
            ["--no-review"],
            env={"PFY_BUILD_SERIAL_GATES": "1", "PFY_GATE_LOG": str(log)},
            use_default=True,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        rows = self._rows(log)
        self.assertEqual(len(rows), 4, text + (log.read_text(encoding="utf-8") if log.exists() else ""))
        self.assertEqual(len([row for row in rows if row[2] == "git"]), 3, rows)
        self.assertEqual(len([row for row in rows if row[2] == "extract"]), 1, rows)
        self.assertEqual(self._pair_count(rows), 0, rows)

    def test_signal_during_overlapped_gates_kills_both(self) -> None:
        # Fail: the runner remembers one child, so the second gate keeps
        # sleeping after SIGTERM.
        # Recover: both gate pids are dead and the receipt says interrupted.
        log = self.side / "gate-log"
        self._commit_suite(_SIGNAL_SUITE)
        grok = _write_exe(self.side / "grok.py", _grok_script(0.05, 0.05))
        proc = subprocess.Popen(
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
                "--no-review",
                "--timeout",
                "30",
                "--grok-cmd",
                str(grok),
                "--receipt-dir",
                str(self.receipt_dir),
            ],
            cwd=self.repo,
            env={
                **os.environ,
                "TMPDIR": str(SCRATCH),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PFY_GATE_LOG": str(log),
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        def _stop() -> None:
            if proc.poll() is None:
                try:
                    os.kill(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

        self.addCleanup(_stop)
        deadline = time.monotonic() + 8
        pids: list[int] = []
        while time.monotonic() < deadline:
            if log.exists():
                pids = [
                    int(line)
                    for line in log.read_text(encoding="utf-8").split()
                    if line.strip().isdigit()
                ]
                if len(pids) >= 3:
                    break
            time.sleep(0.05)
        self.assertGreaterEqual(len(pids), 3, "gates did not overlap: %s" % pids)
        os.kill(proc.pid, signal.SIGTERM)
        try:
            out, err = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            _stop()
            self.fail("runner did not exit after SIGTERM")
        text = (out or "") + (err or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._payload()
        self.assertEqual(payload["reason"], "interrupted", text)
        for pid in pids[1:3]:
            gone = time.monotonic() + 2
            alive = True
            while time.monotonic() < gone:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    alive = False
                    break
                time.sleep(0.05)
            self.assertFalse(alive, "gate pid %s still alive" % pid)

    def _tagged(self, log: Path) -> list[tuple[float, float, str]]:
        rows = []
        for line in log.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            start, end, kind = line.split()
            rows.append((float(start), float(end), kind))
        return rows

    def test_review_overlaps_the_recheck_and_four_gates_still_run(self) -> None:
        # Fail: the clean extract waits until review returns, so a long
        # suite is paid again after the model call.
        # Recover: the review call overlaps that extract, and the run
        # still executes four gates.
        log = self.side / "gate-log"
        gate = (
            "#!/usr/bin/env python3\n"
            "import fcntl, os, time\n"
            "from pathlib import Path\n"
            "start = time.monotonic()\n"
            "time.sleep(0.45)\n"
            "end = time.monotonic()\n"
            "log = Path(os.environ['PFY_GATE_LOG'])\n"
            "with open(log, 'a', encoding='utf-8') as handle:\n"
            "    fcntl.flock(handle, fcntl.LOCK_EX)\n"
            "    handle.write('%s %s gate\\n' % (start, end))\n"
            "raise SystemExit(0)\n"
        )
        grok = (
            "#!/usr/bin/env python3\n"
            "import fcntl, os, sys, time\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    start = time.monotonic()\n"
            "    time.sleep(0.55)\n"
            "    end = time.monotonic()\n"
            "    log = Path(os.environ['PFY_GATE_LOG'])\n"
            "    with open(log, 'a', encoding='utf-8') as handle:\n"
            "        fcntl.flock(handle, fcntl.LOCK_EX)\n"
            "        handle.write('%s %s review\\n' % (start, end))\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        )
        proc = self._build(
            0,
            [],
            env={"PFY_GATE_LOG": str(log)},
            gate_body=gate,
            grok_body=grok,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        rows = self._tagged(log)
        gates = sorted((row for row in rows if row[2] == "gate"), key=lambda row: row[0])
        reviews = [row for row in rows if row[2] == "review"]
        self.assertEqual(len(gates), 4, rows)
        self.assertEqual(len(reviews), 1, rows)
        review = reviews[0]
        last = gates[-1]
        earlier = gates[:-1]
        self.assertTrue(review[0] < last[1] and last[0] < review[1], rows)
        for row in earlier:
            self.assertFalse(review[0] < row[1] and row[0] < review[1], rows)
        payload = self._payload()
        self.assertGreaterEqual(payload["phases"]["review"], 0.4, payload["phases"])
        self.assertGreaterEqual(payload["phases"]["gate"], 1.6, payload["phases"])
        self.assertEqual(payload["status"], "PASS", text)

    def test_review_reject_wins_when_the_extract_also_fails(self) -> None:
        # Fail: a red extract overwrites a review reject, or the extract
        # is skipped once review is going to reject.
        # Recover: the extract still runs, and the receipt says
        # review-rejected with no branch.
        ignore = self.repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "helper.py\n", encoding="utf-8")
        added = _git(self.repo, "add", ".gitignore")
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", "ignore helper")
        self.assertEqual(committed.returncode, 0, committed.stderr)
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        marker = self.side / "extract-missed-helper"
        gate = (
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "p = Path(%r)\n"
            "n = int(p.read_text(encoding='utf-8') or '0') if p.exists() else 0\n"
            "p.write_text(str(n + 1), encoding='utf-8')\n"
            "sys.path.insert(0, str(Path('.').resolve()))\n"
            "try:\n"
            "    import kept\n"
            "except Exception as exc:\n"
            "    print('GATE-IMPORT-FAIL %%s' %% exc)\n"
            "    if Path('kept.py').is_file():\n"
            "        Path(%r).write_text('extract-missed-helper\\n', encoding='utf-8')\n"
            "    raise SystemExit(1)\n"
            "print('GATE-OK')\n"
            "raise SystemExit(0)\n" % (str(self.counter), str(marker))
        )
        grok = (
            "#!/usr/bin/env python3\n"
            "import sys\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: reject')\n"
            "    print('reasons: both-failed')\n"
            "    raise SystemExit(0)\n"
            "Path('helper.py').write_text('VALUE = 1\\n', encoding='utf-8')\n"
            "Path('kept.py').write_text('import helper\\nvalue = helper.VALUE\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        )
        proc = self._build(0, [], gate_body=gate, grok_body=grok)
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._payload()
        self.assertEqual(payload["reason"], "review-rejected", text)
        self.assertIsNone(payload["branch"])
        self.assertIsNone(payload["commit"])
        self.assertEqual(self._count(), 4, payload)
        self.assertEqual(marker.read_text(encoding="utf-8"), "extract-missed-helper\n")
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_signal_during_review_and_recheck_kills_both(self) -> None:
        # Fail: the runner tracks the review process and leaves the extract
        # gate sleeping after SIGTERM.
        # Recover: both pids are dead, the receipt says interrupted, and
        # no branch is kept.
        log = self.side / "gate-log"
        gate = (
            "#!/usr/bin/env python3\n"
            "import fcntl, os, time\n"
            "from pathlib import Path\n"
            "here = os.path.realpath(os.getcwd())\n"
            "if not os.path.basename(here).startswith('recheck-'):\n"
            "    raise SystemExit(0)\n"
            "log = Path(os.environ['PFY_GATE_LOG'])\n"
            "with open(log, 'a', encoding='utf-8') as handle:\n"
            "    fcntl.flock(handle, fcntl.LOCK_EX)\n"
            "    handle.write(str(os.getpid()) + '\\n')\n"
            "    handle.flush()\n"
            "time.sleep(8)\n"
            "raise SystemExit(0)\n"
        )
        grok = (
            "#!/usr/bin/env python3\n"
            "import fcntl, os, sys, time\n"
            "from pathlib import Path\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    log = Path(os.environ['PFY_GATE_LOG'])\n"
            "    with open(log, 'a', encoding='utf-8') as handle:\n"
            "        fcntl.flock(handle, fcntl.LOCK_EX)\n"
            "        handle.write(str(os.getpid()) + '\\n')\n"
            "        handle.flush()\n"
            "    time.sleep(8)\n"
            "    print('verdict: accept')\n"
            "    raise SystemExit(0)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n"
        )
        gate_path = _write_exe(self.side / "gate.py", gate)
        grok_path = _write_exe(self.side / "grok.py", grok)
        proc = subprocess.Popen(
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
                "%s %s" % (sys.executable, gate_path),
                "--grok-cmd",
                str(grok_path),
                "--receipt-dir",
                str(self.receipt_dir),
            ],
            cwd=self.repo,
            env={
                **os.environ,
                "TMPDIR": str(SCRATCH),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PFY_GATE_LOG": str(log),
            },
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        def _stop() -> None:
            if proc.poll() is None:
                try:
                    os.kill(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass

        self.addCleanup(_stop)
        deadline = time.monotonic() + 8
        pids: list[int] = []
        while time.monotonic() < deadline:
            if log.exists():
                pids = [
                    int(line)
                    for line in log.read_text(encoding="utf-8").split()
                    if line.strip().isdigit()
                ]
                if len(pids) >= 2:
                    break
            time.sleep(0.05)
        self.assertGreaterEqual(len(pids), 2, "review and recheck did not start: %s" % pids)
        os.kill(proc.pid, signal.SIGTERM)
        try:
            out, err = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            _stop()
            self.fail("runner did not exit after SIGTERM")
        text = (out or "") + (err or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._payload()
        self.assertEqual(payload["reason"], "interrupted", text)
        self.assertIsNone(payload["branch"], text)
        for pid in pids[:2]:
            gone = time.monotonic() + 2
            alive = True
            while time.monotonic() < gone:
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    alive = False
                    break
                time.sleep(0.05)
            self.assertFalse(alive, "pid %s still alive" % pid)

