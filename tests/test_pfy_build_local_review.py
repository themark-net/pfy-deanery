"""Review-and-retry behavior for ./pfy build --local.

Stub opencode and the stub Ollama in test_pfy_build_local.py. These tests
fail on a runner that has no review loop: the new flags are rejected, or a
green out-of-scope patch is committed as PASS.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
import unittest

import tests.test_pfy_build_local as harness


def _prompts(path):
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


class ReviewLoopTests(unittest.TestCase):
    def setUp(self):
        self.inner = harness.LocalBuildTests()
        self.inner.setUp()
        # Sibling of the repo, not its parent. The sandbox bind is this
        # directory only, so it does not uncover the hidden checkout.
        notes = self.inner.tmp / "stub-notes"
        notes.mkdir()
        self.prompts = notes / "prompts.jsonl"
        self.plan = notes / "plan.json"
        self.count = notes / "attempt-count"

    def tearDown(self):
        blocker = getattr(self.inner.httpd, "review_block", None)
        if blocker is not None:
            blocker.set()
        self.inner.tearDown()

    def _plan(self, steps):
        self.plan.write_text(json.dumps(steps), encoding="utf-8")

    def _env(self):
        return {
            "PFY_STUB_PLAN": str(self.plan),
            "PFY_STUB_COUNT": str(self.count),
            "PFY_STUB_PROMPTS": str(self.prompts),
        }

    def _run(self, task, steps, extra=None, timeout=90):
        self._plan(steps)
        return self.inner.run_build(
            "plan",
            extra=extra,
            env_extra=self._env(),
            timeout=timeout,
            task=task,
        )

    def _receipt(self, proc, receipt):
        return self.inner.receipt(proc, receipt)

    def test_out_of_scope_patch_is_rejected_and_the_retry_passes(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        steps = [
            {"mode": "fix", "write": {"src/notes.py": "outside\n"}},
            {"mode": "fix"},
        ]
        proc, receipt = self._run(task, steps)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["attempts"], 2)
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        outside = first["checks"]["scope"]["outside"]
        self.assertIn("src/notes.py", outside)
        rows = _prompts(self.prompts)
        self.assertGreaterEqual(len(rows), 2)
        self.assertIn("src/notes.py", rows[1]["prompt"])
        self.assertIsNotNone(data["commit"])

    def test_missing_wiring_names_the_module_and_the_retry_wires_both(self):
        task = (
            "fix add so one plus one is two\n"
            "files: src/calc.py, tests/test_calc.py, tests/test_other.py\n"
            "require: PFY_SMOKE_RECEIPT_DIR in tests/test_calc.py, tests/test_other.py\n"
        )
        steps = [
            {"mode": "fix", "append": {"tests/test_calc.py": "\nPFY_SMOKE_RECEIPT_DIR = 'one'\n"}},
            {
                "mode": "fix",
                "append": {
                    "tests/test_calc.py": "\nPFY_SMOKE_RECEIPT_DIR = 'one'\n",
                    "tests/test_other.py": "\nPFY_SMOKE_RECEIPT_DIR = 'two'\n",
                },
            },
        ]
        proc, receipt = self._run(
            task,
            steps,
            extra=[
                "--writable-test",
                "tests/test_calc.py",
                "--writable-test",
                "tests/test_other.py",
            ],
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["attempts"], 2)
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        blob = json.dumps(first)
        self.assertIn("tests/test_other.py", blob)
        self.assertNotIn("tests/test_calc.py", json.dumps(first["checks"]["wiring"]["missing"]))
        rows = _prompts(self.prompts)
        self.assertIn("tests/test_other.py", rows[1]["prompt"])

    def test_a_reviewer_that_keeps_rejecting_stops_at_three_attempts(self):
        self.inner.httpd.review_queue = [
            json.dumps({"verdict": "reject", "reasons": ["too broad"]}),
            json.dumps({"verdict": "reject", "reasons": ["still broad"]}),
            json.dumps({"verdict": "reject", "reasons": ["no"]}),
            json.dumps({"verdict": "accept", "reasons": ["should not be asked"]}),
        ]
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "fix"}])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS-REJECTED")
        self.assertEqual(data["attempts"], 3)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        for number in (1, 2, 3):
            path = receipt / ("attempt-%d" % number) / "receipt.json"
            self.assertTrue(path.is_file(), path)
        self.assertFalse((receipt / "attempt-4" / "receipt.json").exists())
        self.assertEqual(len(self.inner.httpd.review_queue), 1)

    def test_unparseable_review_is_a_reject_and_the_reason_is_fed_back(self):
        self.inner.httpd.review_queue = [
            "not json at all",
            json.dumps({"verdict": "accept", "reasons": []}),
        ]
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "fix"}], extra=["--retries", "1"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["attempts"], 2)
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertIn("review-unparseable", first["model_review"]["reasons"])
        self.assertNotEqual(first["model_review"]["verdict"], "accept")
        rows = _prompts(self.prompts)
        self.assertIn("review-unparseable", rows[1]["prompt"])

    def test_gate_fail_is_retried_and_the_tail_reaches_the_next_prompt(self):
        self.inner.httpd.review_queue = [
            json.dumps({"verdict": "accept", "reasons": []}),
        ]
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "worse"}, {"mode": "fix"}])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["attempts"], 2)
        rows = _prompts(self.prompts)
        self.assertGreaterEqual(len(rows), 2)
        self.assertIn("tests-failed", rows[1]["prompt"])
        self.assertIn("AssertionError", rows[1]["prompt"])

    def test_no_review_is_one_attempt_and_a_green_gate_passes(self):
        proc, receipt = self.inner.run_build("fix", extra=["--no-review"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["attempts"], 1)
        self.assertFalse(data["review"]["enabled"])
        self.assertFalse((receipt / "attempt-2").exists())
        chat = [path for path, _payload in self.inner.httpd.posts if "chat" in path]
        self.assertEqual(chat, [])
        log = (receipt / "agent.log").read_text(encoding="utf-8")
        self.assertEqual(log.count("PFY_STUB_REPORT "), 1)

    def test_kill_during_review_leaves_an_aborted_receipt_and_the_next_run_is_clean(self):
        self.inner.httpd.review_block = threading.Event()
        self.inner.httpd.review_started = threading.Event()
        cmd, receipt = self.inner.command(
            "fix",
            extra=["--timeout", "60"],
            task="fix add so one plus one is two\nfiles: src/calc.py\n",
        )
        proc = subprocess.Popen(
            cmd,
            cwd=self.inner.repo,
            env=self.inner.env("fix"),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            started = self.inner.httpd.review_started.wait(timeout=40)
            self.assertTrue(started, "review call did not start")
            os.kill(proc.pid, signal.SIGKILL)
            proc.wait(timeout=5)
        finally:
            if proc.poll() is None:
                os.kill(proc.pid, signal.SIGKILL)
                proc.wait(timeout=5)
            self.inner.httpd.review_block.set()
        reap = subprocess.run(
            [str(harness.ROOT / "pfy"), "build", "--local", "--reap", "--repo", str(self.inner.repo)],
            cwd=self.inner.repo,
            env=self.inner.env("noop"),
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(reap.returncode, 0, reap.stdout + reap.stderr)
        aborted = json.loads((receipt / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(aborted["status"], "ABORTED")
        self.assertEqual(aborted["reason"], "no-receipt")
        self.inner.httpd.review_block = None
        self.inner.httpd.review_started = None
        self.inner.httpd.review_queue = []
        again, again_receipt = self.inner.run_build(
            "fix",
            task="fix add so one plus one is two\nfiles: src/calc.py\n",
        )
        self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
        data = self._receipt(again, again_receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertNotEqual(again_receipt, receipt)
