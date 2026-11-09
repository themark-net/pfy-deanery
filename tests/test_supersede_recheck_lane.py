"""One supersede recheck lane against a local bare remote.

The lane may push only data/supersede-watchlist.json. An extra dirty file
parks and leaves the remote where it was. No network and no real model lock.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "supersede_recheck_lane.sh"

WATCH = {
    "version": 1,
    "candidate_min_parts": 2,
    "recheck_days": 30,
    "projects": [
        {
            "name": "Old Tool",
            "url": "https://example.com/old-tool",
            "what": "A public page to recheck.",
            "coverage": {
                "track": "none",
                "catalog": "none",
                "evaluate": "none",
                "integrate": "none",
            },
            "verdict": "watch",
            "reason": "fixture",
            "last_checked": "2020-01-01",
        }
    ],
}


def git(repo, *args):
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "Lane",
        "GIT_AUTHOR_EMAIL": "lane@example.com",
        "GIT_COMMITTER_NAME": "Lane",
        "GIT_COMMITTER_EMAIL": "lane@example.com",
        "GIT_TERMINAL_PROMPT": "0",
    })
    subprocess.check_call(["git", *args], cwd=repo, env=env)


def write_grok(path: Path, extra: bool) -> None:
    extra_line = "printf '%s\\n' extra > extra.txt\n" if extra else ""
    path.write_text(
        "#!/bin/sh\n"
        "set -e\n"
        "if [ \"${PFY_MODEL_LOCK_HELD:-}\" != \"1\" ]; then\n"
        "  echo \"model lock not held\" >&2\n"
        "  exit 1\n"
        "fi\n"
        + extra_line
        + "python3 - <<'PY'\n"
        "import json\n"
        "from pathlib import Path\n"
        "p = Path('data/supersede-watchlist.json')\n"
        "doc = json.loads(p.read_text())\n"
        "for proj in doc['projects']:\n"
        "    proj['last_checked'] = '2026-11-08'\n"
        "p.write_text(json.dumps(doc, indent=2) + '\\n')\n"
        "PY\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def make_repo(td: Path):
    seed = td / "seed"
    bare = td / "origin.git"
    clone = td / "clone"
    seed.mkdir()
    subprocess.check_call(["git", "init", "-b", "main", str(seed)])
    git(seed, "config", "user.email", "lane@example.com")
    git(seed, "config", "user.name", "Lane")
    for rel in (
        "scripts/supersede_recheck_lane.sh",
        "scripts/supersede_check.py",
        "scripts/model_lock.sh",
    ):
        dest = seed / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, dest)
        dest.chmod(dest.stat().st_mode | stat.S_IEXEC)
    (seed / "data").mkdir()
    (seed / "data" / "supersede-watchlist.json").write_text(
        json.dumps(WATCH, indent=2) + "\n", encoding="utf-8"
    )
    git(seed, "add", ".")
    git(seed, "commit", "-m", "seed")
    subprocess.check_call(["git", "init", "--bare", str(bare)])
    git(seed, "remote", "add", "origin", str(bare))
    git(seed, "push", "-u", "origin", "main")
    subprocess.check_call(["git", "--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"])
    subprocess.check_call(["git", "clone", str(bare), str(clone)])
    git(clone, "config", "user.email", "lane@example.com")
    git(clone, "config", "user.name", "Lane")
    return clone, bare


def run_lane(td: Path, clone: Path, grok: Path):
    state = td / "state"
    (state / "supersede").mkdir(parents=True)
    (state / "supersede" / "stale.txt").write_text("Old Tool (1 days)\n", encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "PFY_LOOP_STATE": str(state),
        "PFY_LOOP_REPO": str(clone),
        "PFY_GROK_BIN": str(grok),
        "PFY_MODEL_LOCK": str(td / "model.lock"),
        "PFY_DCG_DISABLE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "GIT_TERMINAL_PROMPT": "0",
    })
    proc = subprocess.run(
        ["bash", str(clone / "scripts" / "supersede_recheck_lane.sh")],
        cwd=td,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return proc, state


class SupersedeRecheckLaneTest(unittest.TestCase):
    def test_updates_only_the_watchlist_on_the_bare_remote(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone, bare = make_repo(td)
            before = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            grok = td / "grok"
            write_grok(grok, extra=False)
            proc, state = run_lane(td, clone, grok)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertIn(
                "dcg-fallback: guard.sh missing; built-in denylist not applied; command unchanged",
                proc.stderr,
            )
            after = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            self.assertNotEqual(after, before)
            remote = subprocess.check_output(
                ["git", "--git-dir", str(bare), "show", "main:data/supersede-watchlist.json"],
                text=True,
            )
            self.assertIn("2026-11-08", remote)
            names = subprocess.check_output(
                ["git", "--git-dir", str(bare), "diff-tree", "--no-commit-id", "--name-only", "-r", after],
                text=True,
            )
            self.assertEqual(names.strip(), "data/supersede-watchlist.json")
            self.assertFalse((state / "supersede" / "recheck.dispatched").exists())
            self.assertEqual((state / "supersede" / "recheck.done").read_text().strip(), after)
            self.assertEqual((state / "supersede" / "LANDED_recheck").read_text().strip(), after)
            prompt = (state / "supersede" / "recheck.prompt").read_text(encoding="utf-8")
            for name in (
                "catalog-intake-dedupe",
                "catalog-eval-lane",
                "catalog-integrate-lane",
                "catalog-apply-and-ceiling",
                "catalog-loop-operator",
            ):
                self.assertIn(name, prompt)
            self.assertIn("Old Tool", prompt)
            self.assertFalse((state / "supersede" / "wt").exists())

    def test_extra_file_parks_and_does_not_push(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            clone, bare = make_repo(td)
            before = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            grok = td / "grok"
            write_grok(grok, extra=True)
            proc, state = run_lane(td, clone, grok)
            self.assertNotEqual(proc.returncode, 0, proc.stdout)
            parked = (state / "supersede" / "recheck.parked").read_text(encoding="utf-8")
            self.assertIn("unexpected", parked)
            after = subprocess.check_output(
                ["git", "--git-dir", str(bare), "rev-parse", "main"], text=True
            ).strip()
            self.assertEqual(after, before)
            self.assertTrue((state / "supersede" / "recheck.dispatched").exists())
            self.assertFalse((state / "supersede" / "wt").exists())


if __name__ == "__main__":
    unittest.main()
