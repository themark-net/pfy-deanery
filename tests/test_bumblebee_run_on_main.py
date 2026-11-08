import os
import pathlib
import subprocess
import tempfile
import unittest


class BumblebeeRunOnMainTest(unittest.TestCase):
    def test_non_ancestor_writes_no_receipt(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        script = root / "eval" / "integrate" / "bumblebee" / "run-on-main.sh"
        self.assertTrue(script.is_file(), "run-on-main.sh is missing")
        text = script.read_text(encoding="utf-8")
        self.assertIn("pipeline", text)
        ancestor = subprocess.call(
            ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
            cwd=root,
        )
        if ancestor == 0:
            self.skipTest("HEAD is already on origin/main")
        receipt = root / "eval" / "integrate" / "bumblebee" / "receipt.json.not-main"
        if receipt.exists():
            receipt.unlink()
        proc = subprocess.run(
            ["bash", str(script), str(receipt)],
            cwd=root,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(receipt.exists())

    def test_refused_run_does_not_claim_marker(self):
        root = pathlib.Path(__file__).resolve().parents[1]
        script = root / "eval" / "integrate" / "bumblebee" / "run-on-main.sh"
        ancestor = subprocess.call(
            ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
            cwd=root,
        )
        if ancestor == 0:
            self.skipTest("HEAD is already on origin/main")
        with tempfile.TemporaryDirectory() as tmp:
            marker = pathlib.Path(tmp) / "bumblebee.dispatched"
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
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(receipt.exists())
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
