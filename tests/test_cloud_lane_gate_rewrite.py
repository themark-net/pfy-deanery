"""Exit test for lane C3 (sandcastle-grok batch cloud-hardening-1103)."""

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


class GateRewriteIsNotCommitted(_Base):
    def test_gate_that_rewrites_the_tree_fails_gate_rewrote_without_a_branch(self) -> None:
        grok = _write_exe(self.side / "grok.py",
            "#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n" + REVIEW_OK +
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n")
        gate = _write_exe(self.side / "gate.py",
            "#!/usr/bin/env python3\nfrom pathlib import Path\n"
            "if Path('kept.py').exists():\n"
            "    Path('kept.py').write_text('value = 999\\n', encoding='utf-8')\n"
            "print('GATE-OK')\n")
        head = _git(self.repo, "rev-parse", "HEAD").stdout.strip()
        p = _run(self.argv("add kept value 1", grok, gate, "r"), self.repo, timeout=40)
        self.assertEqual(p.returncode, 1, (p.stdout or "") + (p.stderr or ""))
        r = self.receipt("r")
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["reason"], "gate-rewrote")
        self.assertEqual(r["exit_code"], 1)
        self.assertIsNone(r["commit"])
        self.assertIsNone(r["branch"])
        self.assertIn("only check, not write files", r["recovery"])
        self.assertIn("gate", r["recovery"].lower())
        self.assertNotIn("--local", r["recovery"])
        self.assertEqual(_git(self.repo, "rev-parse", "HEAD").stdout.strip(), head)
        self.assertNotIn("\ncloud/", "\n" + _git(self.repo, "branch", "--list").stdout)

    def test_gate_that_only_checks_still_passes(self) -> None:
        grok = _write_exe(self.side / "grok.py",
            "#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n" + REVIEW_OK +
            "Path('kept.py').write_text('value = 1\\n', encoding='utf-8')\n")
        gate = _write_exe(self.side / "gate.py", "#!/usr/bin/env python3\nprint('GATE-OK')\n")
        p = _run(self.argv("add kept value 1", grok, gate, "r"), self.repo, timeout=40)
        self.assertEqual(p.returncode, 0, (p.stdout or "") + (p.stderr or ""))
        self.assertEqual(self.receipt("r")["reason"], "ok")


if __name__ == "__main__":
    unittest.main()
