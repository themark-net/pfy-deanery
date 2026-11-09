"""Lane records go to the ops checkout; public keeps scrubbed verdicts.

How this fails: an eval or integrate lane commits REPORT.md, traces, or a
raw log under eval/ and lands it on public main, or a VERDICT.json with the
operator home path or name lands as is, or the prose report is lost instead
of reaching PFY_OPS_ROOT.
Recover: scripts/lane_ops_sync.py moves records to tmp/ops and syncs them,
scrubs public outputs, and exits 1 (lane parks) when the guard still fails.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYNC = ROOT / "scripts" / "lane_ops_sync.py"
OWNER = "Ma" + "rk"
ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
       "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com"}


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env={**os.environ, **ENV}, check=True,
                          capture_output=True, text=True).stdout


class LaneOpsSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.home = str(Path.home())
        for name in ("pub.git", "ops.git"):
            git(base, "init", "-q", "--bare", "-b", "main", name)
        self.wt = base / "wt"
        self.ops = base / "ops"
        for repo, remote in ((self.wt, "pub.git"), (self.ops, "ops.git")):
            git(base, "clone", "-q", str(base / remote), repo.name)
            (repo / "README.md").write_text("x\n", encoding="utf-8")
            (repo / ".gitignore").write_text("tmp/\n", encoding="utf-8")
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "base")
            git(repo, "push", "-q", "origin", "HEAD:main")
        git(self.wt, "fetch", "-q", "origin")
        lane = self.wt / "eval" / "evals" / "x"
        (lane / "traces").mkdir(parents=True)
        (lane / "VERDICT.json").write_text('{"bin": "%s/.local/bin/x", "who": "%s"}\n' % (self.home, OWNER),
                                           encoding="utf-8")
        (lane / "REPORT.md").write_text("what happened\n", encoding="utf-8")
        (lane / "traces" / "session.json").write_text("{}\n", encoding="utf-8")
        git(self.wt, "add", "-A")
        git(self.wt, "commit", "-qm", "lane")
        side = self.wt / "tmp" / "ops" / "eval" / "evals" / "x"
        side.mkdir(parents=True)
        (side / "run.log").write_text("raw\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_sync(self, ops: str | None) -> subprocess.CompletedProcess:
        env = {**os.environ, **ENV}
        env.pop("PFY_OPS_ROOT", None)
        env.pop("PFY_LOOP_NO_PUSH", None)
        if ops is not None:
            env["PFY_OPS_ROOT"] = ops
        return subprocess.run([sys.executable, str(SYNC), "--worktree", str(self.wt),
                               "--subdir", "eval/evals/x", "--label", "eval x"],
                              env=env, capture_output=True, text=True, timeout=60)

    def test_records_move_to_ops_and_public_outputs_are_scrubbed(self) -> None:
        proc = self.run_sync(str(self.ops))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        tracked = git(self.wt, "ls-files", "eval").split()
        self.assertEqual(tracked, ["eval/evals/x/VERDICT.json"])
        verdict = (self.wt / "eval/evals/x/VERDICT.json").read_text(encoding="utf-8")
        self.assertNotIn(self.home, verdict)
        self.assertIn("$HOME/.local/bin/x", verdict)
        self.assertNotIn(OWNER, verdict)
        git(self.ops, "fetch", "-q", "origin")
        pushed = git(self.ops, "ls-tree", "-r", "--name-only", "origin/main").split()
        for rel in ("eval/evals/x/REPORT.md", "eval/evals/x/traces/session.json", "eval/evals/x/run.log"):
            self.assertIn(rel, pushed)
        self.assertIn("ops pushed eval/evals/x", proc.stdout)

    def test_unset_ops_root_keeps_records_in_gitignored_tmp(self) -> None:
        proc = self.run_sync(None)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("ops unset", proc.stdout)
        self.assertTrue((self.wt / "tmp/ops/eval/evals/x/REPORT.md").is_file())
        self.assertEqual(git(self.wt, "ls-files", "eval").split(), ["eval/evals/x/VERDICT.json"])

    def test_guard_failure_outside_the_lane_dir_parks(self) -> None:
        (self.wt / "docs").mkdir()
        (self.wt / "docs" / "n.md").write_text("Ask %s first.\n" % OWNER, encoding="utf-8")
        git(self.wt, "add", "-A")
        git(self.wt, "commit", "-qm", "doc")
        proc = self.run_sync(str(self.ops))
        self.assertEqual(proc.returncode, 1, proc.stdout)
        self.assertIn("docs/n.md:1: owner name", proc.stdout)


if __name__ == "__main__":
    unittest.main()
