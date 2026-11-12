import subprocess
import sys
import textwrap
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestOverlappingBuildLock(unittest.TestCase):
    def test_live_holder_blocks_and_dead_pid_is_reclaimed(self):
        from pfylib.review_chunks import BuildAlreadyRunning, acquire_repo_lock

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.check_call(["git", "init"], cwd=repo, stdout=subprocess.DEVNULL)
            holder = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    textwrap.dedent(
                        """
                        import sys, time
                        sys.path.insert(0, sys.argv[1])
                        from pfylib.review_chunks import acquire_repo_lock
                        lock = acquire_repo_lock(sys.argv[2])
                        print("held", flush=True)
                        time.sleep(30)
                        lock.release()
                        """
                    ),
                    str(ROOT),
                    str(repo),
                ],
                stdout=subprocess.PIPE,
                text=True,
            )
            try:
                line = holder.stdout.readline()
                self.assertTrue(line.startswith("held"), line)
                with self.assertRaises(BuildAlreadyRunning) as ctx:
                    acquire_repo_lock(str(repo))
                self.assertEqual(ctx.exception.status, "build-already-running")
                self.assertIn(str(holder.pid), str(ctx.exception))
            finally:
                holder.terminate()
                holder.wait(timeout=5)
            lock = acquire_repo_lock(str(repo))
            lock.release()
