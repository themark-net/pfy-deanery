"""B2: in a worktree copy isolated by _isolate_gitdir, a gate that runs
`git status` (which refreshes .git.private/index) is not a rewrite."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_pfy_build_cloud import SCRATCH, _git, _init_repo, _load_cloud


class IsolatedGitdirGateStatus(unittest.TestCase):
    def setUp(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.base = Path(tempfile.mkdtemp(prefix="isogit-", dir=SCRATCH))
        self.addCleanup(shutil.rmtree, self.base, True)
        self.mod = _load_cloud()
        repo = _init_repo(self.base / "repo")
        (repo / "src").mkdir(exist_ok=True)
        (repo / "src" / "kept.py").write_text("kept = 1\n", encoding="utf-8")
        _git(repo, "add", "src/kept.py")
        _git(repo, "commit", "-qm", "kept")
        self.wt = self.base / "wt"
        self.assertEqual(_git(repo, "worktree", "add", "-q", str(self.wt)).returncode, 0)
        (self.wt / "src" / "kept.py").write_text("kept = 2\n", encoding="utf-8")
        self.copy = self.base / "wt-flake"
        shutil.copytree(self.wt, self.copy, symlinks=True)
        self.mod.CloudBuild._isolate_gitdir(None, self.copy)

    def test_copy_has_its_own_private_gitdir(self) -> None:
        self.assertTrue((self.copy / ".git.private").is_dir())
        self.assertIn(".git.private", (self.copy / ".git").read_text())

    def test_git_status_in_the_isolated_copy_does_not_change_the_manifest(self) -> None:
        before = self.mod.gate_tree_manifest(self.copy)
        self.assertIn("src/kept.py", before)
        status = subprocess.run(["git", "status", "--porcelain"], cwd=self.copy, capture_output=True, text=True, timeout=60)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("src/kept.py", status.stdout)
        after = self.mod.gate_tree_manifest(self.copy)
        self.assertFalse([k for k in after if k == ".git" or k.startswith((".git/", ".git.private"))], sorted(after))
        self.assertEqual(before, after)

    def test_a_real_rewrite_in_the_isolated_copy_still_changes_the_manifest(self) -> None:
        before = self.mod.gate_tree_manifest(self.copy)
        (self.copy / "src" / "kept.py").write_text("kept = 3\n", encoding="utf-8")
        self.assertNotEqual(before, self.mod.gate_tree_manifest(self.copy))


if __name__ == "__main__":
    unittest.main()
