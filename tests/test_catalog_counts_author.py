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


class AuthorTest(unittest.TestCase):
    def test_commit_identity_is_catalog_loop(self):
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
            (repo / "data" / "stages").mkdir(parents=True)
            (repo / "pipelines" / "catalog").mkdir(parents=True)
            (repo / "data" / "stages" / "_registry.json").write_text("{}\n")
            (repo / "pipelines" / "catalog" / "dashboard.latest.md").write_text("old\n")
            (repo / "pipelines" / "catalog" / "counts.latest.json").write_text("{}\n")
            (repo / "scripts" / "catalog_counts.py").write_text(
                "from pathlib import Path\n"
                "Path('data/stages/_registry.json').write_text('{\"coverage\": 1}\\n')\n"
                "Path('pipelines/catalog/dashboard.latest.md').write_text('new\\n')\n"
                "Path('pipelines/catalog/counts.latest.json').write_text('{\"n\": 1}\\n')\n"
            )
            pub = repo / "scripts" / "catalog_counts_publish.sh"
            pub.write_text(PUBLISH.read_text())
            pub.chmod(pub.stat().st_mode | stat.S_IEXEC)
            git(repo, "add", ".")
            git(repo, "commit", "-m", "fixture")
            git(repo, "remote", "add", "origin", str(origin))
            git(repo, "push", "-u", "origin", "main")
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            r = subprocess.run(
                ["bash", str(LOOP), "--wt", str(td / "wt"), "--", "scripts/catalog_counts_publish.sh"],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            ident = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "log", "-1", "--format=%an%n%ae%n%cn%n%ce"],
                text=True,
            ).splitlines()
            self.assertEqual(
                ident,
                ["catalog-loop", "catalog-loop@localhost", "catalog-loop", "catalog-loop@localhost"],
            )
