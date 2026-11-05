"""Exit test F2: a gate that changes a file's mode is a rewrite."""

from __future__ import annotations

import unittest

from tests.test_cloud_lane_manifest import _Rewrite


class GateModeChanges(_Rewrite):
    def test_gate_that_makes_a_changed_file_executable_fails(self) -> None:
        r = self.build(
            "Path('run.sh').write_text('echo hi\\n')\n",
            "p = Path('run.sh')\nif p.exists(): os.chmod(p, 0o755)\nprint('ok')\n",
        )
        self.assert_rewrote(r)

    def test_gate_that_drops_the_exec_bit_of_a_tracked_file_fails(self) -> None:
        self.commit_file("tool.sh", "echo tool\n")
        (self.repo / "tool.sh").chmod(0o755)
        self.assertEqual(__import__("tests.test_pfy_build_cloud", fromlist=["_git"])._git(self.repo, "add", "tool.sh").returncode, 0)
        __import__("tests.test_pfy_build_cloud", fromlist=["_git"])._git(self.repo, "commit", "-qm", "exec tool")
        r = self.build(
            "Path('k.py').write_text('k = 1\\n')\n",
            "p = Path('tool.sh')\nif Path('k.py').exists(): os.chmod(p, 0o644)\nprint('ok')\n",
        )
        self.assert_rewrote(r)

    def test_executable_file_made_by_the_agent_is_committed_as_executable(self) -> None:
        r = self.build(
            "p = Path('run.sh')\np.write_text('echo hi\\n')\nos.chmod(p, 0o755)\n",
            "print('ok')\n",
        )
        self.assert_passed(r)
        from tests.test_pfy_build_cloud import _git

        entry = _git(self.repo, "ls-tree", r["commit"], "run.sh").stdout
        self.assertTrue(entry.startswith("100755 "), entry)


if __name__ == "__main__":
    unittest.main()
