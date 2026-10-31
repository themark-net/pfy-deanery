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
from pathlib import Path

import tests.test_pfy_build_local as harness


def _prompts(path):
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


class ReviewHelpTests(unittest.TestCase):
    def test_help_says_review_is_on_and_names_the_size_cap(self):
        env = os.environ.copy()
        env["TMPDIR"] = str(harness.ROOT / "tmp" / "scratch")
        proc = subprocess.run(
            [str(harness.ROOT / "pfy"), "build", "--local", "--help"],
            cwd=harness.ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = " ".join((proc.stdout or "").split())
        self.assertIn("Review is on by default", text)
        self.assertIn("--no-review", text)
        self.assertIn("3 changed files", text)
        self.assertIn("250 added plus removed lines", text)


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
            "PFY_LOCAL_BUILD_TEST_SEAM": "1",
        }

    def _run(self, task, steps, extra=None, timeout=90, env_extra=None):
        self._plan(steps)
        env = self._env()
        if env_extra:
            env.update(env_extra)
        return self.inner.run_build(
            "plan",
            extra=extra,
            env_extra=env,
            timeout=timeout,
            task=task,
        )

    def _receipt(self, proc, receipt):
        return self.inner.receipt(proc, receipt)

    def test_out_of_scope_patch_is_rejected_and_the_retry_passes(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        steps = [
            {"mode": "fix", "write": {"src/notes.py": "outside PFY_SCOPE_DIFF_MARKER\n"}},
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
        self.assertIn("PFY_SCOPE_DIFF_MARKER", rows[1]["prompt"])
        self.assertIn("Previous diff:", rows[1]["prompt"])
        self.assertIsNotNone(data["commit"])
        names = harness._git(
            self.inner.repo,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            data["commit"],
        ).strip().splitlines()
        self.assertEqual(names, ["src/calc.py"])

    def _commit_gate(self, body, name):
        path = self.inner.repo / "tools" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        self.inner.commit_base("add %s" % name)
        return "python3 tools/%s" % name

    def test_no_change_runs_the_gate_and_puts_the_tail_in_the_next_prompt(self):
        marker = "PFY_NO_CHANGE_GATE_MARKER"
        cmd = self._commit_gate(
            "print(%r)\nprint('Ran 1 test in 0.001s')\nprint('FAILED (failures=1)')\nraise SystemExit(1)\n" % marker,
            "no_change_gate.py",
        )
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "noop"}, {"mode": "noop"}],
            extra=["--retries", "1", "--test-cmd", cmd],
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["reason"], "no-change")
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["attempts"], 2)
        self.assertIsNone(data["branch"])
        self.assertIsNone(data["commit"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertIn(marker, (data.get("tests_after") or {}).get("tail") or "")
        rows = _prompts(self.prompts)
        self.assertGreaterEqual(len(rows), 2)
        self.assertIn(marker, rows[1]["prompt"])
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(first["reason"], "no-change")
        self.assertIn(marker, first["tests_after"]["tail"])
        chat = [path for path, _payload in self.inner.httpd.posts if "chat" in path]
        self.assertEqual(chat, [])
        self.inner.assert_clean_origin()

    def test_green_gate_and_empty_diff_is_no_change_when_retries_are_spent(self):
        marker = "PFY_GREEN_EMPTY_DIFF"
        cmd = self._commit_gate(
            "print(%r)\nprint('Ran 1 test in 0.001s')\nprint('OK')\n" % marker,
            "green_gate.py",
        )
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "noop"}],
            extra=["--retries", "0", "--test-cmd", cmd],
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "no-change")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["branch"])
        self.assertIsNone(data["commit"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertEqual(data["tests_after"]["exit"], 0)
        self.assertIn(marker, data["tests_after"]["tail"])
        chat = [path for path, _payload in self.inner.httpd.posts if "chat" in path]
        self.assertEqual(chat, [])
        self.inner.assert_clean_origin()

    def test_gitignored_extra_file_is_absent_from_the_commit(self):
        repo = self.inner.repo
        ignore = repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "pipelines/\n", encoding="utf-8")
        self.inner.commit_base("ignore pipeline receipts")
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        steps = [
            {
                "mode": "fix",
                "write": {"pipelines/smoke/kander/latest.json": '{"ok": true}\n'},
            }
        ]
        proc, receipt = self._run(task, steps)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertIsNotNone(data["commit"])
        self.assertNotIn("pipelines/smoke/kander/latest.json", data["files_changed"])
        names = harness._git(
            repo, "diff-tree", "--no-commit-id", "--name-only", "-r", data["commit"]
        ).strip().splitlines()
        self.assertEqual(names, ["src/calc.py"])
        shown = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", "%s:pipelines/smoke/kander/latest.json" % data["commit"]],
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(shown.returncode, 0, shown.stderr)
        self.inner.assert_clean_origin()

    def test_staged_names_that_differ_reset_and_do_not_branch(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix"}],
            env_extra={"PFY_LOCAL_BUILD_INJECT_EXTRA_STAGE": "1"},
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["reason"], "scope-commit-mismatch")
        self.assertEqual(data["status"], "FAIL")
        self.assertIsNone(data["branch"])
        self.assertIsNone(data["commit"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.inner.assert_clean_origin()
        worktree = data["worktree"]
        self.assertTrue(worktree)
        cached = harness._git(worktree, "diff", "--cached", "--name-only")
        self.assertEqual(cached.strip(), "")
        log = harness._git(self.inner.repo, "log", "--all", "--name-only", "--pretty=format:")
        self.assertNotIn("injected-extra.txt", log)

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

    def test_previous_diff_reaches_the_retry_prompt(self):
        """Kills M7: the retry prompt drops the previous diff and keeps only the reasons."""
        self.inner.httpd.review_queue = [
            json.dumps({"verdict": "reject", "reasons": ["too broad"]}),
            json.dumps({"verdict": "accept", "reasons": []}),
        ]
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "fix"}, {"mode": "fix"}], extra=["--retries", "1"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["attempts"], 2)
        rows = _prompts(self.prompts)
        self.assertGreaterEqual(len(rows), 2)
        first_prompt = rows[0]["prompt"]
        retry = rows[1]["prompt"]
        self.assertNotIn("return a + b + 1", first_prompt)
        self.assertIn("too broad", retry)
        self.assertIn("Previous diff:", retry)
        removed = "return a + b + 1"
        self.assertIn(removed, retry)
        self.assertLess(retry.index("Previous diff:"), retry.index(removed))
        self.assertLess(retry.index("Reasons:"), retry.index("Previous diff:"))

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
        self.assertIn("Previous diff:", rows[1]["prompt"])
        self.assertIn("return a + b + 5", rows[1]["prompt"])

    def test_stub_binds_stay_off_unless_the_test_seam_is_on(self):
        notes = self.inner.tmp / "seam-notes"
        notes.mkdir()
        plan = notes / "plan.json"
        plan.write_text(json.dumps([{"mode": "fix"}]), encoding="utf-8")
        count = notes / "count"
        prompts = notes / "prompts.jsonl"
        stub_env = {
            "PFY_STUB_PLAN": str(plan),
            "PFY_STUB_COUNT": str(count),
            "PFY_STUB_PROMPTS": str(prompts),
        }
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        off, off_receipt = self.inner.run_build(
            "fix",
            extra=["--no-review"],
            env_extra={**stub_env, "PFY_LOCAL_BUILD_TEST_SEAM": "0"},
            task=task,
        )
        self.assertEqual(off.returncode, 0, off.stdout + off.stderr)
        off_data = self._receipt(off, off_receipt)
        self.assertEqual(off_data["status"], "PASS")
        self.assertEqual(off_data.get("sandbox_extra_rw") or [], [])

        on, on_receipt = self.inner.run_build(
            "fix",
            extra=["--no-review"],
            env_extra={**stub_env, "PFY_LOCAL_BUILD_TEST_SEAM": "1"},
            task=task,
        )
        self.assertEqual(on.returncode, 0, on.stdout + on.stderr)
        on_data = self._receipt(on, on_receipt)
        self.assertEqual(on_data["status"], "PASS")
        binds = on_data.get("sandbox_extra_rw") or []
        self.assertIn(str(notes.resolve()), binds)

    def test_missing_allow_list_warns_and_a_named_list_does_not(self):
        bare, bare_receipt = self.inner.run_build(
            "fix",
            extra=["--no-review"],
            task="fix add so one plus one is two",
        )
        self.assertEqual(bare.returncode, 0, bare.stdout + bare.stderr)
        bare_data = self._receipt(bare, bare_receipt)
        self.assertEqual(bare_data["status"], "PASS")
        self.assertIn("no allow list", " ".join(bare_data.get("warnings") or []))

        named, named_receipt = self._run(
            "fix add so one plus one is two\nfiles: src/calc.py\n",
            [{"mode": "fix"}],
            extra=["--no-review"],
        )
        self.assertEqual(named.returncode, 0, named.stdout + named.stderr)
        named_data = self._receipt(named, named_receipt)
        self.assertEqual(named_data["status"], "PASS")
        self.assertNotIn("no allow list", " ".join(named_data.get("warnings") or []))

        flagged, flagged_receipt = self.inner.run_build(
            "fix",
            extra=["--no-review", "--allow-path", "src/*.py"],
            task="fix add so one plus one is two",
        )
        self.assertEqual(flagged.returncode, 0, flagged.stdout + flagged.stderr)
        flagged_data = self._receipt(flagged, flagged_receipt)
        self.assertEqual(flagged_data["status"], "PASS")
        self.assertNotIn("no allow list", " ".join(flagged_data.get("warnings") or []))

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

    def test_ignored_out_of_scope_file_is_written_and_left_out_of_the_commit(self):
        repo = self.inner.repo
        ignore = repo / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "secret-scratch/\n", encoding="utf-8")
        self.inner.commit_base("ignore secret scratch")
        secret = "PFY_IGNORED_UNREVIEWED_TOKEN"
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        steps = [{"mode": "fix", "write": {"secret-scratch/note.txt": secret + "\n"}}]
        proc, receipt = self._run(task, steps, extra=["--keep-worktree"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertIsNotNone(data["commit"])
        ignored = Path(data["worktree"]) / "secret-scratch" / "note.txt"
        self.assertTrue(ignored.is_file(), data["worktree"])
        self.assertIn(secret, ignored.read_text(encoding="utf-8"))
        self.assertNotIn("secret-scratch/note.txt", data["files_changed"])
        names = harness._git(
            repo, "diff-tree", "--no-commit-id", "--name-only", "-r", data["commit"]
        ).strip().splitlines()
        self.assertEqual(names, ["src/calc.py"])
        tree = harness._git(repo, "ls-tree", "-r", "--name-only", data["commit"])
        self.assertNotIn("secret-scratch/note.txt", tree.splitlines())
        reviewed = [
            json.dumps(payload)
            for path, payload in self.inner.httpd.posts
            if "chat" in path and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertTrue(reviewed, "reviewer was not called")
        for blob in reviewed:
            self.assertNotIn(secret, blob)
        self.inner.assert_clean_origin()

    def test_reviewer_http_error_does_not_commit(self):
        self.inner.httpd.review_http_status = 500
        self.inner.httpd.review_queue = [
            json.dumps({"verdict": "accept", "reasons": ["should not be read"]}),
        ]
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "fix"}], extra=["--retries", "2"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "reviewer-unavailable")
        self.assertEqual(data["reason"], "reviewer-unavailable")
        self.assertNotEqual(data["status"], "FAIL")
        self.assertNotEqual(data["status"], "TIMEOUT")
        self.assertNotEqual(data["status"], "PASS-REJECTED")
        self.assertIn("reviewer-unavailable", data.get("recovery") or "")
        self.assertIn("not a reject", data.get("recovery") or "")
        self.assertIn("Nothing was committed", data.get("recovery") or "")
        self.assertIn("Recovery:", data.get("recovery") or "")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertFalse((receipt / "attempt-2").exists())
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(first["status"], "reviewer-unavailable")
        self.assertEqual(first["reason"], "reviewer-unavailable")
        self.assertNotEqual(first["model_review"]["verdict"], "accept")
        self.assertNotEqual(first["model_review"]["verdict"], "reject")
        self.inner.assert_clean_origin()

    def test_review_timeout_does_not_commit(self):
        self.inner.httpd.review_block = threading.Event()
        self.inner.httpd.review_started = threading.Event()
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix"}],
            extra=["--timeout", "40", "--retries", "2"],
            timeout=150,
        )
        self.assertTrue(self.inner.httpd.review_started.is_set(), proc.stdout + proc.stderr)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertNotEqual(proc.returncode, harness.BUILD.EXIT_TIMEOUT)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "reviewer-unavailable")
        self.assertEqual(data["reason"], "reviewer-unavailable")
        self.assertNotEqual(data["status"], "FAIL")
        self.assertNotEqual(data["status"], "TIMEOUT")
        self.assertNotEqual(data["status"], "PASS-REJECTED")
        self.assertIn("not a reject", data.get("recovery") or "")
        self.assertIn("was not retried", data.get("recovery") or "")
        self.assertIn("Recovery:", data.get("recovery") or "")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertFalse((receipt / "attempt-2").exists())
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(first["status"], "reviewer-unavailable")
        self.assertIsNotNone(first["checks"])
        self.inner.assert_clean_origin()

    def test_overall_timeout_stops_the_review_loop_without_a_commit(self):
        """The wall cap covers the review call, not only the agent timeout."""
        self.inner.httpd.review_block = threading.Event()
        self.inner.httpd.review_started = threading.Event()
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix"}],
            extra=["--timeout", "60", "--overall-timeout", "35", "--retries", "2"],
            timeout=90,
        )
        self.assertTrue(self.inner.httpd.review_started.is_set(), proc.stdout + proc.stderr)
        self.assertEqual(proc.returncode, harness.BUILD.EXIT_TIMEOUT, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "TIMEOUT")
        self.assertEqual(data["reason"], "overall-timeout")
        self.assertNotEqual(data["reason"], "timeout")
        self.assertNotEqual(data["status"], "reviewer-unavailable")
        self.assertNotEqual(data["status"], "FAIL")
        self.assertIn("wall-clock cap", data.get("recovery") or "")
        self.assertIn("Nothing was committed", data.get("recovery") or "")
        self.assertIn("Recovery:", data.get("recovery") or "")
        self.assertIn("--overall-timeout", data.get("recovery") or "")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertFalse((receipt / "attempt-2").exists())
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(first["status"], "TIMEOUT")
        self.assertEqual(first["reason"], "overall-timeout")
        self.inner.assert_clean_origin()

    def test_empty_diff_sent_toward_the_reviewer_does_not_commit(self):
        cmd = self._commit_gate(
            "print('PFY_EMPTY_DIFF_GATE')\nprint('Ran 1 test in 0.001s')\nprint('OK')\n",
            "empty_diff_gate.py",
        )
        task = "fix add so one plus one is two\n"
        steps = [{"mode": "noop", "symlink": {"src/hole": "missing-target"}}]
        proc, receipt = self._run(
            task,
            steps,
            extra=["--retries", "2", "--test-cmd", cmd],
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "review-empty-diff")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        chat = [
            json.dumps(payload)
            for path, payload in self.inner.httpd.posts
            if "chat" in path and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertEqual(chat, [])
        log = harness._git(self.inner.repo, "log", "--all", "--name-only", "--pretty=format:")
        self.assertNotIn("src/hole", log)
        self.inner.assert_clean_origin()

    def test_scope_retries_spent_do_not_commit(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        steps = [{"mode": "fix", "write": {"src/notes.py": "outside\n"}}]
        proc, receipt = self._run(task, steps, extra=["--retries", "0"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS-REJECTED")
        self.assertEqual(data["reason"], "review-rejected")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertIn("src/notes.py", first["checks"]["scope"]["outside"])
        self.inner.assert_clean_origin()

    def test_wiring_retries_spent_do_not_commit(self):
        task = (
            "fix add so one plus one is two\n"
            "files: src/calc.py, tests/test_calc.py\n"
            "require: PFY_SMOKE_RECEIPT_DIR in tests/test_calc.py\n"
        )
        proc, receipt = self._run(task, [{"mode": "fix"}], extra=["--retries", "0"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS-REJECTED")
        self.assertEqual(data["reason"], "review-rejected")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        missing = first["checks"]["wiring"]["missing"]
        self.assertTrue(any("tests/test_calc.py" in item for item in missing), missing)
        self.inner.assert_clean_origin()

    def test_previous_diff_marker_stays_inside_the_previous_diff_section(self):
        marker = "PFY_PREV_DIFF_MARKER_14"
        self.inner.httpd.review_queue = [
            json.dumps({"verdict": "reject", "reasons": ["too broad"]}),
            json.dumps({"verdict": "accept", "reasons": []}),
        ]
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        steps = [
            {"mode": "fix", "append": {"src/calc.py": "\n# %s\n" % marker}},
            {"mode": "fix"},
        ]
        proc, receipt = self._run(task, steps, extra=["--retries", "1"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["attempts"], 2)
        rows = _prompts(self.prompts)
        self.assertGreaterEqual(len(rows), 2)
        self.assertIn("Previous diff:", rows[1]["prompt"])
        self.assertIn(marker, rows[1]["prompt"])
        self.assertNotIn(marker, rows[1]["prompt"].split("Previous diff:", 1)[0])
        self.inner.assert_clean_origin()

    def test_scope_check_skipped_is_on_stderr_and_the_receipt(self):
        phrase = "scope check skipped: no allow list"
        bare, bare_receipt = self.inner.run_build(
            "fix",
            task="fix add so one plus one is two",
        )
        self.assertEqual(bare.returncode, 0, bare.stdout + bare.stderr)
        self.assertIn(phrase, bare.stderr)
        bare_data = self._receipt(bare, bare_receipt)
        self.assertEqual(bare_data["status"], "PASS")
        self.assertIn(phrase, bare_data["warnings"])
        self.assertEqual(bare_data["warnings"].count(phrase), 1)

        named, named_receipt = self._run(
            "fix add so one plus one is two\nfiles: src/calc.py\n",
            [{"mode": "fix"}],
        )
        self.assertEqual(named.returncode, 0, named.stdout + named.stderr)
        self.assertNotIn(phrase, named.stderr)
        named_data = self._receipt(named, named_receipt)
        self.assertEqual(named_data["status"], "PASS")
        self.assertNotIn(phrase, named_data.get("warnings") or [])

        flagged, flagged_receipt = self.inner.run_build(
            "fix",
            extra=["--allow-path", "src/calc.py"],
            task="fix add so one plus one is two",
        )
        self.assertEqual(flagged.returncode, 0, flagged.stdout + flagged.stderr)
        self.assertNotIn(phrase, flagged.stderr)
        flagged_data = self._receipt(flagged, flagged_receipt)
        self.assertEqual(flagged_data["status"], "PASS")
        self.assertNotIn(phrase, flagged_data.get("warnings") or [])
        self.assertEqual(flagged_data["review"]["allow_path"], ["src/calc.py"])

    def test_no_review_does_not_retry_a_red_gate(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "worse"}, {"mode": "fix"}],
            extra=["--no-review", "--retries", "2"],
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "tests-failed")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertFalse(data["review"]["enabled"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertFalse((receipt / "attempt-2").exists())
        log = (receipt / "agent.log").read_text(encoding="utf-8")
        self.assertEqual(log.count("PFY_STUB_REPORT "), 1)
        self.inner.assert_clean_origin()
