"""Exit test for lane C1 (sandcastle-grok batch cloud-hardening-1103)."""

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


class SecondCloudBuildIsBusy(_Base):
    def test_second_build_on_one_repo_exits_build_busy_before_grok(self) -> None:
        ready = self.side / "ready"
        second_marker = self.side / "second-started"
        grok_a = _write_exe(self.side / "grok-a.py",
            "#!/usr/bin/env python3\nimport os, sys, time\nfrom pathlib import Path\n" + REVIEW_OK +
            "Path(%r).write_text(str(os.getpid()), encoding='utf-8')\n"
            "time.sleep(6)\n"
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n" % str(ready))
        grok_b = _write_exe(self.side / "grok-b.py",
            "#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n" + REVIEW_OK +
            "Path(%r).write_text('yes', encoding='utf-8')\n"
            "Path('beta.py').write_text('value = 1\\n', encoding='utf-8')\n" % str(second_marker))
        gate = _write_exe(self.side / "gate.py", "#!/usr/bin/env python3\nprint('GATE-OK')\n")
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        self.proc = subprocess.Popen(self.argv("add alpha", grok_a, gate, "receipt-a"), cwd=str(self.repo),
                                     env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     start_new_session=True)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and not ready.exists() and self.proc.poll() is None:
            time.sleep(0.05)
        self.assertTrue(ready.exists(), "first grok did not start")
        second = _run(self.argv("add beta", grok_b, gate, "receipt-b"), self.repo, timeout=20)
        text = (second.stdout or "") + (second.stderr or "")
        self.assertEqual(second.returncode, 1, text)
        b = self.receipt("receipt-b")
        self.assertEqual(b["reason"], "build-busy")
        self.assertEqual(b["exit_code"], 1)
        self.assertIsNone(b["commit"])
        self.assertIn("Mark:", b["recovery"])
        self.assertNotIn("--local", b["recovery"])
        self.assertFalse(second_marker.exists(), "the busy build started grok")
        out, err = self.proc.communicate(timeout=30)
        self.assertEqual(self.proc.returncode, 0, (out or "") + (err or ""))
        a = self.receipt("receipt-a")
        self.assertEqual(a["reason"], "ok")
        names = _git(self.repo, "ls-tree", "-r", "--name-only", a["commit"]).stdout
        self.assertIn("kept.py", names)
        self.assertNotIn("beta.py", names)
        self.assertEqual(_git(self.repo, "branch", "--list").stdout.count("cloud/"), 1)
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)

    def test_builds_one_after_another_both_pass(self) -> None:
        grok = _write_exe(self.side / "grok.py",
            "#!/usr/bin/env python3\nimport sys, time\nfrom pathlib import Path\n" + REVIEW_OK +
            "Path('one%d.py' % int(time.time() * 1000)).write_text('v = 1\\n', encoding='utf-8')\n")
        gate = _write_exe(self.side / "gate.py", "#!/usr/bin/env python3\nprint('GATE-OK')\n")
        for n in ("r1", "r2"):
            p = _run(self.argv("add file " + n, grok, gate, n), self.repo, timeout=40)
            self.assertEqual(p.returncode, 0, (p.stdout or "") + (p.stderr or ""))
            self.assertEqual(self.receipt(n)["reason"], "ok")


if __name__ == "__main__":
    unittest.main()
