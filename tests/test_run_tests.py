#!/usr/bin/env python3
"""run_tests.py exit status follows the module, not the runner.

How this fails: a failing module is reported as rc 0, so CI goes green.
Recovery: the receipt rc and the process exit stay nonzero, and the output
tail names the failure. A passing module stays rc 0.
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
RUN = ROOT / "scripts" / "run_tests.py"


class RunTestsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pfy-run-"))
        tests = self.tmp / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_ok.py").write_text(
            "import unittest\n"
            "class Ok(unittest.TestCase):\n"
            "    def test_ok(self):\n"
            "        self.assertEqual(1, 1)\n",
            encoding="utf-8",
        )
        (tests / "test_bad.py").write_text(
            "import unittest\n"
            "class Bad(unittest.TestCase):\n"
            "    def test_bad(self):\n"
            "        self.fail('boom')\n",
            encoding="utf-8",
        )
        self.env = os.environ.copy()
        self.env["TMPDIR"] = str(self.tmp)
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *modules: str) -> subprocess.CompletedProcess[str]:
        receipt = self.tmp / "receipt.json"
        proc = subprocess.run(
            [sys.executable, str(RUN), "--root", str(self.tmp), "--receipt", str(receipt), "-j", "2", *modules],
            cwd=self.tmp,
            env=self.env,
            capture_output=True,
            text=True,
        )
        proc.receipt_path = receipt  # type: ignore[attr-defined]
        return proc

    def test_passing_module_is_rc_zero(self) -> None:
        proc = self._run("tests.test_ok")
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn("PASS tests.test_ok", proc.stdout)
        data = json.loads((self.tmp / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(data["rc"], 0)
        self.assertEqual(data["modules"], ["tests.test_ok"])

    def test_failing_module_is_rc_nonzero_and_tail_is_printed(self) -> None:
        proc = self._run("tests.test_bad")
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertIn("FAIL tests.test_bad", proc.stdout)
        self.assertIn("boom", blob)
        data = json.loads((self.tmp / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(data["rc"], 1)
        self.assertEqual(data["results"][0]["status"], "FAIL")

    def _argv(self, *extra: str) -> list[str]:
        return [sys.executable, str(RUN), "--root", str(self.tmp), "-j", "2", *extra]

    def test_full_suite_skips_fixture_test_files(self) -> None:
        """Fail: a fixture's test_*.py under tests/fixtures/ is collected as a
        suite module and errors on import (the nightly full suite went red on
        tests.fixtures.mvp_receipt.fixture.test_add). Recovery: the default
        list leaves out any path under a fixtures directory and keeps the
        real modules.
        """
        fixture = self.tmp / "tests" / "fixtures" / "demo" / "fixture"
        fixture.mkdir(parents=True)
        (fixture / "test_add.py").write_text("from add import add\n", encoding="utf-8")
        nested = self.tmp / "tests" / "sub"
        nested.mkdir()
        (nested / "__init__.py").write_text("", encoding="utf-8")
        (nested / "test_nested.py").write_text("", encoding="utf-8")
        proc = subprocess.run(
            self._argv("--list"), cwd=self.tmp, env=self.env, capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        listed = [line for line in proc.stdout.splitlines() if line]
        self.assertEqual(listed, ["tests.sub.test_nested", "tests.test_bad", "tests.test_ok"])

    def test_shards_cover_the_list_once_and_a_bad_shard_stays_red(self) -> None:
        """Fail: one shard runs every module, or a shard that contains the
        failing module exits 0. Recovery: each name lands in one slot, the
        shard with only the passing module exits 0, and a bad i/n exits 2.
        An empty slot of a non-empty list is a successful no-op.
        """
        names = ["tests.test_ok", "tests.test_bad"]
        count = 0
        slots: dict[str, int] = {}
        for n in range(3, 17):
            slots = {name: _slot(name, n) for name in names}
            if len(set(slots.values())) == 2:
                count = n
                break
        self.assertGreaterEqual(count, 3, slots)
        listed: set[str] = set()
        for index in range(count):
            proc = subprocess.run(
                self._argv("--list", "--shard", f"{index}/{count}", *names),
                cwd=self.tmp,
                env=self.env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            found = [line for line in proc.stdout.splitlines() if line]
            listed.update(found)
            self.assertEqual(found, [name for name in names if slots[name] == index])
        self.assertEqual(listed, set(names))

        ok_index = slots["tests.test_ok"]
        bad_index = slots["tests.test_bad"]
        receipt = self.tmp / "receipt.json"
        ok = subprocess.run(
            self._argv("--receipt", str(receipt), "--shard", f"{ok_index}/{count}", *names),
            cwd=self.tmp,
            env=self.env,
            capture_output=True,
            text=True,
        )
        blob = ok.stdout + ok.stderr
        self.assertEqual(ok.returncode, 0, blob)
        self.assertIn("PASS tests.test_ok", ok.stdout)
        self.assertNotIn("tests.test_bad", ok.stdout)
        data = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(data["rc"], 0)
        self.assertEqual(data["modules"], ["tests.test_ok"])
        self.assertEqual(data["shard"], f"{ok_index}/{count}")

        bad = subprocess.run(
            self._argv("--receipt", str(receipt), "--shard", f"{bad_index}/{count}", *names),
            cwd=self.tmp,
            env=self.env,
            capture_output=True,
            text=True,
        )
        blob = bad.stdout + bad.stderr
        self.assertNotEqual(bad.returncode, 0, blob)
        self.assertIn("FAIL tests.test_bad", bad.stdout)
        self.assertNotIn("PASS tests.test_ok", bad.stdout)
        data = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(data["modules"], ["tests.test_bad"])
        self.assertEqual(data["shard"], f"{bad_index}/{count}")

        empty_index = next(i for i in range(count) if i not in slots.values())
        empty = subprocess.run(
            self._argv("--receipt", str(receipt), "--shard", f"{empty_index}/{count}", *names),
            cwd=self.tmp,
            env=self.env,
            capture_output=True,
            text=True,
        )
        blob = empty.stdout + empty.stderr
        self.assertEqual(empty.returncode, 0, blob)
        self.assertIn("modules=0", empty.stdout)
        data = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(data["rc"], 0)
        self.assertEqual(data["modules"], [])
        self.assertEqual(data["shard"], f"{empty_index}/{count}")

        for bad_shard in ("2/2", "no", "0/0"):
            proc = subprocess.run(
                self._argv("--shard", bad_shard, *names),
                cwd=self.tmp,
                env=self.env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(proc.returncode, 2, proc.stderr)
            self.assertIn("shard must be i/n", proc.stderr)


def _slot(name: str, count: int) -> int:
    import hashlib

    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % count


if __name__ == "__main__":
    unittest.main()
