import os
import signal
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
        # New session so finally can reap flock and its sleep child together.
        # Killing only flock leaves sleep holding .run.lock.
        holder = subprocess.Popen(
            ["flock", "-n", lock_path, "sleep", "20"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
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
            with open(script, encoding="utf-8") as handle:
                text = handle.read()
            self.assertIn("taste-skill-ff", text)
            self.assertNotIn("git push", text)
        finally:
            if holder.poll() is None:
                try:
                    os.killpg(holder.pid, signal.SIGTERM)
                except OSError:
                    holder.terminate()
            try:
                holder.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(holder.pid, signal.SIGKILL)
                except OSError:
                    pass
                holder.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
