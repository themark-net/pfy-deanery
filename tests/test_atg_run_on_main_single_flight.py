import os
import stat
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/atomic-task-graph-atg/run-on-main.sh"
MARKER = (Path.home() / "DEVELOP/pfy-mentat/tmp/integrate2/atomic-task-graph-atg.dispatched")


class AtgSingleFlightTest(unittest.TestCase):
    def test_script_names_receipt_flock(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("flock", text)
        self.assertIn("receipt", text)
        self.assertNotIn("git push", text)

    def test_second_start_exits_2_when_marker_present(self):
        if not SCRIPT.is_file():
            self.fail("run-on-main.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            env = os.environ.copy()
            env["ATG_LANE_MARKER"] = str(MARKER)
            # The script must honor an injected marker path when the real marker
            # is absent in CI, and must not create the owner-checkout path.
            probe = Path(tmp) / "atomic-task-graph-atg.dispatched"
            probe.write_text("busy\n", encoding="utf-8")
            env["ATG_LANE_MARKER"] = str(probe)
            proc = subprocess.run(
                ["bash", str(SCRIPT), str(receipt)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertFalse(MARKER.exists() and MARKER.stat().st_mtime > probe.stat().st_mtime)

    def test_held_receipt_flock_exits_2_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            receipt = td / "receipt.json"
            offline = td / "slow_ok"
            offline.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/sh
                    sleep 5
                    echo offline
                    """
                ),
                encoding="utf-8",
            )
            offline.chmod(0o755)
            env = os.environ.copy()
            env["ATG_OFFLINE_CHECK"] = str(offline)
            env["ATG_SKIP_MAIN_ANCESTOR"] = "1"
            env.pop("ATG_FORCE_NOT_ANCESTOR", None)
            env.pop("ATG_LANE_MARKER", None)
            first = subprocess.Popen(
                ["bash", str(SCRIPT), str(receipt)],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            lock = Path(str(receipt) + ".lock")
            try:
                seen = False
                for _ in range(100):
                    if lock.exists():
                        seen = True
                        break
                    if first.poll() is not None:
                        break
                    time.sleep(0.05)
                self.assertTrue(seen, "receipt lock was not taken")
                second = subprocess.run(
                    ["bash", str(SCRIPT), str(receipt)],
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertEqual(second.returncode, 2, second.stderr)
                self.assertIn("receipt-path flock is held", second.stderr)
                self.assertFalse(receipt.exists())
                out, err = first.communicate(timeout=10)
                self.assertEqual(first.returncode, 0, err)
                self.assertTrue(receipt.is_file(), err or out)
                self.assertFalse(lock.exists())
            finally:
                if first.poll() is None:
                    first.kill()
                    first.communicate(timeout=5)


if __name__ == "__main__":
    unittest.main()
