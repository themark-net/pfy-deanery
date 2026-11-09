"""Behavior of the review mutation harness.

A throwaway fixture clone classifies a real failure as killed, a comment-only
edit as survived, a missing anchor as not-applied, and a hung suite as timeout.
The worktree runner is never written. A red baseline is not scored as kills.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import unittest
from pathlib import Path

from tests._ops import OPS, present, require  # noqa: E402


REPO = Path(__file__).resolve().parents[1]
RUNNER = REPO / "scripts" / "pfy_build_local.py"
SCRATCH = REPO / "tmp" / "mutation-1031" / "harness-tests"
HARNESS = OPS / "eval" / "mutation-1031" / "review" / "run_mutants.py"


def _load():
    path = HARNESS
    spec = importlib.util.spec_from_file_location("review_mutants_under_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load run_mutants")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MUT = _load() if present(HARNESS) else None


def setUpModule() -> None:
    require(HARNESS)


def _git(cwd, *args):
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "mut-harness"
    env["GIT_AUTHOR_EMAIL"] = "mut-harness@example.com"
    env["GIT_COMMITTER_NAME"] = "mut-harness"
    env["GIT_COMMITTER_EMAIL"] = "mut-harness@example.com"
    subprocess.run(["git", "-C", str(cwd), *args], check=True, env=env, capture_output=True)


class HarnessBehaviorTests(unittest.TestCase):
    def setUp(self):
        if SCRATCH.exists():
            shutil.rmtree(SCRATCH)
        SCRATCH.mkdir(parents=True)
        self.source = SCRATCH / "src"
        self.clone = SCRATCH / "clone"
        self.report = SCRATCH / "REPORT.md"
        self._init_fixture()
        self.runner_before = RUNNER.read_bytes()
        self.widget = self.source / "widget.py"

    def tearDown(self):
        self.assertEqual(RUNNER.read_bytes(), self.runner_before)
        if SCRATCH.exists():
            shutil.rmtree(SCRATCH, ignore_errors=True)

    def _init_fixture(self):
        self.source.mkdir(parents=True)
        (self.source / "widget.py").write_text(
            "# stable\ndef answer():\n    return \"keep\"\n",
            encoding="utf-8",
        )
        tests = self.source / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_widget.py").write_text(
            "import time\n"
            "import unittest\n"
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[1]\n"
            "class WidgetTests(unittest.TestCase):\n"
            "    def test_keeps_the_word(self):\n"
            "        ns = {}\n"
            "        exec((ROOT / 'widget.py').read_text(encoding='utf-8'), ns)\n"
            "        self.assertEqual(ns['answer'](), 'keep')\n"
            "    def test_would_call_a_model(self):\n"
            "        self.fail('this test would call a model')\n"
            "    def test_sleeps_when_marked(self):\n"
            "        text = (ROOT / 'widget.py').read_text(encoding='utf-8')\n"
            "        if 'SLOW' in text:\n"
            "            time.sleep(30)\n",
            encoding="utf-8",
        )
        _git(self.source, "init", "-q")
        _git(self.source, "add", ".")
        _git(self.source, "commit", "-q", "-m", "fixture")

    def _mutants(self):
        return [
            MUT.Mutant("R-flip", "answer flipped", "", (("return \"keep\"\n", "return \"drop\"\n"),)),
            MUT.Mutant("R-note", "comment only", "", (("# stable\n", "# nudged\n"),)),
            MUT.Mutant("R-miss", "missing anchor", "", (("NO-SUCH-ANCHOR-1031\n", "nope\n"),)),
            MUT.Mutant("R-slow", "sleeps", "", (("# stable\n", "# SLOW\n"),)),
        ]

    def _run(self, mutants, exclude, timeout_s):
        return MUT.run_campaign(
            source_repo=self.source,
            clone_dest=self.clone,
            worktree=REPO,
            mutants=mutants,
            modules=["tests.test_widget"],
            exclude=exclude,
            timeout_s=timeout_s,
            tmpdir=SCRATCH / "run",
            report_path=self.report,
            protect_files=[RUNNER, self.widget],
            runner_rel="widget.py",
            audit="fixture",
        )

    def test_campaign_classifies_kill_survive_miss_and_timeout(self):
        exclude = ["tests.test_widget.WidgetTests.test_would_call_a_model"]
        outcome = self._run(self._mutants(), exclude, timeout_s=2)
        by_id = {row["id"]: row for row in outcome["rows"]}
        self.assertEqual(by_id["R-flip"]["result"], "killed")
        self.assertIn("test_keeps_the_word", by_id["R-flip"]["first_failure"])
        self.assertEqual(by_id["R-note"]["result"], "survived")
        self.assertEqual(by_id["R-miss"]["result"], "not-applied")
        self.assertEqual(by_id["R-slow"]["result"], "timeout")
        self.assertIn(exclude[0], outcome["meta"]["excluded"])
        self.assertEqual(outcome["meta"]["baseline"], "pass")
        text = self.report.read_text(encoding="utf-8")
        self.assertIn("| R-flip |", text)
        self.assertIn("| killed |", text)
        self.assertIn("Survivors before: 1 (R-note)", text)
        clone_widget = (self.clone / "widget.py").read_text(encoding="utf-8")
        self.assertIn("return \"keep\"", clone_widget)
        self.assertNotIn("SLOW", clone_widget)
        self.assertEqual(self.widget.read_text(encoding="utf-8"), "# stable\ndef answer():\n    return \"keep\"\n")

    def test_red_baseline_is_not_scored_as_kills(self):
        outcome = self._run(self._mutants()[:1], exclude=[], timeout_s=5)
        self.assertEqual(outcome["rows"][0]["result"], "skipped-red-base")
        self.assertNotEqual(outcome["rows"][0]["result"], "killed")
        self.assertIn("red-base", outcome["meta"]["baseline"])
        self.assertEqual(outcome["meta"]["modules"], [])

    def test_refuses_a_clone_outside_the_worktree_tmp(self):
        with self.assertRaises(RuntimeError):
            MUT.run_campaign(
                source_repo=self.source,
                clone_dest=REPO / "eval" / "mutation-1031" / "review-clone",
                worktree=REPO,
                mutants=[],
                modules=["tests.test_widget"],
                exclude=[],
                timeout_s=1,
                tmpdir=SCRATCH / "run",
                report_path=None,
                protect_files=[RUNNER],
                runner_rel="widget.py",
            )
        self.assertFalse((REPO / "eval" / "mutation-1031" / "review-clone").exists())

    def test_write_refuses_the_worktree_runner(self):
        mutant = MUT.CATALOG[0]
        with self.assertRaises(RuntimeError):
            MUT.write_mutant(RUNNER, [RUNNER], mutant, RUNNER.read_text(encoding="utf-8"))
        self.assertEqual(RUNNER.read_bytes(), self.runner_before)

    def test_survivor_modules_omit_the_harness_and_an_override_replaces_the_suite(self):
        tests = self.source / "tests"
        (tests / "test_mut_review_harness.py").write_text("raise SystemExit('harness')\n", encoding="utf-8")
        (tests / "test_mut_review_size_cap.py").write_text("# size cap\n", encoding="utf-8")
        names = MUT.survivor_modules(self.source)
        self.assertEqual(names, ["tests.test_mut_review_size_cap"])
        real = MUT.survivor_modules(REPO)
        self.assertIn("tests.test_mut_review_size_cap", real)
        self.assertNotIn("tests.test_mut_review_harness", real)
        override = MUT.modules_for(REPO, "tests.test_mut_review_size_cap")
        self.assertEqual(override, ["tests.test_mut_review_size_cap"])
        self.assertNotIn("tests.test_pfy_build_local_review", override)
        self.assertEqual(MUT.modules_for(REPO, ""), MUT.review_modules(REPO))

    def test_catalog_anchors_match_a_copy_of_the_runner(self):
        self.assertEqual(len(MUT.CATALOG), 14)
        ids = [item.id for item in MUT.CATALOG]
        self.assertEqual(ids, ["R%d" % n for n in range(1, 15)])
        reviewers = {item.id: item.reviewer for item in MUT.CATALOG}
        self.assertEqual(reviewers["R4"], "M4")
        self.assertEqual(reviewers["R5"], "M7")
        rc = MUT.check_anchors(REPO)
        self.assertEqual(rc, 0)
        self.assertEqual(RUNNER.read_bytes(), self.runner_before)
        text = RUNNER.read_text(encoding="utf-8")
        for mutant in MUT.CATALOG:
            mutated = MUT.apply_text(text, mutant)
            self.assertNotEqual(mutated, text)
            self.assertEqual(RUNNER.read_text(encoding="utf-8"), text)
