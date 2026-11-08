import os
import subprocess
import tempfile
import unittest


class TestTasteSkillReceiptGate(unittest.TestCase):
    def test_non_ancestor_writes_no_receipt(self):
        script = "eval/integrate/taste-skill/run-on-main.sh"
        self.assertTrue(os.path.isfile(script))
        check = subprocess.run(
            ["git", "merge-base", "--is-ancestor", "HEAD", "origin/main"],
            capture_output=True,
            text=True,
        )
        if check.returncode == 0:
            self.skipTest("HEAD is an ancestor of origin/main")
        fd, receipt = tempfile.mkstemp(prefix="taste-receipt-", suffix=".json")
        os.close(fd)
        os.unlink(receipt)
        proc = subprocess.run(
            ["bash", script, receipt],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(os.path.exists(receipt))


if __name__ == "__main__":
    unittest.main()
