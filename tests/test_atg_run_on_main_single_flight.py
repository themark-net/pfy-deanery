import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/atomic-task-graph-atg/run-on-main.sh"
MARKER = Path("/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/atomic-task-graph-atg.dispatched")


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


if __name__ == "__main__":
    unittest.main()
