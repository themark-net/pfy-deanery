"""Product-sized wrap behavior: chunked review, generated paths, salvage, estimate.

T1–T8 from the wrapfix ticket. Fake grok and the local stub only. No model calls.
"""

from __future__ import annotations

import json
import os
import pty
import select
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

import tests.test_pfy_build_local as local_harness
from tests.test_pfy_build_cloud import CLOUD, SCRATCH, _git, _init_repo, _run, _write_exe
from tests.test_pfy_build_cloud_review_files import _diff_sections

MISSING_TOOL = "/no/such/pfy-impact-tool"
ONE_FILE_SENTENCE = "Do not reject because this file alone does not implement the whole task."
KEEP_TEST = (
    "import unittest\n\n"
    "class KeepTests(unittest.TestCase):\n"
    "    def test_keep(self):\n"
    "        self.assertEqual(1, 1)  # keep-assert\n"
)
REMOVED_ASSERT = "-        self.assertEqual(1, 1)  # keep-assert"


def _review_posts(httpd):
    found = []
    for path, payload in httpd.posts:
        if "chat" not in path or not isinstance(payload, dict):
            continue
        messages = payload.get("messages") or []
        content = ""
        if messages and isinstance(messages[0], dict):
            content = messages[0].get("content") or ""
        if "pfy-review-v1" in content:
            found.append(content)
    return found


def _prompt_parts(log: Path):
    if not log.is_file():
        return []
    return [item for item in log.read_text(encoding="utf-8").split("---PROMPT---") if item.strip()]


