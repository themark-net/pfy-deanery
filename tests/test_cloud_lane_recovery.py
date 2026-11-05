"""Exit test F3: recovery lines tell the operator or bot what to do, not who."""

from __future__ import annotations

import unittest

from tests.test_pfy_build_cloud import _load_cloud


class RecoveryLinesNameTheNextAction(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = _load_cloud()

    def lines(self) -> dict[str, str]:
        mod = self.mod
        out = {"reason:%s" % r: mod.failure_recovery(r, "add kept value") for r in mod.TERMINAL_FAILURE_REASONS}
        out["auth"] = mod.auth_recovery("add kept value")
        out["rate"] = mod.rate_recovery("add kept value")
        for detail in ("missing-ref", "mkdir", "add", ""):
            out["worktree:%s" % detail] = mod.worktree_recovery("add kept value", "main", detail)
        return out

    def test_no_recovery_line_is_addressed_to_a_person(self) -> None:
        for key, line in self.lines().items():
            self.assertNotIn("Mark:", line, key)
            self.assertFalse(line.lstrip().lower().startswith("mark"), (key, line))

    def test_every_recovery_line_names_a_next_action(self) -> None:
        verbs = ("rerun", "./pfy ", "run ", "pass ", "wait", "restore", "restate", "read", "change", "make", "log in", "fix", "split", "remove", "install")
        for key, line in self.lines().items():
            self.assertTrue(any(v in line.lower() for v in verbs), (key, line))

    def test_build_busy_says_wait_then_rerun(self) -> None:
        line = self.mod.failure_recovery("build-busy", "add kept value").lower()
        self.assertIn("wait", line)
        self.assertIn("./pfy build", line)

    def test_gate_rewrote_says_make_the_gate_check_only(self) -> None:
        line = self.mod.failure_recovery("gate-rewrote", "add kept value").lower()
        self.assertIn("gate", line)
        self.assertIn("./pfy build", line)


if __name__ == "__main__":
    unittest.main()
