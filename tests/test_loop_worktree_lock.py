import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "loop_worktree.sh"


def git(cwd, *args):
    r = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    if r.returncode != 0:
        raise AssertionError(f"git {args} failed: {r.stderr}")
    return r


def make_repo(td: Path) -> Path:
    origin = td / "origin.git"
    repo = td / "repo"
    subprocess.check_call(["git", "init", "--bare", "-b", "main", str(origin)])
    subprocess.check_call(["git", "init", "-b", "main", str(repo)])
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    (repo / "README").write_text("x\n")
    git(repo, "add", "README")
    git(repo, "commit", "-m", "init")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-u", "origin", "main")
    return repo


class BusyLockTest(unittest.TestCase):
    def test_busy_lock_exits_75_without_running(self):
        self.assertTrue(SCRIPT.is_file(), "loop_worktree.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = make_repo(td)
            wt = td / "loop" / "wt"
            wt.parent.mkdir(parents=True)
            lock = wt.parent / "loop-worktree.lock"
            lock.write_text("")
            holder = subprocess.Popen(
                ["flock", "-n", str(lock), "sleep", "60"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                time.sleep(0.3)
                self.assertIsNone(holder.poll(), "could not hold the lock")
                marker = td / "ran"
                env = os.environ.copy()
                env["PFY_LOOP_REPO"] = str(repo)
                try:
                    r = subprocess.run(
                        ["bash", str(SCRIPT), "--wt", str(wt), "--", "bash", "-c", f"touch {marker}"],
                        env=env,
                        text=True,
                        capture_output=True,
                        timeout=8,
                    )
                except subprocess.TimeoutExpired:
                    self.fail("busy lock blocked instead of exiting 75")
                self.assertEqual(r.returncode, 75, r.stdout + r.stderr)
                self.assertFalse(marker.exists())
                self.assertIn("lock", (r.stdout + r.stderr).lower())
            finally:
                holder.kill()
                holder.wait(timeout=5)
