"""Exit test for lane C2 (sandcastle-grok batch cloud-hardening-1103)."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import unittest

from tests.test_pfy_build_cloud import CLOUD, SCRATCH, _git, _init_repo, _run, _write_exe

REVIEW_OK = (
    "blob = '\\n'.join(sys.argv)\n"
    "if 'PFY-CLOUD-REVIEW' in blob:\n"
    "    print('verdict: accept')\n"
    "    raise SystemExit(0)\n"
)


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        name = self.id().replace(".", "_")
        self.repo = _init_repo(SCRATCH / name)
        self.side = SCRATCH / (name + "-side")
        self.side.mkdir(parents=True, exist_ok=True)
        self.proc = None

    def tearDown(self) -> None:
        proc = self.proc
        if proc is not None and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                proc.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                pass
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def argv(self, task: str, grok, gate, receipt: str, *extra: str) -> list[str]:
        return [sys.executable, str(CLOUD), task, "--repo", str(self.repo), "--retries", "0",
                "--timeout", "30", "--test-cmd", "%s %s" % (sys.executable, gate),
                "--grok-cmd", str(grok), "--receipt-dir", str(self.side / receipt), *extra]

    def receipt(self, receipt: str) -> dict:
        return json.loads((self.side / receipt / "receipt.json").read_text(encoding="utf-8"))


class FinishKeepsForeignPidFile(_Base):
    def test_finish_leaves_a_pid_file_that_names_another_process(self) -> None:
        pid_path = self.repo / "tmp" / "cloud-build.pids.json"
        grok = _write_exe(self.side / "grok.py",
            "#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n" + REVIEW_OK +
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n")
        # The gate runs after grok and after the runner last wrote its own pid,
        # so it stands in for a second build that took over the pid file.
        gate = _write_exe(self.side / "gate.py",
            "#!/usr/bin/env python3\nimport json\nfrom pathlib import Path\n"
            "if Path('kept.py').exists():\n"
            "    Path(%r).write_text(json.dumps({'pid': 999999, 'pgid': 0}), encoding='utf-8')\n"
            "print('GATE-OK')\n" % str(pid_path))
        p = _run(self.argv("add kept", grok, gate, "r", "--no-review"), self.repo, timeout=40)
        self.assertIn(p.returncode, (0, 1), (p.stdout or "") + (p.stderr or ""))
        self.assertTrue(pid_path.is_file(), "finish removed a pid file that names another process")
        self.assertEqual(json.loads(pid_path.read_text(encoding="utf-8"))["pid"], 999999)

    def test_finish_removes_its_own_pid_file(self) -> None:
        pid_path = self.repo / "tmp" / "cloud-build.pids.json"
        grok = _write_exe(self.side / "grok.py",
            "#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n" + REVIEW_OK +
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n")
        gate = _write_exe(self.side / "gate.py", "#!/usr/bin/env python3\nprint('GATE-OK')\n")
        p = _run(self.argv("add kept", grok, gate, "r"), self.repo, timeout=40)
        self.assertEqual(p.returncode, 0, (p.stdout or "") + (p.stderr or ""))
        self.assertFalse(pid_path.exists(), "finish left its own pid file behind")


if __name__ == "__main__":
    unittest.main()
