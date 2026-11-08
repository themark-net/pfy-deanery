#!/usr/bin/env python3
"""Two dcg runs must not share work or file an off-main receipt."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "integrations" / "dcg" / "guard.sh"
RUN_ON_MAIN = ROOT / "eval" / "integrate" / "destructive-command-guard" / "run-on-main.sh"


def _git_env():
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "dcg-test",
        "GIT_AUTHOR_EMAIL": "dcg-test@example.com",
        "GIT_COMMITTER_NAME": "dcg-test",
        "GIT_COMMITTER_EMAIL": "dcg-test@example.com",
    })
    return env


class TestNoDoubleWork(unittest.TestCase):
    def test_parallel_denies_write_nothing_and_do_not_lock(self):
        self.assertTrue(GUARD.is_file(), "guard.sh missing")
        with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as tmp:
            env = os.environ.copy()
            env.pop("PFY_DCG_DISABLE", None)
            env["HOME"] = home
            env["TMPDIR"] = tmp
            env["PFY_DCG_BIN"] = "/nonexistent/dcg"
            procs = [
                subprocess.Popen(
                    ["bash", str(GUARD), "rm", "-rf", "/"],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                for _ in range(2)
            ]
            codes = []
            for proc in procs:
                try:
                    _out, err = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    self.fail("guard blocked as if a shared lock existed")
                codes.append(proc.returncode)
                self.assertIn(b"dcg-fallback", err)
            self.assertEqual(codes, [126, 126])
            self.assertEqual(list(Path(home).rglob("*")), [])
            self.assertEqual(list(Path(tmp).rglob("*")), [])

    def test_receipt_refuses_head_not_ancestor_of_origin_main(self):
        self.assertTrue(RUN_ON_MAIN.is_file(), "run-on-main.sh missing")
        env = _git_env()
        with tempfile.TemporaryDirectory() as d:
            subprocess.check_call(["git", "init", "-q", "-b", "main", d], env=env)
            path = Path(d) / "a.txt"
            path.write_text("a\n")
            subprocess.check_call(["git", "-C", d, "add", "a.txt"], env=env)
            subprocess.check_call(["git", "-C", d, "commit", "-q", "-m", "base"], env=env)
            subprocess.check_call(["git", "-C", d, "checkout", "-q", "-b", "diverged"], env=env)
            path.write_text("b\n")
            subprocess.check_call(["git", "-C", d, "commit", "-q", "-am", "side"], env=env)
            subprocess.check_call(
                ["git", "-C", d, "update-ref", "refs/remotes/origin/main", "refs/heads/main"],
                env=env,
            )
            receipt = Path(d) / "receipt.json"
            proc = subprocess.run(
                ["bash", str(RUN_ON_MAIN), str(receipt)],
                cwd=d,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(receipt.exists())


if __name__ == "__main__":
    unittest.main()
