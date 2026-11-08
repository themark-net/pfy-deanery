import os
import pathlib
import stat
import subprocess
import tempfile
import textwrap
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "hiroute" / "run-on-main.sh"


class HirouteOfflineFailClosedTest(unittest.TestCase):
    def test_missing_binary_writes_no_receipt(self):
        self.assertTrue(SCRIPT.is_file(), "run-on-main.sh missing")
        empty = pathlib.Path(tempfile.mkdtemp())
        dest = empty / "receipt.json"
        env = os.environ.copy()
        env["PATH"] = str(empty)
        env["HIROUTE_BIN"] = str(empty / "hiroute-missing")
        proc = subprocess.run(
            ["/bin/bash", str(SCRIPT), str(dest)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(dest.exists())
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("11434", text)
        self.assertIn("no-listen", text)


if __name__ == "__main__":
    unittest.main()
