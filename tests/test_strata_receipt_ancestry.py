import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "eval" / "integrate" / "strata" / "run-on-main.sh"


def _off_main_repo(td):
    # Fixture checkout whose HEAD is one commit ahead of origin/main, so the
    # test proves the refusal no matter whether a real receipt is on main.
    repo = td / "repo"
    dest = repo / "eval" / "integrate" / "strata"
    dest.mkdir(parents=True)
    shutil.copy2(SCRIPT, dest / "run-on-main.sh")
    git = ["git", "-C", str(repo), "-c", "user.email=lane@example.com",
           "-c", "user.name=lane", "-c", "commit.gpgsign=false"]
    subprocess.check_call(["git", "init", "-q", str(repo)])
    subprocess.check_call(git + ["add", "-A"])
    subprocess.check_call(git + ["commit", "-qm", "base"])
    subprocess.check_call(git + ["update-ref", "refs/remotes/origin/main", "HEAD"])
    subprocess.check_call(git + ["commit", "--allow-empty", "-qm", "ahead"])
    return repo


class StrataReceiptAncestryTest(unittest.TestCase):
    def test_pipeline_receipt_requires_origin_main_ancestor(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("pipeline", text)
        self.assertIn("origin/main", text)
        self.assertIn("merge-base", text)
        self.assertIn("--is-ancestor", text)
        self.assertIn("receipt.json", text)

    def test_worktree_head_writes_no_receipt(self):
        with tempfile.TemporaryDirectory() as raw:
            repo = _off_main_repo(pathlib.Path(raw))
            receipt = pathlib.Path(raw) / "receipt.json"
            kept = pathlib.Path(raw) / "kept.json"
            kept.write_text("keep\n", encoding="utf-8")
            env = os.environ.copy()
            for key in (
                "GIT_DIR",
                "GIT_WORK_TREE",
                "GIT_INDEX_FILE",
                "PFY_STRATA_BASE",
                "PFY_STRATA_API_KEY",
                "STRATA_API_KEY",
            ):
                env.pop(key, None)
            env["PFY_STRATA_LANE_MARKER"] = str(pathlib.Path(raw) / "missing-marker")
            proc = subprocess.run(
                ["bash", str(repo / "eval/integrate/strata/run-on-main.sh"), str(receipt)],
                cwd=repo,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertFalse(receipt.exists())
            self.assertIn("no receipt", proc.stderr)
            self.assertIn("not an ancestor", proc.stderr)
            again = subprocess.run(
                ["bash", str(repo / "eval/integrate/strata/run-on-main.sh"), str(kept)],
                cwd=repo, env=env, capture_output=True, text=True, timeout=15,
            )
            self.assertEqual(again.returncode, 1, again.stderr)
            self.assertEqual(kept.read_text(encoding="utf-8"), "keep\n")


if __name__ == "__main__":
    unittest.main()
