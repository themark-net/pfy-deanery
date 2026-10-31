#!/usr/bin/env python3
"""Behavior of the workflow image-pin lint: real helper, real pregate call.

Fixture files live in tests/fixtures/workflow_image_pin/. Parse cases skip
when this interpreter cannot import yaml, because the helper itself exits 1
in that case and G0's setup-python does not ship PyYAML. The missing-import
case always runs. The pregate lint test does not execute scripts/pregate.sh,
so it does not write tmp/pregate-runs. It reads check_lint's live shell and
runs the helper with PATH python3.
"""
from __future__ import annotations

import os
import re
import shlex
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


def path_python3_has_yaml(path: str | None = None) -> bool:
    """True when the python3 pregate will exec can import PyYAML.

    pregate.sh calls ``python3`` from PATH. Importing yaml in this process
    (sys.executable) is a different interpreter and must not decide the skip.
    """
    python3 = shutil.which("python3", path=path) if path is not None else shutil.which("python3")
    if not python3:
        return False
    proc = subprocess.run(
        [python3, "-c", "import yaml"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return proc.returncode == 0


def _strip_unquoted_comment(line: str) -> str:
    in_single = False
    in_double = False
    out: list[str] = []
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            break
        out.append(ch)
        i += 1
    return "".join(out)


def check_lint_live_shell() -> str:
    """check_lint body with comments removed, so a commented-out call does not count."""
    text = (ROOT / "scripts" / "pregate.sh").read_text(encoding="utf-8")
    match = re.search(r"^check_lint\(\) \{\n(.*?)\n\}", text, re.M | re.S)
    if not match:
        raise AssertionError("check_lint() not found in scripts/pregate.sh")
    kept: list[str] = []
    for line in match.group(1).splitlines():
        code = _strip_unquoted_comment(line).strip()
        if code:
            kept.append(code)
    return "\n".join(kept)


def pregate_run_names() -> list[set[str]]:
    """Names currently in each pregate-runs dir this repo can write."""
    proc = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    roots = [Path(proc.stdout.strip()).parent / "tmp" / "pregate-runs", ROOT / "tmp" / "pregate-runs"]
    found: list[set[str]] = []
    for runs in roots:
        if runs.is_dir():
            found.append({path.name for path in runs.iterdir()})
        else:
            found.append(set())
    return found


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
    def test_duplicate_key_fails_even_when_the_last_value_is_pinned(self) -> None:
        # safe_load keeps the last runs-on, so this file would look pinned.
        # Recovery: delete the repeated key.
        SCRATCH.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="dup-key-", dir=SCRATCH))
        path = directory / "dup.yml"
        path.write_text(
            "name: dup\n"
            "on: push\n"
            "jobs:\n"
            "  build:\n"
            "    runs-on: ubuntu-latest\n"
            "    runs-on: ubuntu-24.04\n"
            "    steps:\n"
            "      - run: \"true\"\n",
            encoding="utf-8",
        )
        try:
            self.assert_fail(run_helper(str(path)), "duplicate key 'runs-on'")
        finally:
            shutil.rmtree(directory)

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

    def _structural(self, steps: str) -> Path:
        SCRATCH.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="rg-step-", dir=SCRATCH))
        path = directory / "eval-structural.yml"
        path.write_text(
            "name: eval-structural\n"
            "on: push\n"
            "jobs:\n"
            "  structural-github:\n"
            "    runs-on: ubuntu-24.04\n"
            "    steps:\n"
            + steps,
            encoding="utf-8",
        )
        return path

    @needs_yaml
    def test_ripgrep_word_in_a_comment_does_not_pass(self) -> None:
        path = self._structural(
            "      # the old check only looked for the word ripgrep\n"
            "      - run: echo ok\n"
        )
        try:
            self.assert_fail(run_helper(str(path)), "does not install ripgrep")
        finally:
            shutil.rmtree(path.parent)

    @needs_yaml
    def test_echo_ripgrep_does_not_pass(self) -> None:
        path = self._structural("      - name: Install ripgrep\n        run: echo ripgrep\n")
        try:
            self.assert_fail(run_helper(str(path)), "does not install ripgrep")
        finally:
            shutil.rmtree(path.parent)

    @needs_yaml
    def test_commented_out_apt_install_does_not_pass(self) -> None:
        path = self._structural(
            "      - name: Install ripgrep\n"
            "        run: |\n"
            "          # sudo apt-get install -y -qq ripgrep\n"
            "          echo skipped\n"
        )
        try:
            self.assert_fail(run_helper(str(path)), "does not install ripgrep")
        finally:
            shutil.rmtree(path.parent)

    @needs_yaml
    def test_install_without_running_rg_fails(self) -> None:
        path = self._structural(
            "      - run: |\n"
            "          sudo apt-get install -y -qq ripgrep\n"
        )
        try:
            self.assert_fail(run_helper(str(path)), "does not run rg")
        finally:
            shutil.rmtree(path.parent)

    @needs_yaml
    def test_apt_install_and_rg_version_passes(self) -> None:
        path = self._structural(
            "      - name: Install ripgrep\n"
            "        run: |\n"
            "          if ! command -v rg >/dev/null 2>&1; then\n"
            "            sudo apt-get install -y -qq ripgrep\n"
            "          fi\n"
            "          rg --version | head -1\n"
        )
        try:
            self.assert_pass(run_helper(str(path)))
        finally:
            shutil.rmtree(path.parent)

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

    def test_yaml_probe_uses_the_python3_on_path(self) -> None:
        # A python3 earlier on PATH that cannot import yaml must not be hidden
        # by this process's interpreter. The positive half execs the real
        # PATH python3 via that same slot, so a probe of sys.executable fails
        # the negative half instead of passing both.
        SCRATCH.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="path-python3-", dir=SCRATCH))
        try:
            fake = directory / "python3"
            fake.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
            fake.chmod(0o755)
            self.assertFalse(path_python3_has_yaml(str(directory)))
            real = shutil.which("python3")
            self.assertIsNotNone(real)
            if not path_python3_has_yaml():
                return
            fake.write_text(
                "#!/bin/sh\nexec " + shlex.quote(real) + ' "$@"\n',
                encoding="utf-8",
            )
            fake.chmod(0o755)
            self.assertTrue(path_python3_has_yaml(str(directory)))
        finally:
            shutil.rmtree(directory)

    def test_pregate_lint_calls_helper(self) -> None:
        # Running scripts/pregate.sh from unittest writes tmp/pregate-runs on
        # the git common dir (the main checkout, from a linked worktree).
        # The live shell must call the helper. PATH python3 then runs that
        # helper on a workflow whose only ripgrep mention is a comment.
        before = pregate_run_names()
        live = check_lint_live_shell()
        self.assertIn(
            "python3 scripts/check_workflow_image_pin.py .github/workflows",
            live,
        )
        python3 = shutil.which("python3")
        self.assertIsNotNone(python3)
        path = self._structural("      # ripgrep\n      - run: echo ok\n")
        try:
            env = os.environ.copy()
            env["TMPDIR"] = str(SCRATCH)
            proc = subprocess.run(
                [python3, str(HELPER), str(path)],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            blob = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0, blob)
            if path_python3_has_yaml():
                self.assertIn("does not install ripgrep", blob)
            else:
                self.assertIn("PyYAML is not importable", blob)
        finally:
            shutil.rmtree(path.parent)
        after = pregate_run_names()
        for old, new in zip(before, after):
            self.assertEqual(new - old, set())


if __name__ == "__main__":
    unittest.main()
