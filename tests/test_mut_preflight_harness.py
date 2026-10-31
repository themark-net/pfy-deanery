"""Behavior tests for the preflight mutation harness.

A mutant is applied only inside a throwaway clone. The source files stay
byte-for-byte the same. A suite that fails is killed. A suite that passes
is survived. A hang is killed. A missed anchor is not survived.

How this fails and how it recovers:

- A clone dest outside ``<source>/tmp`` returns status ``error`` and does not
  create the dest. Recovery: refuse before ``git clone``.
- A missed anchor is ``unapplicable``, not survived, and the command exits 2.
  Recovery: fix that anchor and re-run. Do not treat the row as a weak test.
- A suite that exceeds its timeout is killed, and processes whose cwd is
  still the clone are signaled. Recovery: the next mutant starts from a
  fresh clone.
"""

from __future__ import annotations

import ast
import importlib.util
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "eval" / "mutation-1031" / "preflight" / "run_mutants.py"
CLASSIFIER = ROOT / "pfylib" / "build_preflight.py"
CHECKER = ROOT / "eval" / "mvp-1031" / "check_receipt.py"
FIXTURES = ROOT / "tmp" / "mutation-1031" / "preflight" / "fixtures"


def load_harness():
    spec = importlib.util.spec_from_file_location("preflight_run_mutants", HARNESS)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load harness")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> None:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)


class HarnessBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_harness()
        cls.classifier_hash = cls.mod.hash_file(CLASSIFIER)
        cls.checker_hash = cls.mod.hash_file(CHECKER)

    def tearDown(self) -> None:
        self.assertEqual(self.mod.hash_file(CLASSIFIER), self.classifier_hash)
        self.assertEqual(self.mod.hash_file(CHECKER), self.checker_hash)
        shutil.rmtree(FIXTURES, ignore_errors=True)

    def test_catalog_applies_once_and_parses(self) -> None:
        classifier = CLASSIFIER.read_text(encoding="utf-8")
        checker = CHECKER.read_text(encoding="utf-8")
        texts = {
            "pfylib/build_preflight.py": classifier,
            "eval/mvp-1031/check_receipt.py": checker,
        }
        ids = [item["id"] for item in self.mod.MUTANTS]
        self.assertGreaterEqual(len(ids), 15)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("P1", ids)
        self.assertIn("R1", ids)
        for mutant in self.mod.MUTANTS:
            self.assertIn(mutant["target"], texts)
            mutated = self.mod.apply_text(texts[mutant["target"]], mutant)
            self.assertNotEqual(mutated, texts[mutant["target"]], mutant["id"])
            ast.parse(mutated)
        self.assertEqual(CLASSIFIER.read_text(encoding="utf-8"), classifier)
        self.assertEqual(CHECKER.read_text(encoding="utf-8"), checker)

    def test_suite_skips_the_harness_module(self) -> None:
        # Fail: including this module in a mutant run starts the harness again.
        # Recover: baseline is the two product suites; later rounds add survivor tests only.
        base = self.mod.suite_modules(ROOT, True)
        self.assertEqual(
            base,
            ["tests.test_build_preflight", "tests.test_mvp_1031_receipt"],
        )
        full = self.mod.suite_modules(ROOT, False)
        self.assertNotIn("tests.test_mut_preflight_harness", full)
        for name in base:
            self.assertIn(name, full)

    def test_killed_and_survived_leave_the_source_file(self) -> None:
        src = self._fixture(
            "value-repo",
            "app.py",
            "# marker keep\nVALUE = 1\n",
            "import app\n"
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_value(self):\n"
            "        self.assertEqual(app.VALUE, 1)\n",
        )
        killed = self.mod.evaluate(
            src=src,
            dest=src / "tmp" / "clone-killed",
            mutant={"id": "K", "title": "value flipped", "target": "app.py", "old": "VALUE = 1\n", "new": "VALUE = 2\n"},
            modules=["tests.test_app"],
            timeout=30,
            script_rel="app.py",
        )
        self.assertEqual(killed["status"], "killed", killed)
        self.assertIn("VALUE = 1\n", (src / "app.py").read_text(encoding="utf-8"))
        survived = self.mod.evaluate(
            src=src,
            dest=src / "tmp" / "clone-survived",
            mutant={"id": "S", "title": "comment only", "target": "app.py", "old": "# marker keep\n", "new": "# marker changed\n"},
            modules=["tests.test_app"],
            timeout=30,
            script_rel="app.py",
        )
        self.assertEqual(survived["status"], "survived", survived)
        self.assertIn("VALUE = 1\n", (src / "app.py").read_text(encoding="utf-8"))

    def test_hang_is_killed_and_anchor_miss_is_not_survived(self) -> None:
        src = self._fixture(
            "hang-repo",
            "app.py",
            "# marker keep\nVALUE = 1\n",
            "import time\n"
            "import unittest\n"
            "class T(unittest.TestCase):\n"
            "    def test_sleep(self):\n"
            "        time.sleep(30)\n",
        )
        hung = self.mod.evaluate(
            src=src,
            dest=src / "tmp" / "clone-hang",
            mutant={"id": "H", "title": "comment only", "target": "app.py", "old": "# marker keep\n", "new": "# marker changed\n"},
            modules=["tests.test_app"],
            timeout=2,
            script_rel="app.py",
        )
        self.assertEqual(hung["status"], "killed", hung)
        self.assertEqual(hung["detail"], "timeout")
        self.assertLess(hung["seconds"], 15)
        missed = self.mod.evaluate(
            src=src,
            dest=src / "tmp" / "clone-miss",
            mutant={"id": "M", "title": "missing", "target": "app.py", "old": "NOT-IN-FILE\n", "new": "NOPE\n"},
            modules=["tests.test_app"],
            timeout=30,
            script_rel="app.py",
        )
        self.assertEqual(missed["status"], "unapplicable", missed)
        self.assertNotEqual(missed["status"], "survived")

    def test_clone_outside_source_tmp_is_refused(self) -> None:
        dest = ROOT / "eval" / "mutation-1031" / "preflight" / "not-a-clone"
        row = self.mod.evaluate(
            src=ROOT,
            dest=dest,
            mutant=None,
            modules=["tests.test_mut_preflight_harness"],
            timeout=5,
            script_rel="pfylib/build_preflight.py",
        )
        self.assertEqual(row["status"], "error", row)
        self.assertNotEqual(row["status"], "survived")
        self.assertIn("refusing clone", row["detail"])
        self.assertFalse(dest.exists())

    def _fixture(self, name: str, script_name: str, script_body: str, test_body: str) -> Path:
        src = FIXTURES / name
        if src.exists():
            shutil.rmtree(src)
        (src / "tests").mkdir(parents=True)
        (src / "tmp").mkdir()
        (src / script_name).write_text(script_body, encoding="utf-8")
        (src / "tests" / "__init__.py").write_text("", encoding="utf-8")
        (src / "tests" / "test_app.py").write_text(test_body, encoding="utf-8")
        git(src, "init", "-b", "main")
        git(src, "config", "user.email", "mut-test@example.com")
        git(src, "config", "user.name", "mut-test")
        git(src, "add", script_name, "tests")
        git(src, "commit", "-m", "fixture")
        return src


if __name__ == "__main__":
    unittest.main()
