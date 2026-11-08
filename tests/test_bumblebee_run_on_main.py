import pathlib
import subprocess
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


if __name__ == "__main__":
    unittest.main()
