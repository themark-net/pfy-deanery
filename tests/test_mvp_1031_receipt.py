"""Behavior checks for the mvp-1031 red fixture and, later, the receipt checker.

No grok, no model, no network. Scratch stays under this worktree tmp/.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "eval" / "mvp-1031" / "fixture"
SCRATCH = ROOT / "tmp" / "mvp-eval-1031"
SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ["TMPDIR"] = str(SCRATCH)
tempfile.tempdir = str(SCRATCH)


class FixtureRedUntilSumTests(unittest.TestCase):
    def test_shipped_add_fails_and_sum_passes(self):
        # Fail: a fixture that already returns the sum would ship green and the demo would have nothing to fix.
        # Recover: keep add wrong in the tree; the same test file passes once add returns a + b.
        red = subprocess.run(
            [sys.executable, "-m", "unittest", "test_add"],
            cwd=FIXTURE,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(red.returncode, 0, red.stdout + red.stderr)
        self.assertIn("AssertionError", red.stderr)

        work = Path(tempfile.mkdtemp(prefix="fix-add-", dir=SCRATCH))
        try:
            shutil.copy(FIXTURE / "test_add.py", work / "test_add.py")
            (work / "add.py").write_text(
                "def add(a, b):\n    return a + b\n",
                encoding="utf-8",
            )
            green = subprocess.run(
                [sys.executable, "-m", "unittest", "test_add"],
                cwd=work,
                capture_output=True,
                text=True,
            )
            self.assertEqual(green.returncode, 0, green.stdout + green.stderr)
        finally:
            shutil.rmtree(work)


class InitFixtureTests(unittest.TestCase):
    def setUp(self):
        self.caller = Path(tempfile.mkdtemp(prefix="caller-", dir=SCRATCH))
        (self.caller / "tmp").mkdir()
        self.init = ROOT / "eval" / "mvp-1031" / "init_fixture.sh"

    def tearDown(self):
        shutil.rmtree(self.caller)

    def _run(self, args):
        return subprocess.run(
            ["bash", str(self.init), *args],
            cwd=self.caller,
            capture_output=True,
            text=True,
        )

    def test_init_makes_main_repo_whose_test_fails(self):
        # Fail: a green seed commit would hide a broken init that already "fixed" add.
        # Recover: the committed test_add stays red on branch main until a later edit.
        dest = self.caller / "tmp" / "repo"
        proc = self._run([str(dest)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), str(dest.resolve()))
        branch = subprocess.run(
            ["git", "-C", str(dest), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(branch.stdout.strip(), "main")
        count = subprocess.run(
            ["git", "-C", str(dest), "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(count.stdout.strip(), "1")
        red = subprocess.run(
            [sys.executable, "-m", "unittest", "test_add"],
            cwd=dest,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(red.returncode, 0, red.stdout + red.stderr)

    def test_usage_exits_2_and_writes_nothing(self):
        # Fail: missing args that still create a default repo would write outside the request.
        # Recover: exit 2 and leave the caller tmp empty.
        missing = self._run([])
        extra = self._run(["tmp/one", "tmp/two"])
        self.assertEqual(missing.returncode, 2, missing.stderr)
        self.assertEqual(extra.returncode, 2, extra.stderr)
        self.assertEqual(list((self.caller / "tmp").iterdir()), [])

    def test_refuses_dest_outside_caller_tmp(self):
        # Fail: init that accepts any path can seed a repo in the caller checkout.
        # Recover: non-zero exit and the outside path is not created.
        outside = self.caller / "not-in-tmp"
        proc = self._run([str(outside)])
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertNotEqual(proc.returncode, 2)
        self.assertFalse(outside.exists())
        self.assertIn("outside", proc.stderr)

    def test_existing_empty_dest_is_initialized(self):
        # Fail: treating an empty dest as occupied would force the caller to delete a dir they just made.
        # Recover: init in place and leave branch main with a red test.
        dest = self.caller / "tmp" / "empty"
        dest.mkdir()
        proc = self._run([str(dest)])
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((dest / "add.py").is_file())
        self.assertTrue((dest / ".git").is_dir())

    def test_refuses_to_delete_preexisting_nonempty_dest(self):
        # Fail: rm of a non-empty dest would destroy a repo the caller already had.
        # Recover: leave the sentinel in place and do not create a git dir.
        dest = self.caller / "tmp" / "repo"
        dest.mkdir()
        sentinel = dest / "keep.txt"
        sentinel.write_text("keep\n", encoding="utf-8")
        proc = self._run([str(dest)])
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep\n")
        self.assertFalse((dest / ".git").exists())
        self.assertFalse((dest / "add.py").exists())

    def test_refuses_symlink_dest_that_leaves_tmp(self):
        # Fail: a symlink inside tmp that points outside would let init write off-tree.
        # Recover: refuse the symlink and leave the outside tree unchanged.
        outside = self.caller / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep\n", encoding="utf-8")
        link = self.caller / "tmp" / "link"
        link.symlink_to(outside)
        proc = self._run([str(link)])
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual((outside / "keep.txt").read_text(encoding="utf-8"), "keep\n")
        self.assertFalse((outside / "add.py").exists())
        self.assertFalse((outside / ".git").exists())


def _pass_receipt() -> dict:
    return {
        "schema": "pfy-cloud-build/1",
        "status": "PASS",
        "reason": "ok",
        "exit_code": 0,
        "branch": "cloud/add-sum-20261031",
        "commit": "a" * 40,
        "review": {"verdict": "accept"},
        "attempts": [{"status": "PASS"}],
        "pushed": False,
        "gate": {"cmd": "python3 -m unittest test_add"},
    }


class CheckReceiptTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix="receipt-", dir=SCRATCH))
        self.checker = ROOT / "eval" / "mvp-1031" / "check_receipt.py"

    def tearDown(self):
        shutil.rmtree(self.work)

    def _write(self, body: dict) -> Path:
        path = self.work / "receipt.json"
        path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def _check(self, path: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.checker), str(path)],
            capture_output=True,
            text=True,
        )

    def test_pass_receipt_exits_0(self):
        # Fail: a checker that rejects a complete PASS would block the integration demo.
        # Recover: exit 0 and write nothing when every required field matches.
        proc = self._check(self._write(_pass_receipt()))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(proc.stderr, "")

    def test_rejects_listed_field_failures(self):
        # Fail: a checker that accepts these shapes would call a bad cloud run a PASS.
        # Recover: exit 1 and name the broken field on one stderr line.
        cases = {
            "commit": {**_pass_receipt(), "commit": None},
            "branch": {**_pass_receipt(), "branch": "local/x"},
            "verdict": {**_pass_receipt(), "review": {"verdict": "reject"}},
            "pushed": {**_pass_receipt(), "pushed": True},
            "attempts": {**_pass_receipt(), "attempts": []},
            "schema": {**_pass_receipt(), "schema": "pfy-local-build/1"},
        }
        expect = {
            "commit": "commit is not 40 hex chars",
            "branch": "branch does not start with cloud/",
            "verdict": "review.verdict is not accept",
            "pushed": "pushed is not false",
            "attempts": "attempts is empty",
            "schema": "schema is not pfy-cloud-build/1",
        }
        for name, body in cases.items():
            proc = self._check(self._write(body))
            self.assertEqual(proc.returncode, 1, name + " " + proc.stderr)
            self.assertEqual(proc.stderr.strip(), "rejected: " + expect[name])
            self.assertEqual(proc.stderr.count("\n"), 1)
            self.assertEqual(proc.stdout, "")

    def test_rejects_secret_markers_in_pass_shaped_json(self):
        # Fail: a PASS-shaped receipt that still carries a token would be archived as success.
        # Recover: exit 1, name the marker class, and do not echo the sample.
        samples = {
            "AKIA": "AKIA" + ("a" * 16),
            "BEGIN PRIVATE KEY": "-----BEGIN PRIVATE KEY-----\nnot-a-real-key\n",
            "sk_": "sk_" + ("b" * 8),
        }
        expect = {
            "AKIA": "rejected: receipt text contains AKIA",
            "BEGIN PRIVATE KEY": "rejected: receipt text contains BEGIN PRIVATE KEY",
            "sk_": "rejected: receipt text contains sk_ secret",
        }
        for name, sample in samples.items():
            body = _pass_receipt()
            body["note"] = sample
            proc = self._check(self._write(body))
            self.assertEqual(proc.returncode, 1, name)
            self.assertEqual(proc.stderr.strip(), expect[name])
            self.assertNotIn(sample, proc.stderr)
            self.assertNotIn(sample, proc.stdout)

    def test_checker_does_not_read_grok_auth(self):
        # Fail: opening ~/.grok/auth.json would copy a credential path into a receipt check.
        # Recover: the checker stays on the receipt file; strace shows no auth.json open.
        path = self._write(_pass_receipt())
        trace = self.work / "strace.txt"
        proc = subprocess.run(
            [
                "strace",
                "-f",
                "-e",
                "trace=file",
                "-o",
                str(trace),
                sys.executable,
                str(self.checker),
                str(path),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = trace.read_text(encoding="utf-8", errors="replace")
        self.assertNotIn("auth.json", text)
        self.assertNotIn(".grok/", text)


class ReadmeDemoTests(unittest.TestCase):
    def test_readme_states_demo_command_without_plan_link(self):
        # Fail: a markdown link to the plan file 404s on this branch, and a drifted command breaks the demo.
        # Recover: keep the three inline commands and do not link the plan.
        text = (ROOT / "eval" / "mvp-1031" / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            'bash eval/mvp-1031/init_fixture.sh "$PWD/tmp/mvp-fixture-repo"',
            text,
        )
        self.assertIn(
            'python3 -m unittest test_add',
            text,
        )
        self.assertIn(
            'python3 eval/mvp-1031/check_receipt.py "$PWD/tmp/mvp-fixture-receipt/receipt.json"',
            text,
        )
        self.assertNotRegex(text, r"\[[^\]]*\]\([^)]*MVP-PARALLEL-1031\.md\)")


if __name__ == "__main__":
    unittest.main()
