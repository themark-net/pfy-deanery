import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path("eval/integrate/codebase-memory-mcp/run-on-main.sh")
MARKER = "/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/codebase-memory-mcp.dispatched"


class DoubleRunLockTest(unittest.TestCase):
    def test_second_start_exits_2_without_receipt(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(MARKER, text)
        self.assertIn("exit 2", text)
        self.assertIn("flock", text)
        comment = "\n".join(line for line in text.splitlines() if line.strip().startswith("#"))
        self.assertIn(MARKER, comment)
        self.assertIn("flock", comment)


class DoubleRunLockBehaviorTest(unittest.TestCase):
    def _run(self, marker: Path | None, receipt: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PFY_CODEBASE_MEMORY"] = "/no/such/codebase-memory-mcp"
        if marker is None:
            env["PFY_CBM_LANE_MARKER"] = str(receipt.parent / "missing-marker")
        else:
            env["PFY_CBM_LANE_MARKER"] = str(marker)
        return subprocess.run(
            ["bash", str(ROOT / SCRIPT), str(receipt)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_foreign_marker_exits_2_without_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            marker = tmp_path / "lane.dispatched"
            marker.write_text("pid 99999999\n", encoding="utf-8")
            receipt = tmp_path / "receipt.json"
            proc = self._run(marker, receipt)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("already dispatched", proc.stderr)

    def test_admitted_lane_marker_does_not_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            marker = tmp_path / "lane.dispatched"
            marker.write_text("pid %s\n" % os.getpid(), encoding="utf-8")
            receipt = tmp_path / "receipt.json"
            proc = self._run(marker, receipt)
            self.assertNotEqual(proc.returncode, 2, proc.stderr)
            self.assertFalse(receipt.exists())

    def test_missing_marker_is_not_a_second_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / "receipt.json"
            proc = self._run(None, receipt)
            self.assertNotEqual(proc.returncode, 2, proc.stderr)
            self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