class LocalWrapfixTests(unittest.TestCase):
    def setUp(self):
        self.inner = local_harness.LocalBuildTests()
        self.inner.setUp()
        notes = self.inner.tmp / "stub-notes"
        notes.mkdir()
        self.plan = notes / "plan.json"
        self.count = notes / "attempt-count"
        self.prompts = notes / "prompts.jsonl"

    def tearDown(self):
        self.inner.tearDown()

    def _green_cmd(self):
        path = self.inner.repo / "tools" / "green_gate.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "print('GATE-OK')\nprint('Ran 1 test in 0.001s')\nprint('OK')\nraise SystemExit(0)\n",
            encoding="utf-8",
        )
        self.inner.commit_base("add green gate")
        return "python3 tools/green_gate.py"

    def _run_plan(self, task, steps, extra):
        self.plan.write_text(json.dumps(steps), encoding="utf-8")
        return self.inner.run_build(
            "plan",
            extra=extra,
            env_extra={
                "PFY_STUB_PLAN": str(self.plan),
                "PFY_STUB_COUNT": str(self.count),
                "PFY_STUB_PROMPTS": str(self.prompts),
                "PFY_LOCAL_BUILD_TEST_SEAM": "1",
            },
            timeout=120,
            task=task,
        )

    def test_t1_product_sized_diff_is_reviewed_in_chunks(self):
        """Five files, one over the local prompt cap, still review every line and pass.

        Fail: review-diff-too-large, one prompt, or a dropped tail.
        Recover: more than one review prompt, every source line is shown, PASS.
        """
        cmd = self._green_cmd()
        files = {}
        expected_lines = []
        for name, letter in (("a", "a"), ("b", "b"), ("c", "c"), ("d", "d")):
            token = "TOKEN_%s_LINE" % name.upper()
            body_line = letter * 6500
            files["src/%s.py" % name] = token + "\n" + body_line + "\n"
            expected_lines.append(token)
            expected_lines.append(body_line)
        wide_line = "W" * 12000
        files["src/wide.py"] = "TOKEN_WIDE_LINE\n" + wide_line + "\nEND_WIDE_LINE\n"
        task = (
            "add five source files\n"
            "files: src/a.py, src/b.py, src/c.py, src/d.py, src/wide.py\n"
        )
        proc, receipt = self._run_plan(
            task,
            [{"mode": "noop", "write": files}],
            ["--retries", "0", "--test-cmd", cmd],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS", text)
        self.assertNotEqual(data["reason"], "review-diff-too-large")
        self.assertIsNotNone(data["commit"])
        names = local_harness._git(
            self.inner.repo,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-r",
            data["commit"],
        ).strip().splitlines()
        self.assertEqual(
            sorted(names),
            ["src/a.py", "src/b.py", "src/c.py", "src/d.py", "src/wide.py"],
        )
        shown = local_harness._git(self.inner.repo, "show", data["commit"])
        self.assertGreater(len(shown), 30000, len(shown))
        reviews = _review_posts(self.inner.httpd)
        self.assertGreater(len(reviews), 1, len(reviews))
        joined = "\n".join(reviews)
        for line in expected_lines:
            self.assertIn(line, joined)
        self.assertIn("TOKEN_WIDE_LINE", joined)
        self.assertIn("END_WIDE_LINE", joined)
        self.assertGreaterEqual(joined.count("W"), 12000)
        self.assertNotIn("...[diff truncated]", joined)
        self.assertNotIn("review-diff-too-large", text)
        for prompt in reviews:
            self.assertIn("You are reviewing one file of a multi-file change", prompt)
            self.assertIn(ONE_FILE_SENTENCE, prompt)
            self.assertIn("Round manifest:", prompt)
        self.inner.assert_clean_origin()

    def test_t8_local_project_and_ignore_edits_that_do_not_touch_the_gate(self):
        """Adding [project] and a build/ ignore is committed. A pytest table or tests/ ignore is not.

        Fail: a metadata edit is tests-tampered, or a gate edit is published.
        Recover: the safe edit passes; the gate edit stops with tests-tampered and no commit.
        """
        cmd = self._green_cmd()
        ignore = (self.inner.repo / ".gitignore").read_text(encoding="utf-8")
        if not ignore.endswith("\n"):
            ignore += "\n"
        proc, receipt = self._run_plan(
            "record project metadata\nfiles: .gitignore, pyproject.toml\n",
            [{
                "mode": "noop",
                "write": {
                    ".gitignore": ignore + "build/\n",
                    "pyproject.toml": '[project]\nname = "demo"\ndependencies = ["rich"]\n',
                },
            }],
            ["--retries", "0", "--test-cmd", cmd],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(data["status"], "PASS", text)
        self.assertNotEqual(data["reason"], "tests-tampered")
        shown_ignore = local_harness._git(
            self.inner.repo, "show", "%s:.gitignore" % data["commit"]
        )
        shown_project = local_harness._git(
            self.inner.repo, "show", "%s:pyproject.toml" % data["commit"]
        )
        self.assertIn("build/", shown_ignore)
        self.assertIn("tmp/", shown_ignore)
        self.assertIn("[project]", shown_project)
        self.assertIn('name = "demo"', shown_project)
        self.inner.assert_clean_origin()

        self.inner.httpd.posts.clear()
        proc, receipt = self._run_plan(
            "weaken the gate\nfiles: .gitignore, pyproject.toml\n",
            [{
                "mode": "noop",
                "write": {
                    ".gitignore": ignore + "tests/\n",
                    "pyproject.toml": '[tool.pytest.ini_options]\naddopts = "-q"\n',
                },
            }],
            ["--retries", "0", "--test-cmd", cmd],
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, text)
        data = self.inner.receipt(proc, receipt)
        self.assertEqual(data["reason"], "tests-tampered", text)
        self.assertIsNone(data["commit"])
        self.inner.assert_clean_origin()


class CloudWrapfixTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.repo = _init_repo(SCRATCH / self.id().replace(".", "_"))
        self.side = SCRATCH / (self.id().replace(".", "_") + "-side")
        self.side.mkdir(parents=True, exist_ok=True)
        self.log = self.side / "prompts.txt"
        self.home = self.side / "home"
        self.grok_home = self.side / "grok-home"
        self.home.mkdir()
        self.grok_home.mkdir()

    def tearDown(self):
        from tests.test_pfy_build_cloud import _drop_external_worktrees

        _drop_external_worktrees(self.repo)
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.side, ignore_errors=True)

    def _env(self, extra=None):
        env = {
            "HOME": str(self.home),
            "GROK_HOME": str(self.grok_home),
            "PFY_CODEBASE_MEMORY": MISSING_TOOL,
            "PFY_TSA_BIN": MISSING_TOOL,
            "PFY_PROMPT_LOG": str(self.log),
            "CI": "",
            "PFY_BUILD_YES": "",
        }
        if extra:
            env.update(extra)
        return env

    def _gate(self):
        return _write_exe(
            self.side / "gate.py",
            "#!/usr/bin/env python3\nprint('GATE-OK')\nraise SystemExit(0)\n",
        )

    def _run(self, grok, task, extra=None, env=None, timeout=60):
        argv = [
            sys.executable,
            str(CLOUD),
            task,
            "--repo",
            str(self.repo),
            "--timeout",
            "30",
            "--test-cmd",
            "%s %s" % (sys.executable, self._gate()),
            "--grok-cmd",
            str(grok),
        ]
        if extra:
            argv.extend(extra)
        merged = self._env(env)
        return _run(argv, self.repo, env=merged, timeout=timeout)

    def _receipt(self):
        receipts = sorted((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))
        self.assertTrue(receipts, "no receipt")
        return json.loads(receipts[-1].read_text(encoding="utf-8"))

    def _reviews(self):
        return [item for item in _prompt_parts(self.log) if "PFY-CLOUD-REVIEW" in item]

    def _implements(self):
        return [
            item
            for item in _prompt_parts(self.log)
            if "PFY-CLOUD-IMPLEMENT" in item and "PFY-CLOUD-REVIEW" not in item
        ]

    def _commit_files(self, mapping, message):
        for rel, text in mapping.items():
            path = self.repo / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        added = _git(self.repo, "add", "--", *mapping.keys())
        self.assertEqual(added.returncode, 0, added.stderr)
        committed = _git(self.repo, "commit", "-m", message)
        self.assertEqual(committed.returncode, 0, committed.stderr)

    def test_t2_untracked_generated_files_are_excluded(self):
        """A huge untracked build tree and egg-info stay out of review and the commit.

        Fail: review-file-too-large, or the generated file is published.
        Recover: the real edit and a tracked build/ path are reviewed and committed,
        and the receipt lists the excluded paths.
        """
        self._commit_files({"build/keep_tracked.py": "tracked-seed\n"}, "tracked build file")
        writer = (
            "from pathlib import Path\n"
            "Path('note.py').write_text('NOTE_TOKEN\\n', encoding='utf-8')\n"
            "Path('build/keep_tracked.py').write_text('TRACKED_EDIT\\n', encoding='utf-8')\n"
            "big = Path('build/lib/pkg/big.py')\n"
            "big.parent.mkdir(parents=True, exist_ok=True)\n"
            "big.write_text('BIG_EXCLUDED_MARKER\\n' + ('Q' * 150001), encoding='utf-8')\n"
            "egg = Path('demo.egg-info/PKG-INFO')\n"
            "egg.parent.mkdir(parents=True, exist_ok=True)\n"
            "egg.write_text('EGG_EXCLUDED_MARKER\\n', encoding='utf-8')\n"
        )
        grok = _write_exe(self.side / "grok.py", _accept_grok(writer))
        proc = self._run(grok, "add a note", extra=["--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertNotEqual(payload["reason"], "review-file-too-large")
        self.assertNotIn("review-file-too-large", text)
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["branch"]).stdout
        self.assertIn("note.py", names)
        self.assertIn("build/keep_tracked.py", names)
        self.assertNotIn("big.py", names)
        self.assertNotIn("PKG-INFO", names)
        excluded = payload["excluded_generated"]
        self.assertGreaterEqual(excluded["count"], 2, excluded)
        self.assertIn("build/lib/pkg/big.py", excluded["paths"])
        self.assertIn("demo.egg-info/PKG-INFO", excluded["paths"])
        reviews = self._reviews()
        joined = "\n".join(_diff_sections(item) for item in reviews)
        self.assertIn("NOTE_TOKEN", joined)
        self.assertIn("TRACKED_EDIT", joined)
        self.assertNotIn("BIG_EXCLUDED_MARKER", joined)
        self.assertNotIn("EGG_EXCLUDED_MARKER", joined)

    def test_t3_tracked_file_over_the_cap_is_split(self):
        """One tracked source file over the cloud cap is reviewed in parts and published.

        Fail: review-file-too-large, or a part drops the tail.
        Recover: more than one review prompt, every W and the end marker are shown, PASS.
        """
        self._commit_files({"src/wide.py": "seed\n"}, "seed wide")
        grok = _write_exe(
            self.side / "grok.py",
            _accept_grok(
                "from pathlib import Path\n"
                "Path('src/wide.py').write_text('W' * 20000 + '\\nEND_WIDE_MARKER\\n', encoding='utf-8')\n"
            ),
        )
        proc = self._run(grok, "widen the tracked source", extra=["--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertNotEqual(payload["reason"], "review-file-too-large")
        reviews = self._reviews()
        self.assertGreater(len(reviews), 1, [len(item) for item in reviews])
        shown = "".join(_diff_sections(item) for item in reviews)
        self.assertGreaterEqual(shown.count("W"), 20000)
        self.assertIn("END_WIDE_MARKER", shown)
        self.assertNotIn("...[diff truncated]", shown)
        blob = _git(self.repo, "show", "%s:src/wide.py" % payload["commit"]).stdout
        self.assertGreaterEqual(blob.count("W"), 20000)
        self.assertIn("END_WIDE_MARKER", blob)

    def test_t4_partial_test_file_is_accepted_when_the_prompt_says_one_file(self):
        """A test-only file is rejected only when the one-file instruction is missing.

        Fail: the reviewer rejects the test because it is not the whole task.
        Recover: the prompt carries the instruction, both files are accepted, PASS.
        """
        writer = (
            "from pathlib import Path\n"
            "Path('src').mkdir(exist_ok=True)\n"
            "Path('tests').mkdir(exist_ok=True)\n"
            "Path('src/feature.py').write_text('def feature():\\n    return 1\\n', encoding='utf-8')\n"
            "Path('tests/test_only.py').write_text(\n"
            "    'import unittest\\n\\nclass OnlyTests(unittest.TestCase):\\n"
            "    def test_one(self):\\n        self.assertEqual(1, 1)\\n',\n"
            "    encoding='utf-8',\n"
            ")\n"
        )
        grok = _write_exe(
            self.side / "grok.py",
            _logged_grok(
                "if 'PFY-CLOUD-REVIEW' in blob:\n"
                "    test_prompt = 'tests/test_only.py' in blob and 'src/feature.py' not in blob.split('Diff:', 1)[-1]\n"
                "    if 'tests/test_only.py' in blob and %r not in blob:\n"
                "        print('verdict: reject')\n"
                "        print('reasons: file does not implement the whole task')\n"
                "    else:\n"
                "        print('verdict: accept')\n"
                "        print('reasons: ok')\n"
                "    raise SystemExit(0)\n"
                "%s" % (ONE_FILE_SENTENCE, writer)
            ),
        )
        proc = self._run(grok, "add a feature and its test", extra=["--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertEqual(payload["review"]["verdict"], "accept")
        reviews = self._reviews()
        test_prompts = [item for item in reviews if "tests/test_only.py" in item and "def test_one" in item]
        self.assertTrue(test_prompts, reviews)
        for prompt in test_prompts:
            self.assertIn(ONE_FILE_SENTENCE, prompt)
            self.assertIn("You are reviewing one file of a multi-file change", prompt)
            self.assertIn("src/feature.py", prompt)
        names = _git(self.repo, "ls-tree", "-r", "--name-only", payload["branch"]).stdout
        self.assertIn("src/feature.py", names)
        self.assertIn("tests/test_only.py", names)

    def test_t5_retry_reviews_only_the_rejected_file(self):
        """A removed assertion is fixed on the retry. The accepted file is not reviewed again.

        Fail: the retry rewrites every file, or re-reviews the accepted diff.
        Recover: the second prompt names only the test, review calls stay at the first round, PASS.
        """
        self._commit_files({"tests/test_keep.py": KEEP_TEST}, "keep assertion")
        grok = _write_exe(self.side / "grok.py", _assert_grok(never_fix=False))
        proc = self._run(grok, "add ok helper without dropping the test", extra=["--retries", "1"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertEqual(len(self._reviews()), 2, self._reviews())
        implements = self._implements()
        self.assertGreaterEqual(len(implements), 2, implements)
        reasons = implements[1].split("Reasons:\n", 1)[1].split("\n\nPrevious diff:\n", 1)[0]
        self.assertIn("Fix only these files", implements[1])
        self.assertIn("tests/test_keep.py", reasons)
        self.assertIn("removed an assertion", reasons)
        self.assertNotIn("src/ok.py", reasons)
        names = _git(
            self.repo, "diff-tree", "--no-commit-id", "--name-only", "-r", payload["commit"]
        ).stdout.splitlines()
        self.assertIn("src/ok.py", names)
        self.assertNotIn("tests/test_keep.py", names)
        kept = _git(self.repo, "show", "%s:tests/test_keep.py" % payload["commit"]).stdout
        self.assertIn("self.assertEqual(1, 1)  # keep-assert", kept)
        files = payload["review"]["files"]
        reused = [row for row in files if row.get("path") == "src/ok.py"]
        self.assertTrue(reused, files)
        self.assertTrue(reused[0]["reused"])
        self.assertEqual(reused[0]["verdict"], "accept")

    def test_t5_unfixed_assertion_keeps_the_worktree(self):
        """A reject that is never fixed fails and leaves the tree for a resume.

        Fail: the worktree is deleted, or recovery omits the rejected file.
        Recover: review-rejected, the tree is still on disk, recovery names the test.
        """
        self._commit_files({"tests/test_keep.py": KEEP_TEST}, "keep assertion")
        grok = _write_exe(self.side / "grok.py", _assert_grok(never_fix=True))
        proc = self._run(grok, "add ok helper without dropping the test", extra=["--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 1, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "FAIL", text)
        self.assertEqual(payload["reason"], "review-rejected")
        self.assertIsNone(payload["commit"])
        self.assertFalse(payload["worktree_removed"])
        self.assertIn("tests/test_keep.py", payload["recovery"])
        self.assertIn("removed an assertion", payload["recovery"])
        self.assertIn("Worktree kept", payload["recovery"])
        self.assertIn("--drop-worktree", payload["recovery"])
        marker = "Worktree kept at "
        start = payload["recovery"].find(marker)
        self.assertGreaterEqual(start, 0, payload["recovery"])
        raw = payload["recovery"][start + len(marker):].split(". Resume", 1)[0].strip()
        worktree = Path(raw)
        self.assertTrue((worktree / "src" / "ok.py").is_file(), worktree)
        body = (worktree / "tests" / "test_keep.py").read_text(encoding="utf-8")
        self.assertNotIn("self.assertEqual(1, 1)  # keep-assert", body)

    def test_t6_timeout_salvage_reads_usage_json(self):
        """A timed-out implement that left files is gated and reviewed. usage.json is the spend.

        Fail: TIMEOUT with the tree discarded, or the receipt misses the flushed cost.
        Recover: PASS, the attempt notes salvaged-after-timeout, usage.usd is the fake ticks.
        """
        grok = _write_exe(self.side / "grok.py", _salvage_grok(kind="usage"))
        proc = self._run(
            grok,
            "write a note before the timeout",
            extra=["--retries", "1", "--timeout", "2"],
            timeout=40,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertTrue(
            any(row.get("note") == "salvaged-after-timeout" for row in payload["attempts"]),
            payload["attempts"],
        )
        self.assertEqual(payload["usage"]["usd"], 1.25)
        self.assertEqual(len(payload["usage"]["sessions"]), 1)
        self.assertFalse(payload["usage"]["sessions"][0]["estimated"])
        self.assertEqual(payload["usage"]["sessions"][0]["source"], "usage.json")
        self.assertIn("spend $1.25 (1 sessions, 0 estimated)", proc.stdout or "")

    def test_t6_timeout_without_usage_json_is_estimated(self):
        """SIGINT is ignored and only updates.jsonl exists, so the spend is estimated.

        Fail: the run drops the tree, or it treats a missing usage.json as zero.
        Recover: the salvaged tree still passes and the receipt marks estimated.
        """
        grok = _write_exe(self.side / "grok.py", _salvage_grok(kind="updates"))
        proc = self._run(
            grok,
            "write a note before the timeout",
            extra=["--retries", "1", "--timeout", "4"],
            env={"PFY_BUILD_SIGINT_GRACE": "0.2"},
            timeout=40,
        )
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertAlmostEqual(payload["usage"]["usd"], 0.0026, places=6)
        session = payload["usage"]["sessions"][0]
        self.assertTrue(session["estimated"])
        self.assertEqual(session["source"], "updates.jsonl")
        self.assertIn("spend $0.00 (1 sessions, 1 estimated)", proc.stdout or "")

    def test_t7_estimate_precedes_grok_and_a_no_spends_nothing(self):
        """The estimate is on stderr before grok starts. Declining skips the call.

        Fail: grok starts before the line, or answering n still spends.
        Recover: the line is already buffered when the order file appears; n exits 2 with no grok.
        """
        order = self.side / "grok-order"
        grok = _write_exe(
            self.side / "grok.py",
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            "from pathlib import Path\n"
            "Path(os.environ['PFY_ORDER_FILE']).write_text('started\\n', encoding='utf-8')\n"
            "blob = '\\n'.join(sys.argv)\n"
            "if 'PFY-CLOUD-REVIEW' in blob:\n"
            "    print('verdict: accept')\n"
            "    print('reasons: ok')\n"
            "    raise SystemExit(0)\n"
            "Path('note.py').write_text('noted\\n', encoding='utf-8')\n"
            "raise SystemExit(0)\n",
        )
        argv = [
            sys.executable,
            str(CLOUD),
            "add a note",
            "--repo",
            str(self.repo),
            "--retries",
            "0",
            "--timeout",
            "30",
            "--test-cmd",
            "%s %s" % (sys.executable, self._gate()),
            "--grok-cmd",
            str(grok),
        ]
        env = os.environ.copy()
        env.update(self._env({"PFY_ORDER_FILE": str(order)}))
        env["TMPDIR"] = str(SCRATCH)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        proc = subprocess.Popen(
            argv,
            cwd=self.repo,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        fd = proc.stderr.fileno()
        os.set_blocking(fd, False)
        buf = bytearray()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not order.is_file():
            ready, _, _ = select.select([fd], [], [], 0.2)
            if ready:
                _drain(fd, buf)
        self.assertTrue(order.is_file(), "grok did not start")
        ready, _, _ = select.select([fd], [], [], 1.0)
        if ready:
            _drain(fd, buf)
        self.assertIn(b"cost estimate:", bytes(buf))
        out, err = proc.communicate(timeout=40)
        self.assertEqual(proc.returncode, 0, (out or b"") + (err or b""))
        payload = self._receipt()
        self.assertIn("estimate", payload)
        self.assertIn("usd", payload["estimate"])
        self.assertIn("low", payload["estimate"])
        self.assertIn("high", payload["estimate"])
        self.assertTrue(payload["estimate"]["basis"])

        order.unlink()
        self.log.write_text("", encoding="utf-8")
        dry = self.side / "dry-receipt"
        dry_proc = _run(
            argv[:3] + ["--dry-run", "--receipt-dir", str(dry), "--grok-cmd", str(grok)],
            self.repo,
            env=self._env(),
        )
        dry_text = (dry_proc.stderr or "")
        self.assertEqual(dry_proc.returncode, 0, dry_proc.stdout + dry_text)
        self.assertIn("cost estimate:", dry_text)
        self.assertFalse(order.exists())
        dry_payload = json.loads((dry / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(dry_payload["status"], "DRY-RUN")
        self.assertIn("estimate", dry_payload)

        master, slave = pty.openpty()
        declined = subprocess.Popen(
            argv,
            cwd=self.repo,
            env=env,
            stdin=slave,
            stdout=slave,
            stderr=slave,
        )
        os.close(slave)
        captured = bytearray()

        def _read_pty():
            while True:
                try:
                    chunk = os.read(master, 4096)
                except OSError:
                    return
                if not chunk:
                    return
                captured.extend(chunk)

        import threading

        reader = threading.Thread(target=_read_pty, daemon=True)
        reader.start()
        os.write(master, b"n\n")
        try:
            code = declined.wait(timeout=30)
        finally:
            os.close(master)
            reader.join(timeout=2)
        self.assertEqual(code, 2)
        self.assertFalse(order.exists(), captured.decode("utf-8", "replace"))
        shown = captured.decode("utf-8", "replace")
        self.assertIn("cost estimate:", shown)
        self.assertIn("Proceed? [y/N]", shown)
        receipts = sorted((self.repo / "pipelines" / "dogfood" / "build-cloud").glob("*/receipt.json"))
        declined_payload = json.loads(receipts[-1].read_text(encoding="utf-8"))
        self.assertEqual(declined_payload["reason"], "estimate-declined")
        self.assertNotEqual(declined_payload["status"], "PASS")
        self.assertEqual(declined_payload["exit_code"], 2)

    def test_t8_cloud_project_and_ignore_edits_that_do_not_touch_the_gate(self):
        """Adding [project] and build/ is committed. A pytest table or tests/ ignore is tests-tampered.

        Fail: metadata is refused, or a gate edit is published.
        Recover: the safe edit passes; the gate edit does not commit.
        """
        ignore = (self.repo / ".gitignore").read_text(encoding="utf-8")
        if not ignore.endswith("\n"):
            ignore += "\n"
        safe = (
            "from pathlib import Path\n"
            "text = Path('.gitignore').read_text(encoding='utf-8')\n"
            "if not text.endswith('\\n'):\n"
            "    text += '\\n'\n"
            "Path('.gitignore').write_text(text + 'build/\\n', encoding='utf-8')\n"
            "Path('pyproject.toml').write_text(\n"
            "    '[project]\\nname = \"demo\"\\ndependencies = [\"rich\"]\\n',\n"
            "    encoding='utf-8',\n"
            ")\n"
        )
        grok = _write_exe(self.side / "grok.py", _accept_grok(safe))
        proc = self._run(grok, "record project metadata", extra=["--retries", "0"])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        payload = self._receipt()
        self.assertEqual(payload["status"], "PASS", text)
        self.assertNotEqual(payload["reason"], "tests-tampered")
        shown_ignore = _git(self.repo, "show", "%s:.gitignore" % payload["commit"]).stdout
        shown_project = _git(self.repo, "show", "%s:pyproject.toml" % payload["commit"]).stdout
        self.assertIn("build/", shown_ignore)
        self.assertIn("tmp/", shown_ignore)
        self.assertIn("[project]", shown_project)

        self.log.write_text("", encoding="utf-8")
        bad = (
            "from pathlib import Path\n"
            "text = Path('.gitignore').read_text(encoding='utf-8')\n"
            "if not text.endswith('\\n'):\n"
            "    text += '\\n'\n"
            "Path('.gitignore').write_text(text + 'tests/\\n', encoding='utf-8')\n"
            "Path('pyproject.toml').write_text(\n"
            "    '[tool.pytest.ini_options]\\naddopts = \"-q\"\\n',\n"
            "    encoding='utf-8',\n"
            ")\n"
        )
        grok = _write_exe(self.side / "grok-bad.py", _accept_grok(bad))
        proc = self._run(grok, "weaken the gate", extra=["--retries", "0", "--receipt-dir", str(self.side / "bad-receipt")])
        text = (proc.stdout or "") + (proc.stderr or "")
        self.assertNotEqual(proc.returncode, 0, text)
        payload = json.loads((self.side / "bad-receipt" / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["reason"], "tests-tampered", text)
        self.assertIsNone(payload["commit"])
        branches = _git(self.repo, "branch", "--list").stdout
        self.assertNotIn("weaken", branches)


def _drain(fd, buf):
    while True:
        try:
            chunk = os.read(fd, 1 << 16)
        except BlockingIOError:
            return
        if not chunk:
            return
        buf.extend(chunk)


def _logged_grok(body):
    return (
        "#!/usr/bin/env python3\n"
        "import os, sys\n"
        "from pathlib import Path\n"
        "blob = '\\n'.join(sys.argv)\n"
        "Path(os.environ['PFY_PROMPT_LOG']).open('a', encoding='utf-8').write(blob + '\\n---PROMPT---\\n')\n"
        "%s\n" % body
    )


def _accept_grok(writer):
    return _logged_grok(
        "if 'PFY-CLOUD-REVIEW' in blob:\n"
        "    print('verdict: accept')\n"
        "    print('reasons: ok')\n"
        "    raise SystemExit(0)\n"
        "%s\n"
        "raise SystemExit(0)\n" % writer
    )


def _assert_grok(never_fix):
    flag = "1" if never_fix else "0"
    return _logged_grok(
        "import os\n"
        "from pathlib import Path\n"
        "ORIGINAL = %r\n"
        "if 'PFY-CLOUD-REVIEW' in blob:\n"
        "    if %r in blob:\n"
        "        print('verdict: reject')\n"
        "        print('reasons: removed an assertion')\n"
        "    else:\n"
        "        print('verdict: accept')\n"
        "        print('reasons: ok')\n"
        "    raise SystemExit(0)\n"
        "if %r == '0' and 'Fix only these files' in blob:\n"
        "    Path('tests/test_keep.py').write_text(ORIGINAL, encoding='utf-8')\n"
        "    raise SystemExit(0)\n"
        "Path('src').mkdir(exist_ok=True)\n"
        "Path('src/ok.py').write_text('def ok():\\n    return 1\\n', encoding='utf-8')\n"
        "path = Path('tests/test_keep.py')\n"
        "path.write_text(path.read_text(encoding='utf-8').replace(\n"
        "    '        self.assertEqual(1, 1)  # keep-assert\\n', ''\n"
        "), encoding='utf-8')\n"
        "raise SystemExit(0)\n" % (KEEP_TEST, REMOVED_ASSERT, flag)
    )


def _salvage_grok(kind):
    usage_body = (
        "def _flush():\n"
        "    import json, urllib.parse\n"
        "    root = Path(os.environ['GROK_HOME']) / 'sessions' / urllib.parse.quote(str(Path.cwd().resolve()), safe='') / 'sess-usage'\n"
        "    root.mkdir(parents=True, exist_ok=True)\n"
        "    (root / 'usage.json').write_text(json.dumps({\n"
        "        'session': {\n"
        "            'costUsdTicks': 12500000000,\n"
        "            'inputTokens': 10,\n"
        "            'outputTokens': 2,\n"
        "            'modelCalls': 1,\n"
        "            'primaryModelId': 'grok-4.7',\n"
        "        }\n"
        "    }), encoding='utf-8')\n"
        "    os._exit(0)\n"
        "signal.signal(signal.SIGINT, lambda *_a: _flush())\n"
    )
    updates_body = (
        "signal.signal(signal.SIGINT, signal.SIG_IGN)\n"
        "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
        "import json, urllib.parse\n"
        "root = Path(os.environ['GROK_HOME']) / 'sessions' / urllib.parse.quote(str(Path.cwd().resolve()), safe='') / 'sess-updates'\n"
        "root.mkdir(parents=True, exist_ok=True)\n"
        "(root / 'updates.jsonl').write_text(json.dumps({\n"
        "    'usage': {\n"
        "        'input_tokens': 1000,\n"
        "        'output_tokens': 100,\n"
        "        'cached_input_tokens': 0,\n"
        "        'model': 'grok-4.7',\n"
        "    }\n"
        "}) + '\\n', encoding='utf-8')\n"
    )
    tail = usage_body if kind == "usage" else updates_body
    return (
        "#!/usr/bin/env python3\n"
        "import os, signal, sys, time\n"
        "from pathlib import Path\n"
        "blob = '\\n'.join(sys.argv)\n"
        "if 'PFY-CLOUD-REVIEW' in blob:\n"
        "    print('verdict: accept')\n"
        "    print('reasons: ok')\n"
        "    raise SystemExit(0)\n"
        "Path('note.py').write_text('salvaged\\n', encoding='utf-8')\n"
        "%s\n"
        "time.sleep(30)\n"
        "raise SystemExit(0)\n" % tail
    )
