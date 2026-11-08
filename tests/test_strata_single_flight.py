import os
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "strata" / "run-on-main.sh"
MARKER = "/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/strata.dispatched"


def _run(marker_text, receipt):
    env = os.environ.copy()
    env["PFY_STRATA_LANE_MARKER"] = str(receipt.parent / "marker")
    (receipt.parent / "marker").write_text(marker_text, encoding="utf-8")
    return subprocess.run(
        ["bash", str(SCRIPT), str(receipt)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )


class StrataSingleFlightTest(unittest.TestCase):
    def test_second_start_exits_2_and_names_flock(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn(MARKER, text)
        self.assertIn("exit 2", text)
        self.assertIn("flock", text)

    def test_usage_exits_2(self):
        proc = subprocess.run(
            ["bash", str(SCRIPT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 2, proc.stderr)

    def test_foreign_marker_exits_2_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            receipt = pathlib.Path(raw) / "receipt.json"
            proc = _run("pid 1\n", receipt)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("already dispatched", proc.stderr)

    def test_admitted_lane_is_not_a_second_start(self):
        with tempfile.TemporaryDirectory() as raw:
            receipt = pathlib.Path(raw) / "receipt.json"
            proc = _run(f"pid {os.getpid()}\n", receipt)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("no receipt", proc.stderr)


if __name__ == "__main__":
    unittest.main()
