import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CatalogLoopExclusiveTickTest(unittest.TestCase):
    def test_busy_lock_exits_zero_and_does_not_launch(self):
        state = Path(tempfile.mkdtemp())
        lock = state / "loop.lock"
        lock.write_text("")
        launched = Path(tempfile.mkdtemp()) / "launched"
        stub_dir = Path(tempfile.mkdtemp())
        stub = stub_dir / "systemd-run"
        stub.write_text("#!/bin/sh\ntouch %s\nexit 0\n" % launched)
        stub.chmod(0o755)
        holder = subprocess.Popen(["flock", str(lock), "sleep", "30"])
        try:
            time.sleep(0.3)
            env = os.environ.copy()
            env["PFY_LOOP_STATE"] = str(state)
            env["PFY_LOOP_NO_PUSH"] = "1"
            env["PFY_SYSTEMD_RUN"] = str(stub)
            proc = subprocess.run(
                ["bash", str(ROOT / "scripts" / "catalog_loop.sh")],
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertFalse(launched.exists())
            blob = proc.stdout
            status_path = state / "loop.latest.json"
            if status_path.exists():
                blob += "\n" + status_path.read_text()
            self.assertIn("busy", blob)
        finally:
            holder.kill()
            holder.wait()
