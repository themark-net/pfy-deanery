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


def in_place_root_limit() -> int:
    """Longer of the two paths pregate measures for --in-place.

    Scratch is <git common parent>/tmp/pgs/<7 sha chars>-<6 clock chars>.
    The clock digits do not change the length.
    """
    common = subprocess.check_output(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=ROOT,
        text=True,
    ).strip()
    main_root = str(Path(common).parent)
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    scratch = f"{main_root}/tmp/pgs/{sha[:7]}-000000"
    return max(len(str(ROOT)), len(scratch))


def run_pregate_lint(limit: int, timeout: int) -> subprocess.CompletedProcess[str]:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMPDIR"] = str(SCRATCH)
    env["PREGATE_MAX_ROOT_LEN"] = str(limit)
    return subprocess.run(
        ["nice", "-n", "19", "scripts/pregate.sh", "--in-place", "--allow-dirty", "--base", "HEAD", "--only", "lint"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
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
    def test_echo_of_apt_install_does_not_count_as_install(self) -> None:
        """Fail: echo apt-get install ripgrep plus a real rg --version passes.

        Recovery: the helper still says the workflow does not install ripgrep.
        A real apt-get install line is unchanged.
        """
        path = self._structural(
            "      - run: |\n"
            "          echo apt-get install -y ripgrep\n"
            "          rg --version\n"
        )
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
    def test_echo_of_rg_version_does_not_count_as_running_rg(self) -> None:
        """Fail: a real apt install plus echo rg --version passes the check.

        Recovery: the helper says ripgrep was installed but rg was not run.
        A real rg --version line still passes.
        """
        for spoken in ("echo rg --version", "sudo echo rg --version", "printf rg --version"):
            path = self._structural(
                "      - run: |\n"
                "          sudo apt-get install -y -qq ripgrep\n"
                "          %s\n" % spoken
            )
            try:
                self.assert_fail(run_helper(str(path)), "does not run rg")
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
                    "--base",
                    "HEAD",
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
        # Fail: pregate execs python3 by name and a venv symlink resolves to
        # a base interpreter that still imports PyYAML.
        # Recover: command -v python3, then exec that path on pin_root.
        self.assertIn('pin_py="$(command -v python3 || true)"', live)
        self.assertIn('"$pin_py" scripts/check_workflow_image_pin.py "$pin_root"', live)
        self.assertIn("PREGATE_IMAGE_PIN_ROOT", live)
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

    @needs_yaml
    def test_failing_image_pin_lint_fails_pregate(self) -> None:
        """A ubuntu-latest fixture must make --only lint print OVERALL=FAIL.

        PREGATE_IMAGE_PIN_ROOT points at a scratch copy of the fixture. The
        real workflow files are not edited. If the hook is ignored, the real
        workflows pass and OVERALL=PASS makes this test red.
        """
        SCRATCH.mkdir(parents=True, exist_ok=True)
        fixture = Path(tempfile.mkdtemp(prefix="image-pin-fail-lint-", dir=SCRATCH))
        try:
            shutil.copy(FIX / "latest.yml", fixture / "latest.yml")
            env = os.environ.copy()
            env["TMPDIR"] = str(SCRATCH)
            env["PREGATE_MAX_ROOT_LEN"] = "200"
            env["PREGATE_IMAGE_PIN_ROOT"] = str(fixture)
            proc = subprocess.run(
                [
                    "nice",
                    "-n",
                    "19",
                    "scripts/pregate.sh",
                    "--in-place",
                    "--allow-dirty",
                    "--base",
                    "HEAD",
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
            self.assertNotEqual(proc.returncode, 0, blob)
            self.assertIn("OVERALL=FAIL", proc.stdout)
            self.assertNotIn("OVERALL=PASS", proc.stdout)
            match = re.search(r"Summary: (\S+)", proc.stdout)
            self.assertIsNotNone(match, blob)
            log = Path(match.group(1)).parent / "logs" / "lint.log"
            text = log.read_text(encoding="utf-8")
            self.assertIn("unpinned GitHub-hosted runs-on (ubuntu-latest)", text)
            self.assertNotIn("PASS workflow image pin:", text)
        finally:
            shutil.rmtree(fixture)

    def test_root_path_over_the_limit_is_refused(self) -> None:
        # B2 guard: a run root or scratch path longer than PREGATE_MAX_ROOT_LEN
        # is a setup error, before any check. Changing `>` to `>=` is the
        # at-limit test. Removing the check lets this call reach OVERALL=.
        limit = in_place_root_limit() - 1
        self.assertGreaterEqual(limit, 1)
        proc = run_pregate_lint(limit, 60)
        blob = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 2, blob)
        self.assertNotIn("OVERALL=", proc.stdout)
        match = re.search(
            r"path too long \((\d+) > (\d+) chars\): (.+?)\. Use a checkout",
            proc.stderr,
        )
        self.assertIsNotNone(match, proc.stderr)
        got_len = int(match.group(1))
        shown_limit = int(match.group(2))
        path = match.group(3)
        self.assertEqual(shown_limit, limit)
        self.assertEqual(got_len, len(path))
        self.assertGreater(got_len, shown_limit)
        self.assertIn("PREGATE_MAX_ROOT_LEN", proc.stderr)

    @needs_yaml
    def test_root_path_at_the_limit_passes_the_guard(self) -> None:
        # Equality is allowed. The guard uses `>`, so a path of exactly the
        # limit must reach the lint and pass. A `>=` comparison exits 2 here.
        limit = in_place_root_limit()
        proc = run_pregate_lint(limit, 240)
        blob = proc.stdout + proc.stderr
        self.assertNotIn("path too long", blob)
        self.assertEqual(proc.returncode, 0, blob)
        self.assertIn("OVERALL=PASS", proc.stdout)
        match = re.search(r"Summary: (\S+)", proc.stdout)
        self.assertIsNotNone(match, blob)
        log = Path(match.group(1)).parent / "logs" / "lint.log"
        text = log.read_text(encoding="utf-8")
        self.assertIn("PASS workflow image pin:", text)


if __name__ == "__main__":
    unittest.main()
