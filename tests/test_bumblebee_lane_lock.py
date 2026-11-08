import os
import pathlib
import subprocess
import tempfile
import unittest


class BumblebeeLaneLockTest(unittest.TestCase):
    def test_second_start_exits_2_and_writes_no_receipt(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        script = root / "eval" / "integrate" / "bumblebee" / "run-on-main.sh"
        self.assertTrue(script.is_file(), "run-on-main.sh is missing")
        text = script.read_text(encoding="utf-8")
        self.assertIn("bumblebee-main-ff.lock", text)
        with tempfile.TemporaryDirectory() as tmp:
            marker = pathlib.Path(tmp) / "bumblebee.dispatched"
            marker.write_text("held\n", encoding="utf-8")
            receipt = pathlib.Path(tmp) / "receipt.json"
            env = os.environ.copy()
            env["BUMBLEBEE_LANE_MARKER"] = str(marker)
            proc = subprocess.run(
                ["bash", str(script), str(receipt)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
