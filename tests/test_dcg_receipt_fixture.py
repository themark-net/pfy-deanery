#!/usr/bin/env python3
"""run-on-main.sh writes a receipt on a fixture whose HEAD is origin/main."""
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN_ON_MAIN = ROOT / "eval" / "integrate" / "destructive-command-guard" / "run-on-main.sh"


def _git_env():
    env = os.environ.copy()
    env.pop("PFY_DCG_DISABLE", None)
    env["PFY_DCG_BIN"] = "/nonexistent/dcg"
    env.update({
        "GIT_AUTHOR_NAME": "dcg-test",
        "GIT_AUTHOR_EMAIL": "dcg-test@example.com",
        "GIT_COMMITTER_NAME": "dcg-test",
        "GIT_COMMITTER_EMAIL": "dcg-test@example.com",
    })
    return env


class TestReceiptFixture(unittest.TestCase):
    def test_ancestor_writes_receipt_and_does_not_run_rm(self):
        self.assertTrue(RUN_ON_MAIN.is_file(), "run-on-main.sh missing")
        env = _git_env()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            bindir = root / "bin"
            bindir.mkdir()
            marker = root / "rm-ran"
            fake = bindir / "rm"
            fake.write_text(
                "#!/bin/sh\nprintf '%s\\n' ran >> " + str(marker) + "\nexit 0\n"
            )
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            env["PATH"] = str(bindir) + os.pathsep + env.get("PATH", "")
            subprocess.check_call(["git", "init", "-q", "-b", "main", str(root)], env=env)
            (root / "a.txt").write_text("a\n")
            subprocess.check_call(["git", "-C", str(root), "add", "a.txt"], env=env)
            subprocess.check_call(["git", "-C", str(root), "commit", "-q", "-m", "base"], env=env)
            subprocess.check_call(
                ["git", "-C", str(root), "update-ref", "refs/remotes/origin/main", "HEAD"],
                env=env,
            )
            head = subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, env=env
            ).strip()
            receipt = root / "receipt.json"
            proc = subprocess.run(
                ["bash", str(RUN_ON_MAIN), str(receipt)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            self.assertFalse(marker.exists(), "guard executed rm")
            data = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(data["slug"], "destructive-command-guard")
            self.assertEqual(data["run_kind"], "gate")
            self.assertEqual(data["main_sha"], head)
            self.assertEqual(data["outcome"], "ok")
            self.assertEqual(data["tool_version"], "fallback")
            self.assertIn("not executed", data["did"])
            self.assertTrue(data["run_id"])
            self.assertTrue(data["started"])
            self.assertTrue(data["finished"])


if __name__ == "__main__":
    unittest.main()
