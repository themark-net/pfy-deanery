"""Exit test F1: the gate-rewrite check covers exactly what a build can commit."""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from tests.test_cloud_lane_busy import REVIEW_OK, _Base
from tests.test_pfy_build_cloud import _git, _run, _write_exe

HEAD = "#!/usr/bin/env python3\nimport os, sys, subprocess, time\nfrom pathlib import Path\n"


class _Rewrite(_Base):
    def build(self, agent: str, gate: str) -> dict:
        grok = _write_exe(self.side / "grok.py", HEAD + REVIEW_OK + agent)
        gate_exe = _write_exe(self.side / "gate.py", HEAD + gate)
        proc = _run(self.argv("change things", grok, gate_exe, "r"), self.repo, timeout=90)
        receipt = self.receipt("r") if (self.side / "r" / "receipt.json").exists() else {}
        receipt["_out"] = ((proc.stdout or "") + (proc.stderr or ""))[-1500:]
        receipt["_rc"] = proc.returncode
        return receipt

    def commit_file(self, rel: str, text: str, *, force: bool = False) -> None:
        path = self.repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        _git(self.repo, "add", *(["-f"] if force else []), rel)
        _git(self.repo, "commit", "-qm", "seed %s" % rel)

    def assert_rewrote(self, r: dict) -> None:
        self.assertEqual((r.get("status"), r.get("reason"), r.get("commit")), ("FAIL", "gate-rewrote", None), r)
        self.assertEqual(r["_rc"], 1, r)
        branches = _git(self.repo, "branch", "--list", "cloud/*").stdout.strip()
        self.assertEqual(branches, "", r)

    def assert_passed(self, r: dict) -> None:
        self.assertEqual((r.get("status"), r.get("reason")), ("PASS", "ok"), r)
        self.assertTrue(r.get("commit"), r)

    def committed_text(self, r: dict, rel: str) -> str:
        return _git(self.repo, "show", "%s:%s" % (r["commit"], rel)).stdout


class GateRewritesOfCommittablePathsFail(_Rewrite):
    def test_nested_tmp_file_rewritten_by_gate_fails(self) -> None:
        # Only the ROOT tmp/ is runner scratch. src/tmp/conf.py is committable.
        (self.repo / ".gitignore").write_text("/tmp/\npipelines/dogfood/build-cloud/\n", encoding="utf-8")
        _git(self.repo, "add", ".gitignore")
        _git(self.repo, "commit", "-qm", "root-only tmp ignore")
        r = self.build(
            "Path('src/tmp').mkdir(parents=True, exist_ok=True)\nPath('src/tmp/conf.py').write_text('SAFE = 1\\n')\n",
            "p = Path('src/tmp/conf.py')\nif p.exists(): p.write_text('EVIL_GATE = 1\\n')\nprint('ok')\n",
        )
        self.assert_rewrote(r)

    def test_new_untracked_file_from_gate_fails(self) -> None:
        r = self.build("Path('k.py').write_text('k = 1\\n')\n", "Path('extra.py').write_text('EVIL = 1\\n')\nprint('ok')\n")
        self.assert_rewrote(r)

    def test_gate_deleting_a_tracked_file_fails(self) -> None:
        self.commit_file("old.py", "o = 1\n")
        r = self.build(
            "Path('k.py').write_text('k = 1\\n')\n",
            "p = Path('old.py')\nif p.exists() and Path('k.py').exists(): p.unlink()\nprint('ok')\n",
        )
        self.assert_rewrote(r)

    def test_gate_rewriting_an_ignored_but_tracked_file_fails(self) -> None:
        # The path matches .gitignore but is tracked, so a change to it is committed.
        (self.repo / ".gitignore").write_text("tmp/\npipelines/dogfood/build-cloud/\n*.cfg\n", encoding="utf-8")
        _git(self.repo, "add", ".gitignore")
        _git(self.repo, "commit", "-qm", "ignore cfg")
        self.commit_file("settings.cfg", "mode = safe\n", force=True)
        r = self.build(
            "Path('k.py').write_text('k = 1\\n')\n",
            "Path('settings.cfg').write_text('mode = evil\\n')\nprint('ok')\n",
        )
        self.assert_rewrote(r)

    def test_rewrite_during_the_base_gate_only_fails(self) -> None:
        # The first gate run is the base gate before grok. A rewrite there must not be committed.
        counter = self.side / "count"
        gate = (
            "c = Path(%r)\nn = len(c.read_text()) + 1 if c.exists() else 1\nc.write_text('x' * n)\n"
            "if n == 1: Path('extra.py').write_text('EVIL = 1\\n')\nprint('ok')\n" % str(counter)
        )
        r = self.build("Path('k.py').write_text('k = 1\\n')\n", gate)
        self.assert_rewrote(r)

    def test_rewrite_during_the_commit_recheck_only_fails(self) -> None:
        # The recheck runs on a fresh extract of the commit. A rewrite there fails the build too.
        gate = "if 'recheck-' in os.getcwd(): Path('extra.py').write_text('EVIL = 1\\n')\nprint('ok')\n"
        r = self.build("Path('k.py').write_text('k = 1\\n')\n", gate)
        self.assert_rewrote(r)


