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


def make_repo(td: Path) -> Path:
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
    return repo


class LoopWorktreeBehaviorTest(unittest.TestCase):
    def test_second_run_resets_edits_and_keeps_tmp(self):
        self.assertTrue(SCRIPT.is_file(), "loop_worktree.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = make_repo(td)
            (repo / "README").write_text("repo-dirty\n")
            (repo / "repo-stray").write_text("stay\n")
            wt = td / "wt"
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            first = subprocess.run(
                ["bash", str(SCRIPT), "--wt", str(wt), "--", "true"],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            (wt / "README").write_text("dirty\n")
            (wt / "stray.txt").write_text("gone\n")
            (wt / "tmp").mkdir()
            (wt / "tmp" / "keep").write_text("hold\n")
            second = subprocess.run(
                [
                    "bash",
                    str(SCRIPT),
                    "--wt",
                    str(wt),
                    "--",
                    "bash",
                    "-c",
                    "test ! -e stray.txt && test -f tmp/keep && grep -qx x README",
                ],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertEqual((wt / "tmp" / "keep").read_text(), "hold\n")
            self.assertEqual((repo / "README").read_text(), "repo-dirty\n")
            self.assertEqual((repo / "repo-stray").read_text(), "stay\n")

    def test_refuses_when_dir_is_repo(self):
        self.assertTrue(SCRIPT.is_file(), "loop_worktree.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = make_repo(td)
            (repo / "README").write_text("repo-dirty\n")
            marker = td / "ran"
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            r = subprocess.run(
                ["bash", str(SCRIPT), "--wt", str(repo), "--", "touch", str(marker)],
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("refusing", (r.stdout + r.stderr).lower())
            self.assertFalse(marker.exists())
            self.assertEqual((repo / "README").read_text(), "repo-dirty\n")

    def test_refuses_dir_that_is_not_our_worktree(self):
        self.assertTrue(SCRIPT.is_file(), "loop_worktree.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = make_repo(td)
            other = td / "other"
            subprocess.check_call([REAL_GIT, "init", "-b", "main", str(other)])
            git(other, "config", "user.email", "t@example.com")
            git(other, "config", "user.name", "t")
            (other / "README").write_text("keep\n")
            git(other, "add", "README")
            git(other, "commit", "-m", "other")
            (other / "README").write_text("dirty-other\n")
            marker = td / "ran"
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            r = subprocess.run(
                ["bash", str(SCRIPT), "--wt", str(other), "--", "touch", str(marker)],
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
            )
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("not a worktree", (r.stdout + r.stderr).lower())
            self.assertFalse(marker.exists())
            self.assertEqual((other / "README").read_text(), "dirty-other\n")

    def test_lock_is_held_while_the_command_runs(self):
        self.assertTrue(SCRIPT.is_file(), "loop_worktree.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = make_repo(td)
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            r = subprocess.run(
                [
                    "bash",
                    str(SCRIPT),
                    "--wt",
                    str(td / "wt"),
                    "--",
                    "flock",
                    "-n",
                    "../loop-worktree.lock",
                    "true",
                ],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
