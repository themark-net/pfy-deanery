"""Lane driver against a fake grok and a local bare remote.

A grok failure parks and does not move origin/main. A later slug commits,
rebases when main has moved, and fast-forwards that SHA onto origin/main.
A STOP file parks without calling git or grok.
"""
from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "integrate_lane.sh"

STUBS = {
    "scripts/catalog_check.py": "#!/usr/bin/env python3\nraise SystemExit(0)\n",
    "scripts/grill_ticket.py": "#!/usr/bin/env python3\nraise SystemExit(0)\n",
    "scripts/check_no_encoded_payloads.py": "#!/usr/bin/env python3\nraise SystemExit(0)\n",
    "scripts/test_select.py": (
        "#!/usr/bin/env python3\n"
        "import json\n"
        "print(json.dumps({'mode': 'none', 'reason': 'fixture', 'modules': [], "
        "'changed': [], 'source': 'ast'}))\n"
    ),
    "scripts/run_tests.py": (
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "sys.stderr.write('run_tests should not run when modules is empty\\n')\n"
        "raise SystemExit(3)\n"
    ),
    "README": "fixture\n",
    "data/stages/badtool.json": '{"name": "badtool", "integration_stage": "I2"}\n',
    "data/stages/goodtool.json": '{"name": "goodtool", "integration_stage": "I2"}\n',
    "data/stages/reviewstop.json": '{"name": "reviewstop", "integration_stage": "I2"}\n',
}


def git(repo, *args, env=None):
    run_env = os.environ.copy()
    run_env.update(
        {
            "GIT_AUTHOR_NAME": "Lane",
            "GIT_AUTHOR_EMAIL": "lane@example.com",
            "GIT_COMMITTER_NAME": "Lane",
            "GIT_COMMITTER_EMAIL": "lane@example.com",
        }
    )
    if env:
        run_env.update(env)
    subprocess.check_call(["git", *args], cwd=repo, env=run_env)


def make_fixture(td: Path) -> tuple[Path, Path]:
    seed = td / "seed"
    bare = td / "origin.git"
    clone = td / "clone"
    seed.mkdir()
    subprocess.check_call(["git", "init", "-b", "main", str(seed)])
    git(seed, "config", "user.email", "lane@example.com")
    git(seed, "config", "user.name", "Lane")
    for rel, text in STUBS.items():
        path = seed / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    git(seed, "add", ".")
    git(seed, "commit", "-m", "seed")
    subprocess.check_call(["git", "init", "--bare", str(bare)])
    git(seed, "remote", "add", "origin", str(bare))
    git(seed, "push", "-u", "origin", "main")
    subprocess.check_call(
        ["git", "--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"]
    )
    subprocess.check_call(["git", "clone", str(bare), str(clone)])
    git(clone, "config", "user.email", "lane@example.com")
    git(clone, "config", "user.name", "Lane")
    return clone, bare


def write_grok(bindir: Path, log: Path) -> None:
    bindir.mkdir()
    path = bindir / "grok"
    path.write_text(textwrap.dedent(f"""\
        #!/bin/sh
        set -e
        if [ "${{PFY_MODEL_LOCK_HELD:-}}" != "1" ]; then
          echo "model lock not held" >&2
          exit 1
        fi
        printf '%s\\n' "$*" >> {log}
        prompt=""
        prev=""
        for arg in "$@"; do
          if [ "$prev" = "--prompt-file" ]; then
            prompt=$arg
          fi
          prev=$arg
        done
        if grep -q "Self-review" "$prompt"; then
          exit 0
        fi
        if grep -q "badtool" "$prompt"; then
          echo "grok failed" >&2
          exit 1
        fi
        printf '%s\\n' 'print("landed")' > landed.py
        git add landed.py
        git commit -m "land widget"
        common=$(git rev-parse --path-format=absolute --git-common-dir)
        root=$(dirname "$common")
        printf '%s\\n' "root=$root" >> {log}
        git -C "$root" commit --allow-empty -m "main moved"
        git -C "$root" push origin HEAD:refs/heads/main
        exit 0
    """))
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