class GateArtifactsThatCannotBeCommittedPass(_Rewrite):
    def test_git_metadata_writes_by_the_gate_pass(self) -> None:
        r = self.build(
            "Path('k.py').write_text('k = 1\\n')\n",
            "subprocess.run(['git', 'status'], capture_output=True)\n"
            "subprocess.run(['git', 'update-index', '--refresh'], capture_output=True)\n"
            "subprocess.run(['git', 'config', 'pfy.gateprobe', '1'], capture_output=True)\nprint('ok')\n",
        )
        self.assert_passed(r)

    def test_pycache_written_by_the_gate_passes(self) -> None:
        self.commit_file("lib/mod.py", "VALUE = 1\n")
        r = self.build(
            "Path('k.py').write_text('k = 1\\n')\n",
            "import py_compile\npy_compile.compile('lib/mod.py', cfile='lib/__pycache__/mod.cpython-x.pyc')\n"
            "py_compile.compile('k.py', cfile='__pycache__/k.cpython-x.pyc')\nprint('ok')\n",
        )
        self.assert_passed(r)
        self.assertEqual(self.committed_text(r, "k.py"), "k = 1\n")

    def test_pytest_cache_written_by_the_gate_passes(self) -> None:
        # pytest writes .pytest_cache/ with its own .gitignore of "*".
        r = self.build(
            "Path('k.py').write_text('k = 1\\n')\n",
            "d = Path('.pytest_cache')\n(d / 'v' / 'cache').mkdir(parents=True, exist_ok=True)\n"
            "(d / '.gitignore').write_text('# Created by pytest automatically.\\n*\\n')\n"
            "(d / 'v' / 'cache' / 'lastfailed').write_text('{}')\nprint('ok')\n",
        )
        self.assert_passed(r)

    def test_gitignored_coverage_artifact_passes(self) -> None:
        (self.repo / ".gitignore").write_text("tmp/\npipelines/dogfood/build-cloud/\n.coverage\n", encoding="utf-8")
        _git(self.repo, "add", ".gitignore")
        _git(self.repo, "commit", "-qm", "ignore coverage")
        r = self.build("Path('k.py').write_text('k = 1\\n')\n", "Path('.coverage').write_text('cov')\nprint('ok')\n")
        self.assert_passed(r)

    def test_gate_writing_into_its_tmpdir_passes(self) -> None:
        r = self.build(
            "Path('k.py').write_text('k = 1\\n')\n",
            "import tempfile\nwith open(os.path.join(tempfile.gettempdir(), 'gate-scratch'), 'w') as f: f.write('1')\nprint('ok')\n",
        )
        self.assert_passed(r)

    @unittest.skipUnless(importlib.util.find_spec("pytest") is not None, "sys.executable cannot import pytest")
    def test_real_pytest_gate_passes(self) -> None:
        tests = self.repo / "tests_k"
        tests.mkdir()
        (tests / "test_k.py").write_text("def test_k():\n    import k\n    assert k.k == 1\n", encoding="utf-8")
        _git(self.repo, "add", "tests_k")
        _git(self.repo, "commit", "-qm", "pytest test")
        grok = _write_exe(self.side / "grok.py", HEAD + REVIEW_OK + "Path('k.py').write_text('k = 1\\n')\n")
        argv = self.argv("add k", grok, self.side / "unused.py", "r")
        argv[argv.index("--test-cmd") + 1] = "%s -m pytest -q tests_k" % sys.executable
        proc = _run(argv, self.repo, timeout=120)
        r = self.receipt("r")
        self.assertEqual((r.get("status"), r.get("reason")), ("PASS", "ok"), (proc.stdout or "")[-1500:])


if __name__ == "__main__":
    unittest.main()
