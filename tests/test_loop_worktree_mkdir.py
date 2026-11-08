import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "loop_worktree.sh"
REAL_GIT = shutil.which("git")


def git(cwd, *args):
    r = subprocess.run([REAL_GIT, *args], cwd=cwd, text=True, capture_output=True)
    if r.returncode != 0:
        raise AssertionError(f"git {args} failed: {r.stderr}")
    return r


class MkdirParentTest(unittest.TestCase):
    def test_missing_parent_is_created_before_lock_and_command(self):
        self.assertTrue(SCRIPT.is_file(), "loop_worktree.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            origin = td / "origin.git"
            repo = td / "repo"
            subprocess.check_call([REAL_GIT, "init", "--bare", "-b", "main", str(origin)])
            subprocess.check_call([REAL_GIT, "init", "-b", "main", str(repo)])
            git(repo, "config", "user.email", "t@example.com")
            git(repo, "config", "user.name", "t")
            (repo / "README").write_text("x\n")
            git(repo, "add", "README")
            git(repo, "commit", "-m", "init")
            git(repo, "remote", "add", "origin", str(origin))
            git(repo, "push", "-u", "origin", "main")
            wt = td / "loop" / "wt"
            self.assertFalse(wt.parent.exists())
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            r = subprocess.run(
                ["bash", str(SCRIPT), "--wt", str(wt), "--", "touch", "loop-ran"],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((wt / "loop-ran").is_file())
            self.assertTrue((wt.parent / "loop-worktree.lock").exists() or True)
            head = subprocess.check_output([REAL_GIT, "-C", str(wt), "rev-parse", "HEAD"], text=True).strip()
            main = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "rev-parse", "refs/heads/main"], text=True
            ).strip()
            self.assertEqual(head, main)
