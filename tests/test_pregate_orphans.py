"""Pregate must remember a run's pids after they chdir, and still signal them if reparented.

How this fails: a pid is judged only by its current cwd and argv, so a daemon
that leaves the run root disappears, and own_child refuses to signal it once
ppid is 1.
How we recover: record the pid while it was under the root, report it as
escaped while it is alive, and return reparented pids from signal_pids.
scripts/pregate.sh must call that helper. A planted prefix (/work/run-evil)
must not count as inside /work/run.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import pregate_orphans as po  # noqa: E402


class PregateOrphanTests(unittest.TestCase):
    def test_cwd_or_argv_under_root_is_tracked(self) -> None:
        roots = ["/work/run", "/work/scratch"]
        self.assertTrue(po.tracked("/work/run", "sleep 1", roots))
        self.assertTrue(po.tracked("/work/run/sub", "sleep 1", roots))
        self.assertTrue(po.tracked("/other", "python /work/scratch/job.py", roots))
        self.assertTrue(po.tracked("/other", "/work/run", roots))
        self.assertFalse(po.tracked("/other", "sleep 1", roots))
        self.assertFalse(po.tracked("/work/run-evil", "sleep 1", roots))
        self.assertFalse(po.tracked("/other", "runtime", roots))

    def test_chdir_keeps_the_pid_as_escaped(self) -> None:
        roots = ["/work/run"]
        seen: set[int] = set()
        po.note(seen, 10, "/work/run/sub", "sleep 1", roots)
        self.assertEqual(seen, {10})
        escaped = po.escaped(seen, {10: ("/var/empty", "sleep 1")}, roots)
        self.assertEqual(escaped, [10])

    def test_never_recorded_and_dead_pids_are_not_escaped(self) -> None:
        roots = ["/work/run"]
        self.assertEqual(po.escaped(set(), {10: ("/var/empty", "sleep")}, roots), [])
        seen = {10}
        self.assertEqual(po.escaped(seen, {}, roots), [])
        # Still under the root: the existing cwd check reports it. Not escaped.
        self.assertEqual(
            po.escaped({10}, {10: ("/work/run/sub", "sleep")}, roots),
            [],
        )

    def test_reparented_pid_stays_in_the_signal_list(self) -> None:
        # ppid 1 means the process left this pregate. own_child would skip it.
        got = po.signal_pids([42, 7], {42: 1, 7: 100}, 100)
        self.assertEqual(got, [42])

    def test_pregate_sh_calls_the_helper(self) -> None:
        text = (ROOT / "scripts" / "pregate.sh").read_text(encoding="utf-8")
        calls = [
            line
            for line in text.splitlines()
            if "pregate_orphans.py" in line and not line.strip().startswith("#")
        ]
        self.assertTrue(calls, "scripts/pregate.sh never calls pregate_orphans.py")


if __name__ == "__main__":
    unittest.main()
