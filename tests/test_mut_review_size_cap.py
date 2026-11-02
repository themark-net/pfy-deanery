"""Size cap of the local review loop. Kills mutants R7, R8, and R9.

A green patch over 3 counted files or 250 added plus removed lines is
PASS-REJECTED and is not committed. The reviewer is not asked. Narrowing
back to the cap lets the same task pass.

R7 allows 4 files. R8 allows 251 lines. R9 skips the check. Each over-cap
case fails on that mutant and passes on the unmutated runner.
"""

from __future__ import annotations

import json
import unittest

import tests.test_pfy_build_local as harness


def _calc(extra_lines):
    lines = ["def add(a, b):", "    return a + b"]
    lines.extend("# pad %d" % i for i in range(extra_lines))
    return "\n".join(lines) + "\n"


class SizeCapTests(unittest.TestCase):
    def setUp(self):
        self.inner = harness.LocalBuildTests()
        self.inner.setUp()
        notes = self.inner.tmp / "stub-notes"
        notes.mkdir()
        self.plan = notes / "plan.json"
        self.count = notes / "attempt-count"

    def tearDown(self):
        self.inner.tearDown()

    def _run(self, task, step, timeout=90, retries="0"):
        self.plan.write_text(json.dumps([step]), encoding="utf-8")
        env = {
            "PFY_STUB_PLAN": str(self.plan),
            "PFY_STUB_COUNT": str(self.count),
            "PFY_LOCAL_BUILD_TEST_SEAM": "1",
        }
        return self.inner.run_build(
            "plan",
            extra=["--retries", retries],
            env_extra=env,
            timeout=timeout,
            task=task,
        )

    def _size(self, receipt):
        path = receipt / "attempt-1" / "receipt.json"
        self.assertTrue(path.is_file(), path)
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["checks"]["size"]

    def _chat(self):
        return [path for path, _payload in self.inner.httpd.posts if "chat" in path]

    def _seed_tracked(self):
        # New untracked names are not staged by the reviewed pathspec, so the
        # cap cases edit files that are already in the base commit.
        repo = self.inner.repo
        for name in ("a", "b", "c"):
            (repo / "src" / ("%s.py" % name)).write_text("x = 0\n", encoding="utf-8")
        self.inner.commit_base("seed tracked sources")

    def test_four_files_are_rejected_and_three_files_pass(self):
        self._seed_tracked()
        task = "fix add so one plus one is two\nfiles: src/*\n"
        fixed = _calc(0)
        wide = {
            "mode": "noop",
            "write": {
                "src/calc.py": fixed,
                "src/a.py": "x = 1\n",
                "src/b.py": "x = 2\n",
                "src/c.py": "x = 3\n",
            },
        }
        proc, receipt = self._run(task, wide)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS-REJECTED")
        self.assertEqual(data["reason"], "review-rejected")
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        size = self._size(receipt)
        self.assertEqual(size["files"], 4)
        self.assertEqual(size["max_files"], 3)
        self.assertFalse(size["ok"])
        self.assertEqual(self._chat(), [])
        self.inner.assert_clean_origin()

        narrow = {
            "mode": "noop",
            "write": {
                "src/calc.py": fixed,
                "src/a.py": "x = 1\n",
                "src/b.py": "x = 2\n",
            },
        }
        proc, receipt = self._run(task, narrow)
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(
            proc.returncode,
            0,
            proc.stdout + proc.stderr + "\n" + json.dumps(data.get("files_changed")),
        )
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["reason"], "ok")
        self.assertIsNotNone(data["commit"])
        names = harness._git(
            self.inner.repo,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            data["commit"],
        ).strip().splitlines()
        self.assertEqual(sorted(names), ["src/a.py", "src/b.py", "src/calc.py"])
        size = self._size(receipt)
        self.assertEqual(size["files"], 3)
        self.assertTrue(size["ok"])
        self.inner.assert_clean_origin()

    def test_two_hundred_fifty_one_lines_are_rejected_and_two_hundred_fifty_pass(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        # The def line is unchanged. One return line is replaced and each pad
        # line is added, so diff lines = pad count + 2. 249 pads is 251.
        # 248 pads is 250, which is still inside the cap.
        over, over_receipt = self._run(task, {"mode": "noop", "write": {"src/calc.py": _calc(249)}})
        data = self.inner.receipt(over, over_receipt)
        size = self._size(over_receipt)
        self.assertEqual(over.returncode, 1, over.stdout + over.stderr + "\n" + json.dumps(size))
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "review-diff-over-line-cap")
        self.assertIsNone(data["commit"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        size = self._size(over_receipt)
        self.assertEqual(size["lines"], 251)
        self.assertEqual(size["max_lines"], 250)
        self.assertEqual(size["files"], 1)
        self.assertFalse(size["ok"])
        self.assertEqual(self._chat(), [])
        self.inner.assert_clean_origin()

        inside, inside_receipt = self._run(task, {"mode": "noop", "write": {"src/calc.py": _calc(248)}})
        self.assertEqual(inside.returncode, 0, inside.stdout + inside.stderr)
        data = self.inner.receipt(inside, inside_receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertIsNotNone(data["commit"])
        size = self._size(inside_receipt)
        self.assertEqual(size["lines"], 250)
        self.assertTrue(size["ok"])
        shown = harness._git(self.inner.repo, "show", "%s:src/calc.py" % data["commit"])
        self.assertIn("return a + b\n", shown)
        self.assertNotIn("+ 1", shown)
        self.inner.assert_clean_origin()

    def test_over_the_line_cap_is_refused_once_without_retries(self):
        # Over the line cap is refused once. The reviewer is not asked, so a
        # retry would only send the model the same size feedback for nothing.
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        over, receipt = self._run(
            task, {"mode": "noop", "write": {"src/calc.py": _calc(260)}}, retries="2"
        )
        data = self.inner.receipt(over, receipt)
        self.assertEqual(over.returncode, 1, over.stdout + over.stderr)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "review-diff-over-line-cap")
        self.assertEqual(data["attempts"], 1)
        self.assertFalse((receipt / "attempt-2").exists())
        self.assertEqual(self.count.read_text(encoding="utf-8").strip(), "1")
        self.assertIsNone(data["commit"])
        self.assertEqual(self._chat(), [])
        self.assertIn("250", (over.stdout or "") + (over.stderr or "") + json.dumps(data))
        self.inner.assert_clean_origin()

