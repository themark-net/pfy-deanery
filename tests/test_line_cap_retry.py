"""The local line cap retries with the same budget and feedback as the 3-file cap.

Fail: an over-line-cap green patch is refused once (reason
review-diff-over-line-cap) even when retries remain, or the retry prompt
does not carry the file-cap-shaped line reason, or an under-cap patch is
retried anyway.
Recover: over-cap sets PASS-REJECTED / review-rejected, posts the
"changed lines N (max M)" reason into the next implement prompt, and
hard-stops when the retry budget is spent. Under the cap is one attempt
and PASS. The stub agent is used; no paid calls.
"""

from __future__ import annotations

import json
import unittest

import tests.test_pfy_build_local as harness


def _calc(extra_lines):
    lines = ["def add(a, b):", "    return a + b"]
    lines.extend("# pad %d" % i for i in range(extra_lines))
    return "\n".join(lines) + "\n"


def _prompts(path):
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


class LineCapRetryTests(unittest.TestCase):
    def setUp(self):
        self.inner = harness.LocalBuildTests()
        self.inner.setUp()
        notes = self.inner.tmp / "stub-notes"
        notes.mkdir()
        self.prompts = notes / "prompts.jsonl"
        self.plan = notes / "plan.json"
        self.count = notes / "attempt-count"

    def tearDown(self):
        self.inner.tearDown()

    def _env(self):
        return {
            "PFY_STUB_PLAN": str(self.plan),
            "PFY_STUB_COUNT": str(self.count),
            "PFY_STUB_PROMPTS": str(self.prompts),
            "PFY_LOCAL_BUILD_TEST_SEAM": "1",
        }

    def _run(self, task, steps, retries, timeout=90):
        self.plan.write_text(json.dumps(steps), encoding="utf-8")
        return self.inner.run_build(
            "plan",
            extra=["--retries", str(retries), "--max-files", "3", "--max-lines", "250"],
            env_extra=self._env(),
            timeout=timeout,
            task=task,
        )

    def _chat(self):
        return [path for path, _payload in self.inner.httpd.posts if "chat" in path]

    def test_over_line_cap_retries_with_file_cap_shaped_feedback(self):
        # 249 pads -> 251 diff lines (over). 248 pads -> 250 (fits).
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        over = {"mode": "noop", "write": {"src/calc.py": _calc(249)}}
        fit = {"mode": "noop", "write": {"src/calc.py": _calc(248)}}
        proc, receipt = self._run(task, [over, fit], retries=1)
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["attempts"], 2)
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(first["status"], "PASS-REJECTED")
        self.assertEqual(first["reason"], "review-rejected")
        self.assertEqual(first["checks"]["size"]["lines"], 251)
        self.assertEqual(first["checks"]["size"]["max_lines"], 250)
        rows = _prompts(self.prompts)
        self.assertGreaterEqual(len(rows), 2)
        retry = rows[1]["prompt"]
        self.assertIn("changed lines 251 (max 250).", retry)
        self.assertIn("The flag that raises the line cap is --max-lines.", retry)
        self.assertIn("Rerun with --max-lines.", retry)
        self.assertNotIn("or --size product", retry)
        self.assertNotIn("not retried", retry)
        self.inner.assert_clean_origin()

    def test_over_line_cap_hard_stops_when_retries_exhausted(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        over = {"mode": "noop", "write": {"src/calc.py": _calc(260)}}
        proc, receipt = self._run(task, [over, over, over, over], retries=2)
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertEqual(data["status"], "PASS-REJECTED")
        self.assertEqual(data["reason"], "review-rejected")
        self.assertEqual(data["attempts"], 3)
        self.assertFalse((receipt / "attempt-4").exists())
        self.assertEqual(self.count.read_text(encoding="utf-8").strip(), "3")
        self.assertIsNone(data["commit"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertEqual(self._chat(), [])
        rows = _prompts(self.prompts)
        self.assertEqual(len(rows), 3)
        self.assertIn("changed lines", rows[1]["prompt"])
        self.assertIn("changed lines", rows[2]["prompt"])
        self.inner.assert_clean_origin()

    def test_under_line_cap_does_not_retry(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        fit = {"mode": "noop", "write": {"src/calc.py": _calc(248)}}
        proc, receipt = self._run(task, [fit, fit], retries=2)
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["attempts"], 1)
        self.assertFalse((receipt / "attempt-2").exists())
        self.assertEqual(self.count.read_text(encoding="utf-8").strip(), "1")
        rows = _prompts(self.prompts)
        self.assertEqual(len(rows), 1)
        self.assertNotIn("changed lines", rows[0]["prompt"])
        size = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(size["checks"]["size"]["lines"], 250)
        self.assertTrue(size["checks"]["size"]["ok"])
        self.inner.assert_clean_origin()


if __name__ == "__main__":
    unittest.main()
