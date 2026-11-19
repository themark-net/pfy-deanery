"""PFY_LOOP_REF pins the loop to a reviewed commit (fix 2).

Failure: the hourly loop runs whatever origin/main holds, so a bad landing
runs unreviewed within the hour. Recovery: with PFY_LOOP_REF set, the loop
runs exactly that commit, and refuses a ref that is malformed or not on
origin/main.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_loop_worktree_behavior import SCRIPT, git, make_repo


def run(repo, wt, ref, cmd=("true",)):
    env = os.environ.copy()
    env["PFY_LOOP_REPO"] = str(repo)
    if ref is None:
        env.pop("PFY_LOOP_REF", None)
    else:
        env["PFY_LOOP_REF"] = ref
    return subprocess.run(["bash", str(SCRIPT), "--wt", str(wt), "--", *cmd], env=env, text=True,
                          capture_output=True, timeout=60)


class LoopPinTest(unittest.TestCase):
    def test_pinned_sha_runs_instead_of_origin_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = make_repo(td)
            reviewed = git(repo, "rev-parse", "HEAD").stdout.strip()
            (repo / "README").write_text("unreviewed\n")
            git(repo, "commit", "-am", "unreviewed landing")
            git(repo, "push", "origin", "main")
            r = run(repo, td / "wt", reviewed, ("bash", "-c", "git rev-parse HEAD; cat README"))
            self.assertEqual(r.returncode, 0, r.stderr)
            lines = r.stdout.strip().splitlines()
            self.assertEqual(lines[-2:], [reviewed, "x"])
            r2 = run(repo, td / "wt", None, ("cat", "README"))
            self.assertEqual(r2.stdout.strip().splitlines()[-1], "unreviewed")

    def test_refuses_malformed_or_off_main_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            td = Path(tmp)
            repo = make_repo(td)
            git(repo, "checkout", "-q", "-b", "side")
            (repo / "side.txt").write_text("s\n")
            git(repo, "add", "side.txt")
            git(repo, "commit", "-m", "side")
            side = git(repo, "rev-parse", "HEAD").stdout.strip()
            git(repo, "push", "origin", "side")
            for ref in ("main", "HEAD~1", side[:12], side):
                with self.subTest(ref=ref):
                    marker = td / f"ran-{ref.replace('~', '_')}"
                    r = run(repo, td / "wt", ref, ("touch", str(marker)))
                    self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                    self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
