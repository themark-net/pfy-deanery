"""R4: lock and snapshot behavior, tested by running the real runner."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

from tests.test_cloud_lane_busy import REVIEW_OK, _Base
HEAD = "#!/usr/bin/env python3\nimport os, sys\nfrom pathlib import Path\n"
from tests.test_pfy_build_cloud import CLOUD, _git, _run, _write_exe


class RunnerWithoutFcntl(_Base):
    """fcntl is made unimportable (sys.modules entry None), not just shadowed."""

    BLOCK = "import sys; sys.modules['fcntl'] = None\n"

    def launcher(self) -> Path:
        path = self.side / "nofcntl_launch.py"
        path.write_text(
            self.BLOCK + "import runpy\nsys.argv = sys.argv[1:]\nrunpy.run_path(sys.argv[0], run_name='__main__')\n",
            encoding="utf-8",
        )
        return path

    def test_fcntl_is_really_blocked_in_the_launcher(self) -> None:
        proc = subprocess.run([sys.executable, "-c", self.BLOCK + "import fcntl"], capture_output=True, text=True, timeout=30)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("fcntl", proc.stderr)

    def test_runner_module_loads_without_fcntl(self) -> None:
        code = self.BLOCK + "import importlib.util as u; s = u.spec_from_file_location('m', %r); m = u.module_from_spec(s); s.loader.exec_module(m); print('LOADED')" % str(CLOUD)
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60)
        self.assertIn("LOADED", proc.stdout, proc.stderr[-1500:])

    def test_build_without_fcntl_runs_unlocked_and_passes(self) -> None:
        grok = _write_exe(self.side / "grok.py", HEAD + REVIEW_OK + "Path('k.py').write_text('k = 1\\n')\n")
        gate = _write_exe(self.side / "gate.py", HEAD + "print('ok')\n")
        argv = self.argv("add k", grok, gate, "r")
        argv[1:1] = [str(self.launcher())]
        proc = _run(argv, self.repo, timeout=90)
        text = (proc.stdout or "") + (proc.stderr or "")
        r = self.receipt("r")
        self.assertNotIn("Traceback", text, text[-1500:])
        self.assertEqual((r.get("status"), r.get("reason")), ("PASS", "ok"), text[-1500:])
        self.assertIn("without the repo lock", text)


class LockIsHeldForTheWholeRunAndReleased(_Base):
    def test_lock_is_free_again_after_a_build(self) -> None:
        grok = _write_exe(self.side / "grok.py", HEAD + REVIEW_OK + "Path('k.py').write_text('k = 1\\n')\n")
        gate = _write_exe(self.side / "gate.py", HEAD + "print('ok')\n")
        first = _run(self.argv("add k", grok, gate, "r1"), self.repo, timeout=90)
        self.assertEqual(first.returncode, 0, (first.stdout or "")[-1500:])
        probe = (
            "import fcntl, os, sys\nfd = os.open(sys.argv[1], os.O_RDWR)\n"
            "fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\nprint('FREE')\n"
        )
        lock = self.repo / "tmp" / "cloud-build.lock"
        if lock.exists():
            out = subprocess.run([sys.executable, "-c", probe, str(lock)], capture_output=True, text=True, timeout=30)
            self.assertIn("FREE", out.stdout, out.stderr)

    def test_lock_is_held_while_the_gate_runs(self) -> None:
        probe = (
            "import fcntl\nfd = os.open('%s', os.O_RDWR)\n"
            "try:\n    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n    Path('%s').write_text('FREE')\n"
            "except BlockingIOError:\n    Path('%s').write_text('HELD')\nprint('ok')\n"
        ) % (self.repo / "tmp" / "cloud-build.lock", self.side / "seen", self.side / "seen")
        grok = _write_exe(self.side / "grok.py", HEAD + REVIEW_OK + "Path('k.py').write_text('k = 1\\n')\n")
        gate = _write_exe(self.side / "gate.py", HEAD + probe)
        proc = _run(self.argv("add k", grok, gate, "r"), self.repo, timeout=90)
        self.assertEqual(proc.returncode, 0, (proc.stdout or "")[-1500:])
        self.assertEqual((self.side / "seen").read_text(), "HELD")


if __name__ == "__main__":
    unittest.main()
