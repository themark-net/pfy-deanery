"""Behavior tests for the cloud mutation harness.

A mutant is applied only inside a throwaway clone. The source file stays
byte-for-byte the same. A suite that fails is killed. A suite that passes
is survived. A hang is killed. A missed anchor is not survived.
"""

from __future__ import annotations

import ast
import importlib.util
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "eval" / "mutation-1031" / "cloud" / "run_mutants.py"
RUNNER = ROOT / "scripts" / "pfy_build_cloud.py"
FIXTURES = ROOT / "tmp" / "mutation-1031" / "cloud" / "fixtures"


def load_harness():
    spec = importlib.util.spec_from_file_location("cloud_run_mutants", HARNESS)
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
        cls.runner_hash = cls.mod.hash_file(RUNNER)

    def tearDown(self) -> None:
        self.assertEqual(self.mod.hash_file(RUNNER), self.runner_hash)
        shutil.rmtree(FIXTURES, ignore_errors=True)

    def test_catalog_applies_once_and_parses(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        ids = [item["id"] for item in self.mod.MUTANTS]
        self.assertEqual(ids, ["C%s" % number for number in range(1, 17)])
        for mutant in self.mod.MUTANTS:
            mutated = self.mod.apply_text(source, mutant)
            self.assertNotEqual(mutated, source, mutant["id"])
            ast.parse(mutated)
        self.assertEqual(RUNNER.read_text(encoding="utf-8"), source)

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
            mutant={"id": "K", "title": "value flipped", "old": "VALUE = 1\n", "new": "VALUE = 2\n"},
            modules=["tests.test_app"],
            timeout=30,
            script_rel="app.py",
        )
        self.assertEqual(killed["status"], "killed", killed)
        self.assertIn("VALUE = 1\n", (src / "app.py").read_text(encoding="utf-8"))
        survived = self.mod.evaluate(
            src=src,
            dest=src / "tmp" / "clone-survived",
            mutant={"id": "S", "title": "comment only", "old": "# marker keep\n", "new": "# marker changed\n"},
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
            mutant={"id": "H", "title": "comment only", "old": "# marker keep\n", "new": "# marker changed\n"},
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
            mutant={"id": "M", "title": "missing", "old": "NOT-IN-FILE\n", "new": "NOPE\n"},
            modules=["tests.test_app"],
            timeout=30,
            script_rel="app.py",
        )
        self.assertEqual(missed["status"], "unapplicable", missed)
        self.assertNotEqual(missed["status"], "survived")

    def test_clone_outside_source_tmp_is_refused(self) -> None:
        dest = ROOT / "eval" / "mutation-1031" / "cloud" / "not-a-clone"
        row = self.mod.evaluate(
            src=ROOT,
            dest=dest,
            mutant=None,
            modules=["tests.test_mut_cloud_harness"],
            timeout=5,
            script_rel="scripts/pfy_build_cloud.py",
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
