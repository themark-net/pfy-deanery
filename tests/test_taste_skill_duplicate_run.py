import os
import subprocess
import tempfile
import time
import unittest


class TestTasteSkillDuplicateRun(unittest.TestCase):
    def test_second_start_exits_2_without_receipt(self):
        script = "eval/integrate/taste-skill/run-on-main.sh"
        lock_path = "eval/integrate/taste-skill/.run.lock"
        self.assertTrue(os.path.isfile(script))
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        holder = subprocess.Popen(
            ["flock", "-n", lock_path, "sleep", "20"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        fd, receipt = tempfile.mkstemp(prefix="taste-receipt-", suffix=".json")
        os.close(fd)
        os.unlink(receipt)
        try:
            time.sleep(0.2)
            proc = subprocess.run(
                ["bash", script, receipt],
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(proc.returncode, 2)
            self.assertFalse(os.path.exists(receipt))
            text = open(script, encoding="utf-8").read()
            self.assertIn("taste-skill-ff", text)
            self.assertNotIn("git push", text)
        finally:
            holder.terminate()
            holder.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
