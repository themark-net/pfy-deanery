#!/usr/bin/env python3
"""Pass cache: round trip, tree miss, FAIL dropped, corrupt file is a miss.

How this fails: a failed run is reused, a new tree hits an old PASS, or a
truncated file is treated as a hit. Recovery: check exits 1 and the suite runs.
A full PASS may satisfy a weaker check. An affected PASS must not satisfy full.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "scripts" / "test_cache.py"


def _git(cwd: Path, *args: str) -> None:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "cache-test"
    env["GIT_AUTHOR_EMAIL"] = "cache-test@example.com"
    env["GIT_COMMITTER_NAME"] = "cache-test"
    env["GIT_COMMITTER_EMAIL"] = "cache-test@example.com"
    proc = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {args[0]} failed: {proc.stderr or proc.stdout}")


class TestCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pfy-cache-"))
        self.cache = self.tmp / "cache"
        self.cache.mkdir()
        repo = self.tmp / "repo"
        repo.mkdir()
        self.repo = repo
        _git(repo, "init", "-b", "main")
        _git(repo, "config", "user.email", "cache-test@example.com")
        _git(repo, "config", "user.name", "cache-test")
        # The key hashes the real config file. Point the script at this repo
        # by copying the config so the tree under test is self-contained? The
        # script finds config by walking parents of the script, which is the
        # real repo. --root is the git tree. That matches CI: config lives in
        # the repo being tested. Copy it in so this temp repo is the --root
        # and still has the file the script requires when --root is used.
        cfg = repo / "config"
        cfg.mkdir()
        shutil.copy(ROOT / "config" / "test_select.json", cfg / "test_select.json")
        (repo / "README.md").write_text("one\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "one")
        self.env = os.environ.copy()
        self.env["PFY_TEST_CACHE"] = str(self.cache)
        self.env["PFY_HOST_CLASS"] = "nimo"

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [os.sys.executable, str(CACHE), "--root", str(self.repo), *args],
            cwd=self.repo,
            env=self.env,
            capture_output=True,
            text=True,
        )

    def _receipt(self, rc: int = 0) -> str:
        path = self.tmp / f"receipt-{rc}.json"
        path.write_text(json.dumps({"rc": rc, "modules": ["tests.test_leaf"]}), encoding="utf-8")
        return str(path)

    def test_record_check_round_trip_and_full_satisfies_weaker(self) -> None:
        receipt = self._receipt(0)
        bare = self._run("record", "--mode", "affected", "--modules", "tests.test_leaf")
        self.assertNotEqual(bare.returncode, 0, bare.stdout + bare.stderr)
        self.assertIn("receipt", bare.stdout + bare.stderr)
        self.assertEqual(list(self.cache.glob("*.json")), [])
        rec = self._run(
            "record", "--mode", "affected", "--modules", "tests.test_leaf", "--receipt", receipt
        )
        self.assertEqual(rec.returncode, 0, rec.stdout + rec.stderr)
        self.assertIn("recorded ", rec.stdout)
        hit = self._run("check", "--need", "affected")
        self.assertEqual(hit.returncode, 0, hit.stdout + hit.stderr)
        self.assertIn("HIT ", hit.stdout)
        # An affected PASS must not unlock a full check.
        full = self._run("check", "--need", "full")
        self.assertEqual(full.returncode, 1, full.stdout)
        self.assertIn("MISS ", full.stdout)
        again = self._run(
            "record", "--mode", "full", "--modules", "tests.test_leaf", "--receipt", receipt
        )
        self.assertEqual(again.returncode, 0, again.stderr)
        weaker = self._run("check", "--need", "structural")
        self.assertEqual(weaker.returncode, 0, weaker.stdout + weaker.stderr)
        self.assertIn("HIT ", weaker.stdout)

    def test_different_tree_misses(self) -> None:
        first = self._run("record", "--mode", "full", "--receipt", self._receipt(0))
        self.assertEqual(first.returncode, 0, first.stderr)
        key1 = self._run("key")
        self.assertEqual(key1.returncode, 0, key1.stderr)
        (self.repo / "README.md").write_text("two\n", encoding="utf-8")
        _git(self.repo, "add", "-A")
        _git(self.repo, "commit", "-m", "two")
        key2 = self._run("key")
        self.assertNotEqual(key1.stdout.strip(), key2.stdout.strip())
        miss = self._run("check", "--need", "full")
        self.assertEqual(miss.returncode, 1, miss.stdout)
        self.assertIn("MISS ", miss.stdout)
        self.assertIn("absent", miss.stdout)

    def test_fail_is_never_cached(self) -> None:
        rec = self._run("record", "--mode", "affected", "--result", "FAIL")
        self.assertNotEqual(rec.returncode, 0)
        self.assertIn("only PASS", rec.stdout + rec.stderr)
        self.assertEqual(list(self.cache.glob("*.json")), [])
        miss = self._run("check")
        self.assertEqual(miss.returncode, 1)
        receipt = self.tmp / "receipt.json"
        receipt.write_text(json.dumps({"rc": 1, "modules": []}), encoding="utf-8")
        again = self._run("record", "--mode", "affected", "--receipt", str(receipt))
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual(list(self.cache.glob("*.json")), [])

    def test_corrupt_cache_file_is_a_miss(self) -> None:
        rec = self._run("record", "--mode", "structural")
        self.assertEqual(rec.returncode, 0, rec.stderr)
        files = list(self.cache.glob("*.json"))
        self.assertEqual(len(files), 1)
        files[0].write_text("{not json", encoding="utf-8")
        miss = self._run("check", "--need", "structural")
        self.assertEqual(miss.returncode, 1)
        self.assertIn("corrupt", miss.stdout)


if __name__ == "__main__":
    unittest.main()