class LaneLandTest(unittest.TestCase):
    def test_grok_failure_parks_then_a_later_slug_lands_on_the_bare_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone, bare = make_fixture(td)
            log = td / "grok.log"
            bindir = td / "bin"
            write_grok(bindir, log)
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            env["PFY_MODEL_LOCK"] = str(td / "model.lock")
            before = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            (clone / "tmp").mkdir()
            (clone / "tmp" / "TICKET-badtool.md").write_text("badtool ticket\n")
            failed = subprocess.run(
                ["bash", str(SCRIPT), "--root", str(clone), "--slug", "badtool", "--date", "1108"],
                cwd=clone,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertNotEqual(failed.returncode, 0, failed.stderr + failed.stdout)
            parked = (clone / "tmp" / "integrate" / "badtool.parked").read_text()
            self.assertIn("grok", parked)
            self.assertFalse((clone / "tmp" / "integrate" / "LANDED_badtool").exists())
            impl = (clone / "tmp" / "integrate" / "badtool-implement.prompt").read_text()
            self.assertIn("bootstrap/grok-cli/skills/catalog-integrate-lane/SKILL.md", impl)
            self.assertIn("bootstrap/grok-cli/skills/catalog-intake-dedupe/SKILL.md", impl)
            self.assertIn("bootstrap/grok-cli/skills/catalog-eval-lane/SKILL.md", impl)
            self.assertIn("bootstrap/grok-cli/skills/catalog-apply-and-ceiling/SKILL.md", impl)
            self.assertIn("bootstrap/grok-cli/skills/catalog-loop-operator/SKILL.md", impl)
            self.assertIn("tmp/TICKET-badtool.md", impl)
            review = (clone / "tmp" / "integrate" / "badtool-review.prompt").read_text()
            self.assertIn("Self-review", review)
            after_fail = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            self.assertEqual(after_fail, before, "failed grok moved origin/main")

            (clone / "tmp" / "TICKET-goodtool.md").write_text("goodtool ticket\n")
            landed = subprocess.run(
                ["bash", str(SCRIPT), "--root", str(clone), "--slug", "goodtool", "--date", "1108"],
                cwd=clone,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(landed.returncode, 0, landed.stderr + landed.stdout)
            sha = (clone / "tmp" / "integrate" / "LANDED_goodtool").read_text().strip()
            done = (clone / "tmp" / "integrate" / "goodtool.done").read_text().strip()
            self.assertEqual(sha, done)
            remote = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            self.assertEqual(remote, sha)
            show = subprocess.check_output(
                ["git", "--git-dir", str(bare), "show", "main:landed.py"], text=True
            )
            self.assertIn("landed", show)
            progress = (clone / "tmp" / "integrate" / "progress.md").read_text()
            self.assertIn("badtool parked", progress)
            self.assertIn("rebase attempt", progress)
            self.assertIn("goodtool landed", progress)
            self.assertIn("test_select mode=none", progress)
            self.assertIn("skill=catalog-integrate-lane sha=", progress)
            again = subprocess.run(
                ["bash", str(SCRIPT), "--root", str(clone), "--slug", "goodtool", "--date", "1108"],
                cwd=clone,
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(again.returncode, 2, again.stderr)
            remote_again = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            self.assertEqual(remote_again, sha)

    def test_stop_file_parks_without_git_or_grok(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            root = Path(td)
            (root / "tmp").mkdir()
            (root / "tmp" / "STOP").write_text("stop\n")
            card = root / "data" / "stages" / "stop-slug.json"
            card.parent.mkdir(parents=True)
            card.write_text('{"name": "stop-slug", "integration_stage": "I2"}\n')
            log = td / "calls.log"
            bindir = td / "bin"
            bindir.mkdir()
            fake = "#!/bin/sh\nprintf '%s\\n' \"$0 $*\" >> " + str(log) + "\nexit 0\n"
            for name in ("git", "grok"):
                path = bindir / name
                path.write_text(fake)
                path.chmod(path.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            result = subprocess.run(
                ["bash", str(SCRIPT), "--root", str(root), "--slug", "stop-slug", "--date", "1108"],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            parked = (root / "tmp" / "integrate" / "stop-slug.parked").read_text()
            self.assertIn("STOP file", parked)
            self.assertFalse(log.exists(), log.read_text() if log.exists() else "")

    def test_stop_during_review_parks_before_push(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone, bare = make_fixture(td)
            bindir = td / "bin"
            bindir.mkdir()
            grok = bindir / "grok"
            grok.write_text(textwrap.dedent("""\
                #!/bin/sh
                set -e
                if [ "${PFY_MODEL_LOCK_HELD:-}" != "1" ]; then
                  echo "model lock not held" >&2
                  exit 1
                fi
                prompt=""
                prev=""
                for arg in "$@"; do
                  if [ "$prev" = "--prompt-file" ]; then
                    prompt=$arg
                  fi
                  prev=$arg
                done
                if grep -q "Self-review" "$prompt"; then
                  mkdir -p tmp
                  printf '%s\\n' stop > tmp/STOP
                  exit 0
                fi
                exit 0
            """))
            grok.chmod(grok.stat().st_mode | stat.S_IEXEC)
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            env["PFY_MODEL_LOCK"] = str(td / "model.lock")
            before = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            (clone / "tmp").mkdir()
            (clone / "tmp" / "TICKET-reviewstop.md").write_text("review stop\n")
            result = subprocess.run(
                ["bash", str(SCRIPT), "--root", str(clone), "--slug", "reviewstop", "--date", "1108"],
                cwd=clone,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            parked = (clone / "tmp" / "integrate" / "reviewstop.parked").read_text()
            self.assertIn("STOP file", parked)
            self.assertFalse((clone / "tmp" / "integrate" / "LANDED_reviewstop").exists())
            after = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            self.assertEqual(after, before)
