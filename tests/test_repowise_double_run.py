import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval/integrate/repowise/run-on-main.sh"
MARKER = "/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/repowise.dispatched"


class TestRepowiseDoubleRun(unittest.TestCase):
    def test_script_stops_a_second_start(self):
        text = Path("eval/integrate/repowise/run-on-main.sh").read_text()
        self.assertIn("repowise.dispatched", text)
        self.assertIn("exit 2", text)
        self.assertNotIn("model_lock.sh", text)
        self.assertNotIn("mkdir", text.lower().split("repowise.dispatched")[0][-80:])
        self.assertTrue("flock" in text)
        self.assertIn(MARKER, text)
        self.assertNotIn(">" + MARKER, text.replace(" ", ""))


def _non_ancestor_repo(path: Path, env: dict[str, str]) -> None:
    env["GIT_AUTHOR_NAME"] = "test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    path.mkdir()
    subprocess.run(["git", "-C", str(path), "init", "-q"], env=env, check=True)
    (path / "README").write_text("ahead\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README"], env=env, check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "init"], env=env, check=True)
    subprocess.run(["git", "-C", str(path), "update-ref", "refs/remotes/origin/main", "HEAD"], env=env, check=True)
    (path / "README").write_text("not-on-main\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "README"], env=env, check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "ahead"], env=env, check=True)


class TestRepowiseDoubleRunBehavior(unittest.TestCase):
    def _run(self, marker: Path | None, receipt: Path, repo: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
        run_env = dict(env)
        run_env["PFY_REPOWISE_LANE_MARKER"] = str(marker if marker is not None else receipt.parent / "missing-marker")
        return subprocess.run(
            ["bash", str(SCRIPT), str(receipt)],
            cwd=repo,
            env=run_env,
            capture_output=True,
            text=True,
        )

    def test_foreign_marker_exits_2_without_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            repo = tmp_path / "repo"
            _non_ancestor_repo(repo, env)
            marker = tmp_path / "lane.dispatched"
            marker.write_text("pid 1\n", encoding="utf-8")
            before = marker.read_bytes()
            receipt = tmp_path / "receipt.json"
            make_log = tmp_path / "make.log"
            env["REPOWISE_MAKE_LOG"] = str(make_log)
            proc = self._run(marker, receipt, repo, env)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertFalse(make_log.exists())
            self.assertEqual(marker.read_bytes(), before)
            self.assertIn("already dispatched", proc.stderr)
            self.assertEqual(list(tmp_path.glob(".receipt.*")), [])

    def test_pidless_marker_exits_2_without_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            repo = tmp_path / "repo"
            _non_ancestor_repo(repo, env)
            marker = tmp_path / "lane.dispatched"
            marker.write_text("held\n", encoding="utf-8")
            receipt = tmp_path / "receipt.json"
            proc = self._run(marker, receipt, repo, env)
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertFalse(receipt.exists())

    def test_admitted_lane_marker_does_not_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            repo = tmp_path / "repo"
            _non_ancestor_repo(repo, env)
            marker = tmp_path / "lane.dispatched"
            marker.write_text("pid %s\n" % os.getpid(), encoding="utf-8")
            before = marker.read_bytes()
            receipt = tmp_path / "receipt.json"
            make_log = tmp_path / "make.log"
            env["REPOWISE_MAKE_LOG"] = str(make_log)
            proc = self._run(marker, receipt, repo, env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertFalse(make_log.exists())
            self.assertEqual(marker.read_bytes(), before)
            self.assertIn("not an ancestor", proc.stderr)

    def test_missing_marker_is_not_a_second_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            repo = tmp_path / "repo"
            _non_ancestor_repo(repo, env)
            receipt = tmp_path / "receipt.json"
            make_log = tmp_path / "make.log"
            env["REPOWISE_MAKE_LOG"] = str(make_log)
            proc = self._run(None, receipt, repo, env)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertFalse(make_log.exists())
            self.assertIn("not an ancestor", proc.stderr)


if __name__ == "__main__":
    unittest.main()
