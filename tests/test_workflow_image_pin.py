#!/usr/bin/env python3
"""Behavior of the workflow image-pin lint: real helper, real pregate call.

Fixture files live in tests/fixtures/workflow_image_pin/. Parse cases skip
when this interpreter cannot import yaml, because the helper itself exits 1
in that case and G0's setup-python does not ship PyYAML. The missing-import
case always runs.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "check_workflow_image_pin.py"
FIX = ROOT / "tests" / "fixtures" / "workflow_image_pin"
SCRATCH = ROOT / "tmp"

try:
    import yaml  # noqa: F401

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

needs_yaml = unittest.skipUnless(
    HAS_YAML,
    "SKIP: PyYAML is not importable; the helper fails closed and these fixtures are not parsed here",
)


def run_helper(*args: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["TMPDIR"] = str(SCRATCH)
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(HELPER), *args],
        cwd=ROOT,
        env=merged,
        capture_output=True,
        text=True,
        timeout=60,
    )


class WorkflowImagePinTests(unittest.TestCase):
    def assert_pass(self, proc: subprocess.CompletedProcess[str]) -> None:
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn("PASS workflow image pin:", proc.stdout)

    def assert_fail(self, proc: subprocess.CompletedProcess[str], needle: str) -> None:
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertIn(needle, blob)

    @needs_yaml
    def test_pinned_passes(self) -> None:
        self.assert_pass(run_helper(str(FIX / "pinned.yml")))

    @needs_yaml
    def test_ubuntu_latest_fails(self) -> None:
        self.assert_fail(run_helper(str(FIX / "latest.yml")), "ubuntu-latest")

    @needs_yaml
    def test_list_containing_ubuntu_latest_fails(self) -> None:
        self.assert_fail(run_helper(str(FIX / "list-latest.yml")), "ubuntu-latest")

    @needs_yaml
    def test_matrix_expression_resolving_to_ubuntu_latest_fails(self) -> None:
        self.assert_fail(run_helper(str(FIX / "matrix-latest.yml")), "ubuntu-latest")

    @needs_yaml
    def test_self_hosted_passes(self) -> None:
        self.assert_pass(run_helper(str(FIX / "self-hosted.yml")))

    @needs_yaml
    def test_malformed_yaml_fails_closed(self) -> None:
        proc = run_helper(str(FIX / "malformed.yml"))
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertIn("malformed YAML", blob)

    @needs_yaml
    def test_pinned_matrix_expression_passes(self) -> None:
        # A resolver that rejects every ${{ }} would fail this file.
        self.assert_pass(run_helper(str(FIX / "pinned-matrix.yml")))

    @needs_yaml
    def test_unpinned_github_image_fails(self) -> None:
        proc = run_helper(str(FIX / "unpinned-image.yml"))
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        self.assertIn("ubuntu-22.04", blob)
        self.assertIn("windows-latest", blob)

    @needs_yaml
    def test_unresolved_expression_fails_closed(self) -> None:
        self.assert_fail(run_helper(str(FIX / "unresolved.yml")), "unresolved")

    @needs_yaml
    def test_reusable_workflow_without_runs_on_passes(self) -> None:
        self.assert_pass(run_helper(str(FIX / "reusable.yml")))

    @needs_yaml
    def test_missing_runs_on_fails_closed(self) -> None:
        self.assert_fail(run_helper(str(FIX / "no-runs-on.yml")), "no runs-on")

    @needs_yaml
    def test_real_workflows_pass(self) -> None:
        self.assert_pass(run_helper(str(ROOT / ".github" / "workflows")))

    @needs_yaml
    def test_empty_directory_fails_closed(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        empty = Path(tempfile.mkdtemp(prefix="image-pin-empty-", dir=SCRATCH))
        try:
            self.assert_fail(run_helper(str(empty)), "no workflow files")
        finally:
            shutil.rmtree(empty)

    def test_missing_pyyaml_fails_closed(self) -> None:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        shadow = Path(tempfile.mkdtemp(prefix="image-pin-nopyyaml-", dir=SCRATCH))
        try:
            (shadow / "yaml.py").write_text("raise ImportError('shadowed')\n", encoding="utf-8")
            env = os.environ.copy()
            env["PYTHONPATH"] = str(shadow) + os.pathsep + env.get("PYTHONPATH", "")
            proc = run_helper(str(FIX / "pinned.yml"), env=env)
            blob = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0, blob)
            self.assertIn("PyYAML is not importable", blob)
        finally:
            shutil.rmtree(shadow)

    @needs_yaml
    def test_pregate_lint_calls_helper(self) -> None:
        # --only lint is filemode, launchers, payload lint, catalog_check, and
        # this helper. It does not discover tests. MVP-3 may be busy.
        env = os.environ.copy()
        env["TMPDIR"] = str(SCRATCH)
        proc = subprocess.run(
            [
                "nice",
                "-n",
                "19",
                "scripts/pregate.sh",
                "--in-place",
                "--allow-dirty",
                "--only",
                "lint",
            ],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=240,
        )
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn("OVERALL=PASS", proc.stdout)
        match = re.search(r"Summary: (\S+)", proc.stdout)
        self.assertIsNotNone(match, blob)
        log = Path(match.group(1)).parent / "logs" / "lint.log"
        text = log.read_text(encoding="utf-8")
        self.assertIn("PASS workflow image pin:", text)


if __name__ == "__main__":
    unittest.main()
