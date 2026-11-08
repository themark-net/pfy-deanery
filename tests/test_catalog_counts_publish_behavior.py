import os
import shutil
import stat
import subprocess
import tempfile
import textwrap
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


def init_pair(td: Path):
    origin = td / "origin.git"
    repo = td / "repo"
    subprocess.check_call([REAL_GIT, "init", "--bare", "-b", "main", str(origin)])
    subprocess.check_call([REAL_GIT, "init", "-b", "main", str(repo)])
    git(repo, "config", "user.email", "t@example.com")
    git(repo, "config", "user.name", "t")
    return origin, repo


def install_publish(repo: Path, counts_body: str):
    (repo / "scripts").mkdir()
    (repo / "scripts" / "catalog_counts.py").write_text(counts_body)
    pub = repo / "scripts" / "catalog_counts_publish.sh"
    pub.write_text(PUBLISH.read_text())
    pub.chmod(pub.stat().st_mode | stat.S_IEXEC)


def seed_outputs(repo: Path):
    (repo / "data" / "stages").mkdir(parents=True)
    (repo / "pipelines" / "catalog").mkdir(parents=True)
    (repo / "data" / "stages" / "_registry.json").write_text("{}\n")
    (repo / "pipelines" / "catalog" / "dashboard.latest.md").write_text("old\n")
    (repo / "pipelines" / "catalog" / "counts.latest.json").write_text("{}\n")


COUNTS_CHANGE = (
    "from pathlib import Path\n"
    "Path('data/stages/_registry.json').write_text('{\"coverage\": 1}\\n')\n"
    "Path('pipelines/catalog/dashboard.latest.md').write_text('new\\n')\n"
    "Path('pipelines/catalog/counts.latest.json').write_text('{\"n\": 1}\\n')\n"
)

COUNTS_SAME = (
    "from pathlib import Path\n"
    "Path('data/stages/_registry.json').write_text('{}\\n')\n"
    "Path('pipelines/catalog/dashboard.latest.md').write_text('old\\n')\n"
    "Path('pipelines/catalog/counts.latest.json').write_text('{}\\n')\n"
)

COUNTS_STRAY = COUNTS_CHANGE + "Path('stray.txt').write_text('nope\\n')\n"


