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


class PushRebaseTest(unittest.TestCase):
    def test_rejected_push_recovers_by_rebase_without_force(self):
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
            (repo / "scripts" / "catalog_counts.py").write_text(textwrap.dedent('''\
                from pathlib import Path
                Path("data/stages/_registry.json").write_text("{\\"coverage\\": 1}\\n")
                Path("pipelines/catalog/dashboard.latest.md").write_text("new\\n")
                Path("pipelines/catalog/counts.latest.json").write_text("{\\"n\\": 1}\\n")
            '''))
            pub = repo / "scripts" / "catalog_counts_publish.sh"
            pub.write_text(PUBLISH.read_text())
            pub.chmod(pub.stat().st_mode | stat.S_IEXEC)
            git(repo, "add", ".")
            git(repo, "commit", "-m", "fixture")
            git(repo, "remote", "add", "origin", str(origin))
            git(repo, "push", "-u", "origin", "main")
            mark = td / "pushed-once"
            bindir = td / "bin"
            bindir.mkdir()
            wrapper = bindir / "git"
            wrapper.write_text(textwrap.dedent(f'''\
                #!/bin/bash
                REAL={REAL_GIT}
                ORIGIN={origin}
                MARK={mark}
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
                if [ "$is_push" = 1 ] && [ ! -f "$MARK" ]; then
                  touch "$MARK"
                  parent=$("$REAL" --git-dir="$ORIGIN" rev-parse refs/heads/main)
                  new=$(GIT_AUTHOR_NAME=other GIT_AUTHOR_EMAIL=other@example.com GIT_COMMITTER_NAME=other GIT_COMMITTER_EMAIL=other@example.com "$REAL" --git-dir="$ORIGIN" commit-tree "$parent^{{tree}}" -p "$parent" -m "other lane")
                  "$REAL" --git-dir="$ORIGIN" update-ref refs/heads/main "$new"
                  echo "remote rejected" >&2
                  exit 1
                fi
                exec "$REAL" "$@"
            '''))
            wrapper.chmod(0o755)
            env = os.environ.copy()
            env["PFY_LOOP_REPO"] = str(repo)
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
            wt = td / "wt"
            r = subprocess.run(
                ["bash", str(LOOP), "--wt", str(wt), "--", "scripts/catalog_counts_publish.sh"],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(mark.is_file())
            log = subprocess.check_output(
                [REAL_GIT, "--git-dir", str(origin), "log", "--format=%s"], text=True
            ).splitlines()
            self.assertEqual(log[0], "catalog: regenerate counts")
            self.assertEqual(log[1], "other lane")
