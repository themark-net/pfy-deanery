#!/usr/bin/env python3
"""Selection modes on a real temp git repo.

How this fails: a docs edit runs the suite, a leaf edit misses an importer,
or a kalshi/trading/deploy/secret path (or .github, or an unknown file) is
allowed to skip tests. Recovery: mode full for risky, core, and unknown
paths; the nightly full suite is the backstop for a missed dynamic import.
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
SELECT = ROOT / "scripts" / "test_select.py"

PAD = 3


def _git(cwd: Path, *args: str) -> None:
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "select-test"
    env["GIT_AUTHOR_EMAIL"] = "select-test@example.com"
    env["GIT_COMMITTER_NAME"] = "select-test"
    env["GIT_COMMITTER_EMAIL"] = "select-test@example.com"
    proc = subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {args[0]} failed: {proc.stderr or proc.stdout}")


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _base_repo(tmp: Path) -> None:
    _git(tmp, "init", "-b", "main")
    _git(tmp, "config", "user.email", "select-test@example.com")
    _git(tmp, "config", "user.name", "select-test")
    _write(tmp / "pfylib" / "__init__.py", '"""pkg"""\n')
    _write(tmp / "pfylib" / "leaf.py", "VALUE = 1\n")
    _write(tmp / "pfylib" / "mid.py", "from pfylib.leaf import VALUE\n")
    _write(
        tmp / "tests" / "__init__.py",
        "",
    )
    _write(
        tmp / "tests" / "test_leaf.py",
        "from pfylib.leaf import VALUE\n\ndef test_leaf():\n    assert VALUE == 1\n",
    )
    _write(
        tmp / "tests" / "test_mid.py",
        "from pfylib.mid import VALUE\n\ndef test_mid():\n    assert VALUE == 1\n",
    )
    _write(
        tmp / "tests" / "test_other.py",
        "def test_other():\n    assert True\n",
    )
    for index in range(PAD):
        _write(
            tmp / "tests" / f"test_pad{index}.py",
            f"def test_pad_{index}():\n    assert True\n",
        )
    _write(tmp / "docs" / "readme.md", "# readme\n")
    _git(tmp, "add", "-A")
    _git(tmp, "commit", "-m", "base")


def _select(tmp: Path, base: str = "HEAD~1", head: str = "HEAD") -> dict:
    proc = subprocess.run(
        [os.sys.executable, str(SELECT), "--root", str(tmp), "--base", base, "--head", head],
        cwd=tmp,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(proc.stderr or proc.stdout)
    return json.loads(proc.stdout)


def _commit_all(tmp: Path, message: str) -> None:
    _git(tmp, "add", "-A")
    _git(tmp, "commit", "-m", message)


class TestSelectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pfy-sel-"))
        _base_repo(self.tmp)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_nothing_changed_is_none(self) -> None:
        data = _select(self.tmp, "HEAD", "HEAD")
        self.assertEqual(data["mode"], "none")
        self.assertEqual(data["modules"], [])
        self.assertEqual(data["source"], "ast")

    def test_docs_only_is_structural_with_no_modules(self) -> None:
        readme = self.tmp / "docs" / "readme.md"
        readme.write_text("# readme\n\nA sentence.\n", encoding="utf-8")
        _commit_all(self.tmp, "docs")
        data = _select(self.tmp)
        self.assertEqual(data["mode"], "structural", data["reason"])
        self.assertEqual(data["modules"], [])
        self.assertIn("docs/readme.md", data["changed"])

    def test_leaf_change_selects_only_importing_tests(self) -> None:
        leaf = self.tmp / "pfylib" / "leaf.py"
        leaf.write_text("VALUE = 1\n# touched\n", encoding="utf-8")
        _commit_all(self.tmp, "leaf")
        data = _select(self.tmp)
        self.assertEqual(data["mode"], "affected", data["reason"])
        self.assertEqual(set(data["modules"]), {"tests.test_leaf", "tests.test_mid"})
        self.assertNotIn("tests.test_other", data["modules"])
        self.assertNotIn("tests.test_pad0", data["modules"])

    def test_risky_paths_are_full(self) -> None:
        # These names sit under docs/ so a missing risky glob would be structural.
        for rel in (
            "docs/kalshi-note.md",
            "docs/trading-note.md",
            "docs/deploy-note.md",
            "docs/secret-note.md",
        ):
            with self.subTest(rel=rel):
                _git(self.tmp, "reset", "--hard", "HEAD")
                _write(self.tmp / rel, "# note\n")
                _commit_all(self.tmp, rel)
                data = _select(self.tmp)
                self.assertEqual(data["mode"], "full", data["reason"])
                self.assertIn("risky glob", data["reason"])
                self.assertGreaterEqual(len(data["modules"]), 6)

    def test_github_workflow_is_full(self) -> None:
        _write(self.tmp / ".github" / "workflows" / "ci.yml", "name: ci\n")
        _commit_all(self.tmp, "workflow")
        data = _select(self.tmp)
        self.assertEqual(data["mode"], "full", data["reason"])
        self.assertIn("core glob", data["reason"])
        self.assertIn(".github/workflows/ci.yml", data["changed"])

    def test_paths_keeps_a_leading_dot_directory(self) -> None:
        # --paths must not strip the dot. .github without it is not a core glob,
        # and the reason would be "no test reference" instead of "core glob".
        _write(self.tmp / ".github" / "workflows" / "ci.yml", "name: ci\n")
        proc = subprocess.run(
            [
                os.sys.executable,
                str(SELECT),
                "--root",
                str(self.tmp),
                "--paths",
                ".github/workflows/ci.yml",
            ],
            cwd=self.tmp,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr or proc.stdout)
        data = json.loads(proc.stdout)
        self.assertEqual(data["mode"], "full", data["reason"])
        self.assertIn("core glob", data["reason"])
        self.assertIn(".github/workflows/ci.yml", data["changed"])

    def test_unknown_file_is_full(self) -> None:
        _write(self.tmp / "blob.dat", "xyz\n")
        _commit_all(self.tmp, "blob")
        data = _select(self.tmp)
        self.assertEqual(data["mode"], "full", data["reason"])
        self.assertIn("unknown file", data["reason"])

    def test_changed_test_selects_itself(self) -> None:
        path = self.tmp / "tests" / "test_other.py"
        path.write_text("def test_other():\n    assert 1 == 1\n", encoding="utf-8")
        _commit_all(self.tmp, "test")
        data = _select(self.tmp)
        self.assertEqual(data["mode"], "affected", data["reason"])
        self.assertIn("tests.test_other", data["modules"])
        self.assertNotIn("tests.test_leaf", data["modules"])

    def test_stage_card_selects_the_assembly_test_only(self) -> None:
        # The assembly test does not embed the card path. A card edit must
        # still run that module, and must not run the rest of the suite.
        # The names are split so this file is not a string hit for the real
        # assembler module.
        card = "widget" + ".json"
        assembly = "test_stage_" + "registry.py"
        _write(
            self.tmp / "pfylib" / ("stage_" + "registry.py"),
            "def load_stages(root):\n    return {}\n",
        )
        _write(
            self.tmp / "tests" / assembly,
            "def test_load():\n    assert True\n",
        )
        _write(
            self.tmp / "data" / "stages" / card,
            '{"name": "Widget", "integration_stage": "I1"}\n',
        )
        _write(self.tmp / "data" / "notes.json", '{"ok": true}\n')
        _commit_all(self.tmp, "cards")
        _write(
            self.tmp / "data" / "stages" / card,
            '{"name": "Widget", "integration_stage": "I2"}\n',
        )
        _commit_all(self.tmp, "edit card")
        data = _select(self.tmp)
        self.assertEqual(data["mode"], "affected", data["reason"])
        self.assertEqual(data["modules"], ["tests." + "test_stage_registry"])
        _write(self.tmp / "data" / "notes.json", '{"ok": false}\n')
        _commit_all(self.tmp, "notes")
        data = _select(self.tmp)
        self.assertEqual(data["mode"], "structural", data["reason"])
        self.assertEqual(data["modules"], [])


if __name__ == "__main__":
    unittest.main()
