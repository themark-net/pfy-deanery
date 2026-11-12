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
import sys
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
        self.assertIn("40 changed files", text)
        self.assertIn("4000 added plus removed lines", text)


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

    def test_excluded_only_change_does_not_commit(self):
        """A diff that is only an excluded path must not reach git commit.

        Fail: .pytest_cache is the only change, the gate is green, and git
        commit of an empty index is recorded as commit-failed.
        Recover: reason no-reviewable-change, exit 1, no branch, caller HEAD
        unchanged.
        """
        cmd = self._commit_gate(
            "print('1 passed in 0.01s')\nraise SystemExit(0)\n",
            "always_ok.py",
        )
        proc, receipt = self._run(
            "touch only the pytest cache\n",
            [{"mode": "noop", "write": {".pytest_cache/README": "cache\n"}}],
            extra=["--no-review", "--test-cmd", cmd],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        data = self.inner.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "no-reviewable-change")
        self.assertEqual(data["status"], "FAIL")

    def test_inject_stage_does_nothing_when_the_test_seam_is_off(self):
        """PFY_LOCAL_BUILD_INJECT_EXTRA_STAGE must not write a file unless the seam is on.

        Fail: the inject env alone stages injected-extra.txt and the green
        fix becomes scope-commit-mismatch.
        Recover: with the seam off, the fix commits and that name is absent.
        With the seam on, the existing mismatch test still injects.
        """
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix"}],
            extra=["--no-review"],
            env_extra={
                "PFY_LOCAL_BUILD_TEST_SEAM": "0",
                "PFY_LOCAL_BUILD_INJECT_EXTRA_STAGE": "1",
            },
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertNotIn("injected-extra.txt", data.get("files_changed") or [])
        names = harness._git(
            self.inner.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", data["commit"]
        ).strip().splitlines()
        self.assertEqual(names, ["src/calc.py"])
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

    def test_missing_review_out_file_is_one_crash_and_does_not_retry(self):
        """A poster that never writes pfy-review-out.json must not be retried.

        Fail: python exits before that file exists, empty stdout is parsed as
        review-unparseable, and the loop tries again.
        Recover: reason review-crashed, exit 1, one attempt, no commit.
        """
        fake_dir = self.inner.tmp / "no-review-python"
        fake_dir.mkdir()
        fake = fake_dir / "python3"
        fake.write_text(
            "#!/bin/sh\n"
            "for arg in \"$@\"; do\n"
            "  case \"$arg\" in\n"
            "    *pfy-review-post.py*) exit 1 ;;\n"
            "  esac\n"
            "done\n"
            "exec %s \"$@\"\n" % sys.executable,
            encoding="utf-8",
        )
        fake.chmod(0o755)
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix"}],
            extra=["--retries", "2"],
            env_extra={"PATH": str(fake_dir) + os.pathsep + os.environ.get("PATH", "")},
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        data = self.inner.assert_no_commit(proc, receipt)
        self.assertEqual(data["reason"], "review-crashed")
        self.assertEqual(data["attempts"], 1)
        self.assertFalse((receipt / "attempt-2").exists())

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
        phrase = "scope check skipped: no allow list"
        self.assertIn(phrase, " ".join(bare_data.get("warnings") or []))
        self.assertIn(phrase, bare.stderr or "")

        named, named_receipt = self._run(
            "fix add so one plus one is two\nfiles: src/calc.py\n",
            [{"mode": "fix"}],
            extra=["--no-review"],
        )
        self.assertEqual(named.returncode, 0, named.stdout + named.stderr)
        named_data = self._receipt(named, named_receipt)
        self.assertEqual(named_data["status"], "PASS")
        self.assertNotIn(phrase, " ".join(named_data.get("warnings") or []))
        self.assertNotIn(phrase, named.stderr or "")

        flagged, flagged_receipt = self.inner.run_build(
            "fix",
            extra=["--no-review", "--allow-path", "src/*.py"],
            task="fix add so one plus one is two",
        )
        self.assertEqual(flagged.returncode, 0, flagged.stdout + flagged.stderr)
        flagged_data = self._receipt(flagged, flagged_receipt)
        self.assertEqual(flagged_data["status"], "PASS")
        self.assertNotIn(phrase, " ".join(flagged_data.get("warnings") or []))
        self.assertNotIn(phrase, flagged.stderr or "")

    def test_no_review_is_one_attempt_and_a_green_gate_passes(self):
        proc, receipt = self.inner.run_build("fix", extra=["--no-review"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["attempts"], 1)
        self.assertFalse(data["review"]["enabled"])
        self.assertIs(data["review"]["same_model"], True)
        self.assertEqual(data["model"], "fixture:small")
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
        steps = [{"mode": "noop", "gitdir": ["src/hole"]}]
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

    def test_poster_with_no_out_file_is_review_crashed_and_not_retried(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix"}, {"mode": "fix"}],
            extra=["--retries", "2"],
            env_extra={"PFY_LOCAL_BUILD_REVIEW_CRASH": "1"},
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "review-crashed")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertFalse((receipt / "attempt-2").exists())
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(first["reason"], "review-crashed")
        self.assertIn("review-crashed", first["model_review"]["reasons"])
        self.assertNotIn("review-unparseable", first["model_review"]["reasons"])
        self.inner.assert_clean_origin()

        off, off_receipt = self.inner.run_build(
            "fix",
            extra=["--retries", "2"],
            env_extra={"PFY_LOCAL_BUILD_REVIEW_CRASH": "1"},
            task=task,
        )
        self.assertEqual(off.returncode, 0, off.stdout + off.stderr)
        off_data = self._receipt(off, off_receipt)
        self.assertEqual(off_data["status"], "PASS")
        self.assertNotEqual(off_data["reason"], "review-crashed")
        self.assertIsNotNone(off_data["commit"])

    def test_only_excluded_paths_are_no_reviewable_change(self):
        cmd = self._commit_gate(
            "print('PFY_EXCLUDED_ONLY_GATE')\nprint('Ran 1 test in 0.001s')\nprint('OK')\n",
            "excluded_only_gate.py",
        )
        task = "fix add so one plus one is two\nfiles: .pytest_cache/note.txt\n"
        steps = [{"mode": "noop", "write": {".pytest_cache/note.txt": "only excluded\n"}}]
        proc, receipt = self._run(
            task,
            steps,
            extra=["--retries", "2", "--test-cmd", cmd],
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "no-reviewable-change")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["branch"])
        self.assertIsNone(data["commit"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        worktree = data["worktree"]
        self.assertTrue(worktree)
        head = harness._git(worktree, "rev-parse", "HEAD").strip()
        self.assertEqual(head, data["base_sha"])
        cached = harness._git(worktree, "diff", "--cached", "--name-only")
        self.assertEqual(cached.strip(), "")
        log = harness._git(self.inner.repo, "log", "--all", "--name-only", "--pretty=format:")
        self.assertNotIn(".pytest_cache/note.txt", log)
        reviews = [
            payload
            for path, payload in self.inner.httpd.posts
            if "chat" in path and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertEqual(len(reviews), 1)
        self.assertFalse((receipt / "attempt-2").exists())
        self.inner.assert_clean_origin()

    def test_receipt_says_the_reviewer_is_the_same_model(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "fix"}])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["model"], "fixture:small")
        self.assertIs(data["review"]["same_model"], True)
        self.assertEqual(data["review"]["reviewer"], "same local model as the agent")
        reviews = [
            payload
            for path, payload in self.inner.httpd.posts
            if "chat" in path and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertTrue(reviews, "reviewer was not called")
        self.assertEqual(reviews[0]["model"], data["model"])
        self.inner.assert_clean_origin()

    def test_seam_off_does_not_bind_stub_notes_or_inject_a_file(self):
        notes = self.inner.tmp / "seam-off"
        notes.mkdir()
        plan = notes / "plan.json"
        plan.write_text(json.dumps([{"mode": "fix"}]), encoding="utf-8")
        count = notes / "count"
        prompts = notes / "prompts.jsonl"
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self.inner.run_build(
            "plan",
            extra=["--retries", "0"],
            env_extra={
                "PFY_STUB_PLAN": str(plan),
                "PFY_STUB_COUNT": str(count),
                "PFY_STUB_PROMPTS": str(prompts),
                "PFY_LOCAL_BUILD_INJECT_EXTRA_STAGE": "1",
            },
            task=task,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertIsNotNone(data["commit"])
        names = harness._git(
            self.inner.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", data["commit"]
        ).strip().splitlines()
        self.assertEqual(names, ["src/calc.py"])
        log = harness._git(self.inner.repo, "log", "--all", "--name-only", "--pretty=format:")
        self.assertNotIn("injected-extra.txt", log)
        self.assertNotEqual(data["reason"], "scope-commit-mismatch")
        if str(data.get("sandbox") or "").startswith("bwrap"):
            self.assertFalse(prompts.is_file() and prompts.stat().st_size > 0, prompts)
            self.assertFalse(count.is_file(), count)
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
        self.assertEqual(data["review"]["retries"], 0)
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertFalse((receipt / "attempt-2").exists())
        log = (receipt / "agent.log").read_text(encoding="utf-8")
        self.assertEqual(log.count("PFY_STUB_REPORT "), 1)
        self.inner.assert_clean_origin()

    def test_gate_rewrite_of_reviewed_file_does_not_commit(self):
        # The gate imports src.calc and the module appends a line the reviewer
        # never saw. That line must not land in a commit.
        body = (
            "from pathlib import Path as _P\n"
            "_p = _P(__file__)\n"
            "_t = 'EV' + 'IL_' + 'GATE'\n"
            "if _t not in _p.read_text():\n"
            "    _p.write_text(_p.read_text() + _t + ' = 1\\n')\n"
            "def add(a, b):\n"
            "    return a + b\n"
        )
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "write": {"src/calc.py": body}}],
            extra=["--retries", "2"],
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "gate-modified-reviewed-file")
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertFalse((receipt / "attempt-2").exists())
        blob = json.dumps(self.inner.httpd.posts)
        self.assertNotIn("EVIL_GATE = 1", blob)
        for path in receipt.rglob("*"):
            if path.is_file() and not path.is_symlink():
                self.assertNotIn("EVIL_GATE = 1", path.read_text(encoding="utf-8", errors="replace"))
        self.inner.assert_clean_origin()

    def _commit_mode(self, sha, rel):
        text = harness._git(self.inner.repo, "ls-tree", sha, "--", rel)
        line = text.strip().splitlines()
        self.assertTrue(line, rel)
        return line[0].split()[0]

    def test_gate_executable_bit_does_not_commit(self):
        # The gate imports src.calc, which sets the executable bit. The
        # reviewer never saw 100755. That mode must not land in a commit.
        body = (
            "import os as _os\n"
            "from pathlib import Path as _P\n"
            "_p = _P(__file__)\n"
            "_m = _p.stat().st_mode\n"
            "if not (_m & 0o111):\n"
            "    _p.chmod(_m | 0o111)\n"
            "def add(a, b):\n"
            "    return a + b\n"
        )
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "fix", "write": {"src/calc.py": body}}])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "gate-modified-reviewed-file")
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.inner.assert_clean_origin()

    def test_gate_clearing_executable_bit_does_not_commit(self):
        # The agent marks the file executable. The gate then clears that bit.
        # The reviewed diff says 100755. The commit must not quietly store 100644.
        body = (
            "import os as _os\n"
            "from pathlib import Path as _P\n"
            "_p = _P(__file__)\n"
            "_m = _p.stat().st_mode\n"
            "if _m & 0o111:\n"
            "    _p.chmod(_m & ~0o111)\n"
            "def add(a, b):\n"
            "    return a + b\n"
        )
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "write": {"src/calc.py": body}, "chmod": {"src/calc.py": 0o755}}],
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "gate-modified-reviewed-file")
        self.assertIsNone(data["commit"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.inner.assert_clean_origin()

    def test_non_git_mode_tweak_during_the_gate_still_commits(self):
        # 0600 and 0644 are both git mode 100644. The gate may tighten the
        # unix mode. The commit still matches the reviewed blob and git mode.
        body = (
            "import os as _os\n"
            "from pathlib import Path as _P\n"
            "_p = _P(__file__)\n"
            "if (_p.stat().st_mode & 0o777) != 0o600:\n"
            "    _p.chmod(0o600)\n"
            "def add(a, b):\n"
            "    return a + b\n"
        )
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "fix", "write": {"src/calc.py": body}}])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(self._commit_mode(data["commit"], "src/calc.py"), "100644")
        shown = harness._git(self.inner.repo, "show", "%s:src/calc.py" % data["commit"])
        self.assertIn("return a + b\n", shown)
        self.assertNotIn("100755", json.dumps(self.inner.httpd.posts))
        self.inner.assert_clean_origin()

    def test_agent_executable_bit_is_what_gets_committed(self):
        # The agent sets the bit before review. The gate does not change it.
        # The reviewer sees 100755 and the commit stores 100755.
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "fix", "chmod": {"src/calc.py": 0o755}}])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(self._commit_mode(data["commit"], "src/calc.py"), "100755")
        reviewed = [
            json.dumps(payload)
            for path, payload in self.inner.httpd.posts
            if "chat" in path and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertEqual(len(reviewed), 1)
        self.assertIn("100755", reviewed[0])
        self.inner.assert_clean_origin()

    def _sentinel_file(self):
        marker = "PFY_SYMLINK_TARGET_SENTINEL_42"
        path = self.inner.tmp / "sentinel-outside.txt"
        path.write_text(marker + "\n", encoding="utf-8")
        return marker, path

    def _leak_hits(self, receipt, marker):
        hits = []
        if receipt is not None and Path(receipt).exists():
            for path in Path(receipt).rglob("*"):
                if not path.is_file() or path.is_symlink():
                    continue
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                if marker in text:
                    hits.append(str(path.relative_to(receipt)))
        if marker in json.dumps(self.inner.httpd.posts):
            hits.append("review-http")
        if self.prompts.is_file() and marker in self.prompts.read_text(encoding="utf-8", errors="replace"):
            hits.append("agent-prompts")
        return hits

    def test_in_scope_symlink_to_outside_is_not_committed(self):
        marker, path = self._sentinel_file()
        task = "fix add so one plus one is two\nfiles: src/calc.py, src/helper.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "symlink": {"src/helper.py": str(path)}}],
            extra=["--retries", "0"],
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertNotEqual(data["status"], "PASS")
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        outside = ((first.get("checks") or {}).get("scope") or {}).get("outside") or []
        self.assertIn("src/helper.py", outside, data.get("reason"))
        self.assertEqual(self._leak_hits(receipt, marker), [])
        log = harness._git(self.inner.repo, "log", "--all", "--name-only", "--pretty=format:")
        self.assertNotIn("src/helper.py", log)
        self.inner.assert_clean_origin()

    def test_out_of_scope_symlink_does_not_leak(self):
        marker, path = self._sentinel_file()
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "symlink": {"src/helper.py": str(path)}}],
            extra=["--retries", "2"],
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertNotEqual(data["status"], "PASS")
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(self._leak_hits(receipt, marker), [])
        self.assertEqual(len(list(receipt.glob("attempt-*"))), 3)
        self.inner.assert_clean_origin()

    def _hide_bwrap(self):
        """Point PATH at a bwrap that fails so --unsafe-no-sandbox is real.

        A working bwrap bind-mounts the worktree. A hardlink from that mount
        to a file outside it returns EXDEV, so the sandbox already blocks the
        attack. This helper builds the case the sandbox does not cover.
        """
        bindir = self.inner.tmp / "bin"
        bindir.mkdir(exist_ok=True)
        stub = bindir / "bwrap"
        stub.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        stub.chmod(0o755)
        return {"PATH": "%s%s%s" % (bindir, os.pathsep, os.environ.get("PATH", ""))}

    def test_in_scope_hardlink_to_outside_is_not_committed(self):
        marker, path = self._sentinel_file()
        task = "fix add so one plus one is two\nfiles: src/calc.py, src/helper.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "hardlink": {"src/helper.py": str(path)}}],
            extra=["--retries", "0", "--unsafe-no-sandbox"],
            env_extra=self._hide_bwrap(),
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], "hardlink-outside")
        self.assertIn("src/helper.py", data["files_changed"])
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertEqual(self._leak_hits(receipt, marker), [])
        self.inner.assert_clean_origin()

    def test_out_of_scope_hardlink_does_not_leak(self):
        marker, path = self._sentinel_file()
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "hardlink": {"src/helper.py": str(path)}}],
            extra=["--retries", "0", "--unsafe-no-sandbox"],
            env_extra=self._hide_bwrap(),
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["reason"], "hardlink-outside")
        self.assertIsNone(data["commit"])
        self.assertIn("src/helper.py", data["files_changed"])
        self.assertEqual(self._leak_hits(receipt, marker), [])
        self.inner.assert_clean_origin()

    def test_hardlink_inside_the_worktree_is_committed(self):
        # Two names, one inode, both inside the worktree. The bytes are the
        # agent's text. Review sees them and the commit keeps both paths.
        task = "fix add so one plus one is two\nfiles: src/calc.py, src/keep.py, src/also.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "write": {"src/keep.py": "INSIDE = 1\n"}, "hardlink": {"src/also.py": "src/keep.py"}}],
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertNotEqual(data["reason"], "hardlink-outside")
        for rel in ("src/keep.py", "src/also.py"):
            shown = harness._git(self.inner.repo, "show", "%s:%s" % (data["commit"], rel))
            self.assertEqual(shown, "INSIDE = 1\n")
        reviewed = [
            json.dumps(payload)
            for path, payload in self.inner.httpd.posts
            if "chat" in path and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertEqual(len(reviewed), 1)
        self.assertIn("INSIDE = 1", reviewed[0])
        self.inner.assert_clean_origin()

    def test_error_field_beside_accept_does_not_commit(self):
        accept = json.dumps({"verdict": "accept", "reasons": ["looks fine"]})
        self.inner.httpd.review_raw = {
            "error": "partial failure",
            "choices": [{"message": {"role": "assistant", "content": accept}}],
        }
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "fix"}], extra=["--retries", "2"])
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS-REJECTED")
        self.assertEqual(data["reason"], "review-rejected")
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        first = json.loads((receipt / "attempt-1" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(first["model_review"]["verdict"], "reject")
        self.assertNotEqual(first["model_review"]["verdict"], "accept")
        self.inner.assert_clean_origin()

    def test_reviewer_prompt_contains_the_changed_line(self):
        task = "fix add so one plus one is two\nfiles: src/calc.py\n"
        proc, receipt = self._run(task, [{"mode": "fix"}])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertIsNotNone(data["commit"])
        reviewed = [
            json.dumps(payload)
            for path, payload in self.inner.httpd.posts
            if "chat" in path and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertEqual(len(reviewed), 1)
        self.assertIn("return a + b", reviewed[0])
        self.assertIn("-    return a + b + 1", reviewed[0])
        self.inner.assert_clean_origin()

    def test_in_scope_rename_is_committed(self):
        (self.inner.repo / "src" / "old.py").write_text("X = 1\n", encoding="utf-8")
        self.inner.commit_base("add old")
        task = "fix add so one plus one is two\nfiles: src/calc.py, src/old.py, src/new.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "mv": [["src/old.py", "src/new.py"]]}],
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertNotEqual(data["reason"], "scope-commit-mismatch")
        text = harness._git(
            self.inner.repo,
            "diff",
            "--name-status",
            "--no-renames",
            data["base_sha"],
            data["commit"],
        )
        self.assertEqual(
            sorted(line for line in text.splitlines() if line.strip()),
            ["A\tsrc/new.py", "D\tsrc/old.py", "M\tsrc/calc.py"],
        )
        self.inner.assert_clean_origin()

    def test_unicode_path_in_scope_is_committed(self):
        name = "src/café.py"
        task = "fix add so one plus one is two\nfiles: src/calc.py, src/café.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "write": {name: "N = 1\n"}}],
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertIn(name, data["files_changed"])
        self.assertFalse(any("caf/" in path for path in data["files_changed"]))
        shown = subprocess.check_output(
            [
                "git",
                "-C",
                str(self.inner.repo),
                "-c",
                "core.quotepath=false",
                "ls-tree",
                "-r",
                "--name-only",
                data["commit"],
            ],
            text=True,
        )
        self.assertIn(name, shown.splitlines())
        reviewed = [
            payload["messages"][0]["content"]
            for path, payload in self.inner.httpd.posts
            if "chat" in path and isinstance(payload, dict) and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertTrue(reviewed)
        self.assertIn("café", reviewed[0])
        self.assertNotIn("\\303", reviewed[0])
        self.inner.assert_clean_origin()

    def _chat_posts(self):
        return [path for path, _payload in self.inner.httpd.posts if "chat" in path]

    def _assert_refused_before_review(self, proc, receipt, reason):
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "FAIL")
        self.assertEqual(data["reason"], reason)
        self.assertEqual(data["attempts"], 1)
        self.assertIsNone(data["commit"])
        self.assertIsNone(data["branch"])
        self.assertEqual(harness._branches(self.inner.repo), [])
        self.assertEqual(self._chat_posts(), [])
        self.assertFalse((receipt / "attempt-2").exists())
        self.inner.assert_clean_origin()
        return data

    def test_diff_over_the_prompt_cap_is_not_committed(self):
        # One line is over the 8000-character pack cap. The tail must still be
        # shown in some review prompt, then committed. A silent slice would hide it.
        body = "PAD = '" + ("x" * 9000) + "'\nEVIL_TAIL = 1\n"
        task = "fix add so one plus one is two\nfiles: src/calc.py, src/helper.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "write": {"src/helper.py": body}}],
            extra=["--retries", "2"],
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS", data)
        self.assertIsNotNone(data["commit"])
        self.assertIn("src/helper.py", data["files_changed"])
        reviewed = [
            payload["messages"][0]["content"]
            for path, payload in self.inner.httpd.posts
            if "chat" in path and isinstance(payload, dict) and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertGreater(len(reviewed), 1, reviewed)
        self.assertTrue(any("EVIL_TAIL = 1" in item for item in reviewed))
        self.assertGreaterEqual("".join(reviewed).count("x"), 9000)
        self.inner.assert_clean_origin()

    def test_many_short_lines_over_the_prompt_cap_are_not_committed(self):
        # 201 lines is under the line cap and still over 8000 characters.
        body = "".join(
            "V%03d = 'ordinary padding line for size %03d'\n" % (i, i) for i in range(200)
        ) + "EVIL_TAIL2 = 1\n"
        self.assertLess(body.count("\n"), 250)
        self.assertGreater(len(body), 8000)
        task = "fix add so one plus one is two\nfiles: src/calc.py, src/helper.py\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "write": {"src/helper.py": body}}],
            extra=["--retries", "2"],
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS", data)
        self.assertIsNotNone(data["commit"])
        self.assertIn("src/helper.py", data["files_changed"])
        reviewed = [
            payload["messages"][0]["content"]
            for path, payload in self.inner.httpd.posts
            if "chat" in path and isinstance(payload, dict) and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertGreater(len(reviewed), 1, len(reviewed))
        joined = "\n".join(reviewed)
        self.assertIn("EVIL_TAIL2 = 1", joined)
        self.assertIn("V199 = ", joined)
        self.inner.assert_clean_origin()

    def test_tracked_binary_edit_is_not_committed(self):
        blob = self.inner.repo / "src" / "blob.bin"
        blob.write_bytes(b"\x00\x01BASE\x00")
        self.inner.commit_base("add blob")
        task = "fix add so one plus one is two\nfiles: src/calc.py, src/blob.bin\n"
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "write": {"src/blob.bin": "\x00\x01EVIL_BIN2\x00"}}],
            extra=["--retries", "2"],
        )
        data = self._assert_refused_before_review(proc, receipt, "review-binary-change")
        self.assertIn("src/blob.bin", data["files_changed"])
        patch = (receipt / "attempt-1" / "patch.diff").read_text(encoding="utf-8")
        self.assertIn("Binary files ", patch)
        self.assertIn(" differ", patch)
        self.assertNotIn("EVIL_BIN2", patch)
        stored = subprocess.check_output(
            ["git", "-C", str(self.inner.repo), "show", "HEAD:src/blob.bin"]
        )
        self.assertEqual(stored, b"\x00\x01BASE\x00")

    def _assert_new_binary_refused(self, rel, raw):
        # Tester probe q3: a new untracked file the model writes. git diff
        # HEAD does not list it, so the runner pastes it into the prompt.
        task = "fix add so one plus one is two\nfiles: src/calc.py, %s\n" % rel
        proc, receipt = self._run(
            task,
            [{"mode": "fix", "write_hex": {rel: raw.hex()}}],
            extra=["--retries", "2"],
        )
        data = self._assert_refused_before_review(proc, receipt, "review-binary-change")
        self.assertIn(rel, data["files_changed"])
        patch = (receipt / "attempt-1" / "patch.diff").read_text(encoding="utf-8")
        self.assertIn("Binary files /dev/null and b/%s differ" % rel, patch)
        self.assertNotIn("\ufffd", patch)
        listed = subprocess.check_output(
            ["git", "-C", str(self.inner.repo), "ls-tree", "-r", "--name-only", "HEAD"], text=True
        )
        self.assertNotIn(rel, listed.splitlines())

    def test_new_untracked_non_utf8_file_is_not_committed(self):
        self._assert_new_binary_refused("src/evil.bin", b"EVIL_Q3 \xff\xfe\x80 tail\n")

    def test_new_untracked_file_with_a_nul_byte_is_not_committed(self):
        # Valid UTF-8, but a NUL makes git treat it as binary in the commit.
        self._assert_new_binary_refused("src/nul.dat", b"EVIL_NUL\x00tail\n")

    def test_reviewer_prompt_shows_a_tracked_non_ascii_path_unescaped(self):
        # A new file is pasted by the runner, so its path never goes through
        # git diff. A tracked edit does. core.quotepath would quote that path
        # as octal and the reviewer would not see src/café.py.
        name = "src/café.py"
        (self.inner.repo / name).write_text("N = 1\n", encoding="utf-8")
        self.inner.commit_base("add café")
        task = "fix add so one plus one is two\nfiles: src/calc.py, src/café.py\n"
        proc, receipt = self._run(task, [{"mode": "fix", "write": {name: "N = 2\n"}}])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        data = self._receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS")
        self.assertIn(name, data["files_changed"])
        reviewed = [
            payload["messages"][0]["content"]
            for path, payload in self.inner.httpd.posts
            if "chat" in path and isinstance(payload, dict) and "pfy-review-v1" in json.dumps(payload)
        ]
        self.assertEqual(len(reviewed), 1)
        prompt = reviewed[0]
        self.assertIn("diff --git a/src/café.py b/src/café.py", prompt)
        self.assertNotIn("\\303", prompt)
        self.assertNotIn('"a/src/caf', prompt)
        shown = subprocess.check_output(
            [
                "git",
                "-C",
                str(self.inner.repo),
                "-c",
                "core.quotepath=false",
                "grep",
                "-l",
                "-e",
                "N = 2",
                data["commit"],
                "--",
                name,
            ],
            text=True,
        )
        self.assertIn(name, shown)
        self.inner.assert_clean_origin()
