import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "hiroute" / "run-on-main.sh"


class HirouteReceiptOnMainTest(unittest.TestCase):
    def test_non_ancestor_writes_nothing(self):
        self.assertTrue(SCRIPT.is_file(), "run-on-main.sh missing")
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
            cwd=ROOT,
        )
        dest = pathlib.Path(tempfile.mkdtemp()) / "receipt.json"
        proc = subprocess.run(
            ["bash", str(SCRIPT), str(dest)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if ancestor.returncode == 0:
            self.skipTest("HEAD is already an ancestor of origin/main")
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
