"""Wave-5 catalog checks for the cloud mutation harness.

C17-C43 each change the runner once and still parse. The source file is
not written. Harness modules are not part of a mutant's suite, so a
mutant run does not start the harness again.
"""

from __future__ import annotations

import ast
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "eval" / "mutation-1031" / "cloud" / "run_mutants.py"
RUNNER = ROOT / "scripts" / "pfy_build_cloud.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("cloud_run_mutants_wave5", HARNESS)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load harness")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Cloud2CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.mod = load_harness()
        cls.runner_text = RUNNER.read_text(encoding="utf-8")
        cls.runner_hash = cls.mod.hash_file(RUNNER)

    def tearDown(self) -> None:
        self.assertEqual(self.mod.hash_file(RUNNER), self.runner_hash)
        self.assertEqual(RUNNER.read_text(encoding="utf-8"), self.runner_text)

    def test_wave5_mutants_each_apply_once_and_parse(self) -> None:
        ids = [item["id"] for item in self.mod.CLOUD2_MUTANTS]
        self.assertGreaterEqual(len(ids), 20)
        self.assertEqual(ids, ["C%s" % number for number in range(17, 17 + len(ids))])
        self.assertEqual([item["id"] for item in self.mod.MUTANTS], ["C%s" % number for number in range(1, 17)])
        seen = set()
        for mutant in self.mod.CLOUD2_MUTANTS:
            self.assertNotIn(mutant["id"], seen)
            seen.add(mutant["id"])
            mutated = self.mod.apply_text(self.runner_text, mutant)
            self.assertNotEqual(mutated, self.runner_text, mutant["id"])
            ast.parse(mutated)
            self.assertIn(mutant["new"], mutated, mutant["id"])

    def test_mutant_suite_skips_harness_modules_and_keeps_survivor_tests(self) -> None:
        modules = self.mod.cloud_modules(ROOT, baseline_only=False)
        self.assertIn("tests.test_pfy_build_cloud", modules)
        self.assertIn("tests.test_mut_cloud_survivors", modules)
        self.assertNotIn("tests.test_mut_cloud_harness", modules)
        self.assertNotIn("tests.test_mut_cloud2_harness", modules)
        baseline = self.mod.cloud_modules(ROOT, baseline_only=True)
        self.assertIn("tests.test_pfy_build_cloud", baseline)
        self.assertNotIn("tests.test_mut_cloud_survivors", baseline)
        self.assertTrue(all(not name.endswith("_harness") for name in modules))

    def test_detail_prefers_the_unittest_failure_over_a_printed_reason(self) -> None:
        # Fail: the report names FAIL: commit-recheck-failed from a passing
        # recovery test, so a real kill is hidden.
        # Recover: the first FAIL: test_ line is the detail.
        text = (
            "FAIL: commit-recheck-failed\n"
            "Mark: the fresh extract of the commit did not pass the gate.\n"
            "FAIL: test_star_filename_commits_that_file_and_not_the_pyc "
            "(tests.test_pfy_build_cloud.CloudBuildNoChangeTests)\n"
            "AssertionError: 1 != 0\n"
        )
        detail = self.mod.first_detail(text)
        self.assertIn("test_star_filename_commits_that_file_and_not_the_pyc", detail)
        self.assertNotIn("commit-recheck-failed", detail)


if __name__ == "__main__":
    unittest.main()
