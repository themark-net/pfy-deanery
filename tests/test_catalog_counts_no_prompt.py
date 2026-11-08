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


class NoPromptTest(unittest.TestCase):
    def test_push_sets_git_terminal_prompt_0(self):
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
            bindir = td / "bin"
            bindir.mkdir()
            marker = td / "push-env"
            wrapper = bindir / "git"
            wrapper.write_text(textwrap.dedent(f'''\
                #!/bin/bash
                is_push=0
                for a in "$@"; do
                  if [ "$a" = "push" ]; then is_push=1; fi
                done
                if [ "$is_push" = 1 ]; then
                  printf '%s' "${{GIT_TERMINAL_PROMPT:-}}" > {marker}
                  if [ "${{GIT_TERMINAL_PROMPT:-}}" != "0" ]; then
                    echo "would prompt" >&2
                    exit 4
                  fi
                fi
                exec {REAL_GIT} "$@"
            '''))
            wrapper.chmod(0o755)
            env = os.environ.copy()
            env.pop("GIT_TERMINAL_PROMPT", None)
            env["PFY_LOOP_REPO"] = str(repo)
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
            r = subprocess.run(
                ["bash", str(LOOP), "--wt", str(td / "wt"), "--", "scripts/catalog_counts_publish.sh"],
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
            )
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(marker.read_text(), "0")
