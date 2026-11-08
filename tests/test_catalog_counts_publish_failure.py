import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOOP = ROOT / "scripts" / "loop_worktree.sh"
PUBLISH = ROOT / "scripts" / "catalog_counts_publish.sh"
REAL_GIT = shutil.which("git")


def git(cwd, *args):
    r = subprocess.run([REAL_GIT, *args], cwd=cwd, text=True, capture_output=True)
    if r.returncode != 0:
        raise AssertionError(f"git {args} failed: {r.stderr}")
    return r


class PublishFailureTest(unittest.TestCase):
    def test_counts_exit_1_does_not_commit_or_push(self):
        self.assertTrue(LOOP.is_file(), "loop_worktree.sh missing")
        self.assertTrue(PUBLISH.is_file(), "catalog_counts_publish.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            origin = td / "origin.git"
            repo = td / "repo"
            subprocess.check_call([REAL_GIT, "init", "--bare", "-b", "main", str(origin)])
            subprocess.check_call([REAL_GIT, "init", "-b", "main", str(repo)])
            git(repo, "config", "user.email", "t@example.com")
            git(repo, "config", "user.name", "t")
            (repo / "scripts").mkdir()
            (repo / "scripts" / "catalog_counts.py").write_text("import sys\nsys.exit(1)\n")
            pub = repo / "scripts" / "catalog_counts_publish.sh"
            pub.write_text(PUBLISH.read_text())
            pub.chmod(pub.stat().st_mode | stat.S_IEXEC)
            (repo / "README").write_text("x\n")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "fixture")
            git(repo, "remote", "add", "origin", str(origin))
            git(repo, "push", "-u", "origin", "main")
            before = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "rev-parse", "refs/heads/main"], text=True
            ).strip()
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            r = subprocess.run(
                ["bash", str(LOOP), "--wt", str(td / "wt"), "--", "scripts/catalog_counts_publish.sh"],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            after = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "rev-parse", "refs/heads/main"], text=True
            ).strip()
            log = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "log", "--format=%s"], text=True
            )
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertEqual(before, after)
            self.assertNotIn("catalog: regenerate counts", log)