class PublishBehaviorTest(unittest.TestCase):
    def test_stray_path_exits_3_and_pushes_nothing(self):
        self.assertTrue(LOOP.is_file(), "loop_worktree.sh missing")
        self.assertTrue(PUBLISH.is_file(), "catalog_counts_publish.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            origin, repo = init_pair(td)
            seed_outputs(repo)
            install_publish(repo, COUNTS_STRAY)
            git(repo, "add", ".")
            git(repo, "commit", "-m", "fixture")
            git(repo, "remote", "add", "origin", str(origin))
            git(repo, "push", "-u", "origin", "main")
            before = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "rev-parse", "refs/heads/main"], text=True
            ).strip()
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            wt = td / "wt"
            r = subprocess.run(
                ["bash", str(LOOP), "--wt", str(wt), "--", "scripts/catalog_counts_publish.sh"],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            after = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "rev-parse", "refs/heads/main"], text=True
            ).strip()
            local = subprocess.check_output(
                [REAL_GIT, "-C", str(wt), "log", "-1", "--format=%s"], text=True
            ).strip()
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            self.assertIn("stray.txt", r.stdout + r.stderr)
            self.assertEqual(before, after)
            self.assertEqual(local, "fixture")

    def test_no_push_still_exits_3_on_stray(self):
        self.assertTrue(LOOP.is_file(), "loop_worktree.sh missing")
        self.assertTrue(PUBLISH.is_file(), "catalog_counts_publish.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            origin, repo = init_pair(td)
            seed_outputs(repo)
            install_publish(repo, COUNTS_STRAY)
            git(repo, "add", ".")
            git(repo, "commit", "-m", "fixture")
            git(repo, "remote", "add", "origin", str(origin))
            git(repo, "push", "-u", "origin", "main")
            before = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "rev-parse", "refs/heads/main"], text=True
            ).strip()
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            env["PFY_LOOP_NO_PUSH"] = "1"
            wt = td / "wt"
            r = subprocess.run(
                ["bash", str(LOOP), "--wt", str(wt), "--", "scripts/catalog_counts_publish.sh"],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            after = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "rev-parse", "refs/heads/main"], text=True
            ).strip()
            local = subprocess.check_output(
                [REAL_GIT, "-C", str(wt), "log", "-1", "--format=%s"], text=True
            ).strip()
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            self.assertNotIn("unchanged", r.stdout)
            self.assertEqual(before, after)
            self.assertEqual(local, "fixture")

    def test_unchanged_tree_prints_unchanged(self):
        self.assertTrue(LOOP.is_file(), "loop_worktree.sh missing")
        self.assertTrue(PUBLISH.is_file(), "catalog_counts_publish.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            origin, repo = init_pair(td)
            seed_outputs(repo)
            install_publish(repo, COUNTS_SAME)
            git(repo, "add", ".")
            git(repo, "commit", "-m", "fixture")
            git(repo, "remote", "add", "origin", str(origin))
            git(repo, "push", "-u", "origin", "main")
            before = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "rev-parse", "refs/heads/main"], text=True
            ).strip()
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            env["PFY_LOOP_NO_PUSH"] = "1"
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
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("unchanged", r.stdout)
            self.assertEqual(before, after)

    def test_publish_refuses_repo_toplevel(self):
        self.assertTrue(PUBLISH.is_file(), "catalog_counts_publish.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            _, repo = init_pair(td)
            install_publish(repo, "import sys\nsys.exit(1)\n")
            (repo / "README").write_text("x\n")
            git(repo, "add", ".")
            git(repo, "commit", "-m", "fixture")
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            r = subprocess.run(
                ["bash", str(repo / "scripts" / "catalog_counts_publish.sh")],
                env=env,
                text=True,
                capture_output=True,
                timeout=30,
            )
            log = subprocess.check_output(
                [REAL_GIT, "-C", str(repo), "log", "--format=%s"], text=True
            )
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("refusing", (r.stdout + r.stderr).lower())
            self.assertNotIn("catalog: regenerate counts", log)

    def test_push_rejected_three_times_exits_nonzero_without_force(self):
        self.assertTrue(LOOP.is_file(), "loop_worktree.sh missing")
        self.assertTrue(PUBLISH.is_file(), "catalog_counts_publish.sh missing")
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            origin, repo = init_pair(td)
            seed_outputs(repo)
            install_publish(repo, COUNTS_CHANGE)
            git(repo, "add", ".")
            git(repo, "commit", "-m", "fixture")
            git(repo, "remote", "add", "origin", str(origin))
            git(repo, "push", "-u", "origin", "main")
            before = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "rev-parse", "refs/heads/main"], text=True
            ).strip()
            count = td / "push-count"
            count.write_text("0\n")
            bindir = td / "bin"
            bindir.mkdir()
            wrapper = bindir / "git"
            wrapper.write_text(textwrap.dedent(f'''\
                #!/bin/bash
                REAL={REAL_GIT}
                COUNT={count}
                for a in "$@"; do
                  if [ "$a" = "--force" ] || [ "$a" = "--force-with-lease" ] || [ "$a" = "-f" ]; then
                    echo "force forbidden" >&2
                    exit 99
                  fi
                done
                is_push=0
                for a in "$@"; do
                  if [ "$a" = "push" ]; then is_push=1; fi
                done
                if [ "$is_push" = 1 ]; then
                  n=$(cat "$COUNT")
                  echo $((n + 1)) > "$COUNT"
                  echo "remote rejected" >&2
                  exit 1
                fi
                exec "$REAL" "$@"
            '''))
            wrapper.chmod(0o755)
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
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
            self.assertNotIn("force forbidden", r.stdout + r.stderr)
            self.assertEqual(count.read_text().strip(), "3")
            self.assertEqual(before, after)
            self.assertNotIn("catalog: regenerate counts", log)
