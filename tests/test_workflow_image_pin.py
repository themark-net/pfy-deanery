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
FIX_CONTAINER = ROOT / "tests" / "fixtures" / "workflow_container_pin"
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


def _image_pin_step_command(steps: object) -> str | None:
    """Return the shell of the step that runs the image-pin helper, if any."""
    if not isinstance(steps, list):
        return None
    found: str | None = None
    for step in steps:
        if not isinstance(step, dict):
            continue
        run = step.get("run")
        if not isinstance(run, str):
            continue
        if "check_workflow_image_pin.py" in run:
            found = run
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
    def test_hosted_ci_step_invokes_image_pin_lint(self) -> None:
        """The hosted G0 job must run the helper. Parse the workflow; do not grep the file.

        A shell comment that names the script is not a step. The test runs the
        parsed step with a PATH python3 that records its argv, so an echo of the
        PASS line does not count as invoking the lint.
        """
        import yaml

        path = ROOT / ".github" / "workflows" / "eval-structural.yml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)
        jobs = data.get("jobs")
        self.assertIsInstance(jobs, dict)
        job = jobs.get("structural-github")
        self.assertIsInstance(job, dict, "hosted job structural-github missing")
        self.assertEqual(job.get("runs-on"), "ubuntu-24.04")
        command = _image_pin_step_command(job.get("steps"))
        self.assertIsNotNone(command, "hosted job has no image-pin step")
        # Comment-only mentions do not count: strip shell comments before matching.
        code_lines = []
        for line in command.splitlines():
            code = line.split("#", 1)[0].strip()
            if code:
                code_lines.append(code)
        body = "\n".join(code_lines)
        self.assertIn("scripts/check_workflow_image_pin.py", body)
        self.assertIn(".github/workflows", body)

        SCRATCH.mkdir(parents=True, exist_ok=True)
        wrap = Path(tempfile.mkdtemp(prefix="image-pin-ci-wrap-", dir=SCRATCH))
        try:
            log = wrap / "argv.log"
            wrapper = wrap / "python3"
            wrapper.write_text(
                "#!/bin/sh\n"
                f"printf '%s\\n' \"$0 $*\" >> {str(log)!r}\n"
                f"exec {sys.executable} \"$@\"\n",
                encoding="utf-8",
            )
            wrapper.chmod(0o755)
            env = os.environ.copy()
            env["TMPDIR"] = str(SCRATCH)
            env["PATH"] = str(wrap) + os.pathsep + env.get("PATH", "")
            proc = subprocess.run(
                ["bash", "-c", command],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            blob = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 0, blob)
            self.assertIn("PASS workflow image pin:", proc.stdout)
            recorded = log.read_text(encoding="utf-8") if log.is_file() else ""
            self.assertIn("scripts/check_workflow_image_pin.py", recorded, recorded or blob)
            self.assertIn(".github/workflows", recorded, recorded or blob)
        finally:
            shutil.rmtree(wrap)

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
            self.assertIn("PyYAML is not importable in %s" % sys.executable, blob)
            self.assertIn(sys.executable, blob)
        finally:
            shutil.rmtree(shadow)

    @needs_yaml
    def test_path_python_without_yaml_fails_closed_for_both_call_sites(self) -> None:
        """Pregate and the hosted step must use PATH python3, and name it when it lacks PyYAML.

        A later interpreter that has PyYAML must not make this PATH pass.
        """
        import yaml

        SCRATCH.mkdir(parents=True, exist_ok=True)
        venv = Path(tempfile.mkdtemp(prefix="image-pin-venv-", dir=SCRATCH))
        try:
            made = subprocess.run(
                [sys.executable, "-m", "venv", "--without-pip", str(venv)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(made.returncode, 0, made.stdout + made.stderr)
            pin_py = venv / "bin" / "python3"
            self.assertTrue(pin_py.is_file(), pin_py)
            probe = subprocess.run(
                [str(pin_py), "-c", "import yaml"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertNotEqual(probe.returncode, 0, "venv python unexpectedly imports yaml")
            env = os.environ.copy()
            env["TMPDIR"] = str(SCRATCH)
            env["PATH"] = str(venv / "bin") + os.pathsep + env.get("PATH", "")
            env["PREGATE_MAX_ROOT_LEN"] = "200"
            needle = "PyYAML is not importable in %s" % pin_py

            data = yaml.safe_load(
                (ROOT / ".github" / "workflows" / "eval-structural.yml").read_text(encoding="utf-8")
            )
            command = _image_pin_step_command(data["jobs"]["structural-github"]["steps"])
            self.assertIsNotNone(command)
            ci = subprocess.run(
                ["bash", "-c", command],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=60,
            )
            ci_blob = ci.stdout + ci.stderr
            self.assertNotEqual(ci.returncode, 0, ci_blob)
            self.assertIn(needle, ci_blob, ci_blob)

            pre = subprocess.run(
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
            pre_blob = pre.stdout + pre.stderr
            self.assertNotEqual(pre.returncode, 0, pre_blob)
            match = re.search(r"Summary: (\S+)", pre.stdout)
            self.assertIsNotNone(match, pre_blob)
            log = Path(match.group(1)).parent / "logs" / "lint.log"
            text = log.read_text(encoding="utf-8")
            self.assertIn(needle, text, text)
        finally:
            shutil.rmtree(venv)

    @needs_yaml
    def test_container_and_service_tags_pass(self) -> None:
        for name in (
            "container-string.yml",
            "container-mapping.yml",
            "service-tag.yml",
            "registry-port.yml",
            "digest-all.yml",
        ):
            self.assert_pass(run_helper(str(FIX_CONTAINER / name)))

    @needs_yaml
    def test_container_and_service_tags_fail(self) -> None:
        cases = (
            ("container-latest.yml", "image tag is latest"),
            ("container-latest-upper.yml", "image tag is latest"),
            ("container-no-tag.yml", "image has no tag"),
            ("container-empty-tag.yml", "image has no tag"),
            ("container-mapping-latest.yml", "image tag is latest"),
            ("service-latest.yml", "image tag is latest"),
            ("service-no-tag.yml", "image has no tag"),
            ("registry-port-no-tag.yml", "image has no tag"),
            ("digest-short.yml", "image digest is not @sha256:"),
            ("unresolved-image.yml", "unresolved image expression"),
            ("digest-mixed.yml", "image is missing @sha256: digest"),
        )
        for name, needle in cases:
            self.assert_fail(run_helper(str(FIX_CONTAINER / name)), needle)

    @needs_yaml
    def test_digest_requirement_spans_files_in_one_run(self) -> None:
        # A tag-only file passes alone. The same file fails when another file
        # in the same invocation already pins @sha256:.
        self.assert_pass(run_helper(str(FIX_CONTAINER / "container-string.yml")))
        self.assert_fail(
            run_helper(
                str(FIX_CONTAINER / "digest-all.yml"),
                str(FIX_CONTAINER / "container-string.yml"),
            ),
            "image is missing @sha256: digest",
        )

    @needs_yaml
    def test_malformed_container_and_service_forms_fail_closed(self) -> None:
        proc = run_helper(str(FIX_CONTAINER / "malformed-forms.yml"))
        blob = proc.stdout + proc.stderr
        self.assertNotEqual(proc.returncode, 0, blob)
        for needle in (
            "container is not a string or a mapping",
            "container has no image",
            "services is not a mapping",
            "services is empty",
            "service has no image",
            "image is not a string",
            "service is not a mapping",
        ):
            self.assertIn(needle, blob, needle)

    @needs_yaml
    def test_pregate_lint_calls_helper(self) -> None:
        # --only lint is filemode, launchers, payload lint, catalog_check, and
        # this helper. It does not discover tests. MVP-3 may be busy.
        env = os.environ.copy()
        env["TMPDIR"] = str(SCRATCH)
        # Lint only: no sockets under the run root, so a long CI checkout
        # path (actions-runner/_work/...) must not trip the 60-char guard.
        env["PREGATE_MAX_ROOT_LEN"] = "200"
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
