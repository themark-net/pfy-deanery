import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "headson" / "run-on-main.sh"
REAL_MARKER = Path("/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/headson.dispatched")


def _run(marker: Path | None, receipt: Path):
    env = os.environ.copy()
    env.pop("HSON_BIN", None)
    if marker is None:
        env["HSON_LANE_MARKER"] = str(receipt.parent / "missing-marker")
    else:
        env["HSON_LANE_MARKER"] = str(marker)
    env["TMPDIR"] = str(receipt.parent)
    return subprocess.run(
        ["bash", str(SCRIPT), str(receipt)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


class TestHeadsonSingleFlight(unittest.TestCase):
    def test_second_start_exits_2_without_new_lock(self):
        script = Path("eval/integrate/headson/run-on-main.sh").read_text()
        self.assertIn(
            "/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/headson.dispatched",
            script,
        )
        self.assertIn("exit 2", script)
        self.assertIn("flock", script.lower())
        self.assertNotIn("model_lock.sh", script)
        self.assertNotIn("git push", script)

    def test_foreign_marker_exits_2_and_writes_no_receipt(self):
        before = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "marker"
            marker.write_text("pid 1\n", encoding="utf-8")
            receipt = Path(tmp) / "receipt.json"
            proc = _run(marker, receipt)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertEqual(marker.read_text(encoding="utf-8"), "pid 1\n")
        after = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        self.assertEqual(before, after)

    def test_own_pid_marker_is_the_admitted_lane(self):
        before = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "marker"
            marker.write_text("pid %s\n" % os.getpid(), encoding="utf-8")
            receipt = Path(tmp) / "receipt.json"
            proc = _run(marker, receipt)
            self.assertNotEqual(proc.returncode, 2, proc.stderr)
            if proc.returncode != 0:
                self.assertFalse(receipt.exists())
            self.assertEqual(marker.read_text(encoding="utf-8"), "pid %s\n" % os.getpid())
        after = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        self.assertEqual(before, after)

    def test_missing_marker_is_not_created(self):
        before = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing-marker"
            receipt = Path(tmp) / "receipt.json"
            proc = _run(None, receipt)
            self.assertFalse(missing.exists())
            if proc.returncode != 0:
                self.assertFalse(receipt.exists())
            self.assertNotEqual(proc.returncode, 2, proc.stderr)
        after = REAL_MARKER.read_bytes() if REAL_MARKER.is_file() else None
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
