#!/usr/bin/env python3
"""Landing G0 selects tests. The nightly job still runs every tests/test_*.py.

How this fails: a landing job drops the selector or the runner, the named
unittest skip disappears, or the nightly backstop passes a module list and
leaves a new tests/test_*.py out. The ubuntu image-pin tests also skip if
the suite runner starts before PyYAML is installed for that interpreter.

How we recover: keep scripts/test_select.py, scripts/run_tests.py, and
--skip-unittests on both G0 jobs. Keep `python3 scripts/run_tests.py` with
no module arguments on the nightly workflow (that job is not named G0).
Install PyYAML on the ubuntu job before that step. Leave runs-on pinned to
ubuntu-24.04. Fixture checks below still fail when a discover or an explicit
list would miss a module. bwrap confinement tests may still skip inside a
module.

The filemode job is also named G0. It is not a suite job. Only
`G0 (ubuntu-24.04)` / `structural-github` and `G0 (self-hosted nimo)` /
`structural-local` are the landing suite jobs.
"""

from __future__ import annotations

import fnmatch
import re
import shlex
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
REVIEW = (
    "tests/test_pfy_build_local_review.py",
    "tests/test_pfy_build_local_review_ci.py",
)

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


def require_yaml(case: unittest.TestCase) -> None:
    if yaml is None:
        case.fail(
            "PyYAML is not importable in %s. Recovery: pip install pyyaml "
            "for that interpreter. The ubuntu G0 job installs it before discover."
            % sys.executable
        )


def norm_dir(text: str) -> str:
    value = text.strip()
    if value in ("", "."):
        return "."
    if value.startswith("./"):
        value = value[2:]
    return value.rstrip("/")


def module_to_rel(token: str) -> str | None:
    parts = token.split(".")
    if not parts or parts[0] != "tests":
        return None
    acc: list[str] = []
    for part in parts:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", part):
            break
        acc.append(part)
        # The package directory is named tests, and fnmatch("tests", "test*")
        # is true. Stop only on the module component after that package.
        if fnmatch.fnmatch(part, "test*") and part != "tests":
            return "/".join(acc) + ".py"
    return None


def _option(args: list[str], index: int) -> tuple[str, str, int] | None:
    token = args[index]
    pairs = (
        ("-s", "--start-directory", "start"),
        ("-p", "--pattern", "pattern"),
        ("-t", "--top-level-directory", "top"),
    )
    for short, long, kind in pairs:
        if token == short or token == long:
            if index + 1 >= len(args):
                return None
            return kind, args[index + 1], 2
        if token.startswith(long + "="):
            return kind, token.split("=", 1)[1], 1
    return None


def discover_spec(args: list[str]) -> tuple[str, str, str]:
    start = "."
    pattern = "test*.py"
    index = 0
    while index < len(args):
        found = _option(args, index)
        if found is None:
            index += 1
            continue
        kind, value, used = found
        if kind == "start":
            start = norm_dir(value)
        elif kind == "pattern":
            pattern = value
        index += used
    return ("discover", start, pattern)


def specs_from_tokens(tokens: list[str]) -> list[tuple]:
    args: list[str] | None = None
    for index, token in enumerate(tokens):
        if token == "-m" and index + 1 < len(tokens) and tokens[index + 1] == "unittest":
            args = tokens[index + 2 :]
            break
    if not args:
        return []
    if args[0] == "discover":
        return [discover_spec(args[1:])]
    skip_with_value = {"-k", "-s", "-p", "-t"}
    modules: list[str] = []
    index = 0
    while index < len(args):
        token = args[index]
        if token in skip_with_value or token in ("--start-directory", "--pattern", "--top-level-directory"):
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        rel = module_to_rel(token)
        if rel:
            modules.append(rel)
        index += 1
    if not modules:
        return []
    return [("explicit", frozenset(modules))]


_ENV_PREFIX = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*=(?:\"[^\"]*\"|'[^']*'|\S+)\s+"
)


def iter_commands(script: str):
    for raw in script.splitlines():
        text = raw.strip()
        if not text or text.startswith("#"):
            continue
        while True:
            match = _ENV_PREFIX.match(text)
            if not match:
                break
            text = text[match.end() :]
        if "unittest" not in text:
            continue
        try:
            tokens = shlex.split(text, posix=True)
        except ValueError:
            continue
        yield tokens


def step_scripts(job: dict) -> list[str]:
    steps = job.get("steps")
    if not isinstance(steps, list):
        return []
    scripts: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        flag = step.get("if")
        if flag is False or flag == "false":
            continue
        run = step.get("run")
        if isinstance(run, str):
            scripts.append(run)
    return scripts


def job_specs(job: dict) -> list[tuple]:
    specs: list[tuple] = []
    for script in step_scripts(job):
        for tokens in iter_commands(script):
            specs.extend(specs_from_tokens(tokens))
    return specs


def spec_covers(spec: tuple, rel: str) -> bool:
    if spec[0] == "explicit":
        return rel in spec[1]
    _kind, start, pattern = spec
    name = PurePosixPath_name(rel)
    if not fnmatch.fnmatch(name, pattern):
        return False
    if start == ".":
        return True
    path = rel[2:] if rel.startswith("./") else rel
    return path == start or path.startswith(start + "/")


def PurePosixPath_name(rel: str) -> str:
    return rel.rstrip("/").rsplit("/", 1)[-1]


def job_kind(job_id: str, job: dict) -> str | None:
    runs = job.get("runs-on")
    name = job.get("name") if isinstance(job.get("name"), str) else ""
    ubuntu = runs == "ubuntu-24.04" or runs == ["ubuntu-24.04"]
    if ubuntu and (name == "G0 (ubuntu-24.04)" or job_id == "structural-github"):
        return "ubuntu"
    if (
        isinstance(runs, list)
        and "self-hosted" in runs
        and "pfy-mentat" in runs
        and (name == "G0 (self-hosted nimo)" or job_id == "structural-local")
    ):
        return "nimo"
    return None


def suite_jobs(docs: list[dict]) -> dict[str, list[dict]]:
    found: dict[str, list[dict]] = {"ubuntu": [], "nimo": []}
    for doc in docs:
        if not isinstance(doc, dict):
            continue
        jobs = doc.get("jobs")
        if not isinstance(jobs, dict):
            continue
        for job_id, job in jobs.items():
            if not isinstance(job, dict):
                continue
            kind = job_kind(str(job_id), job)
            if kind:
                found[kind].append(job)
    return found


def outside(docs: list[dict], modules: list[str]) -> dict[str, list[str]]:
    """Modules a suite job would not collect. An absent job misses all of them."""
    jobs = suite_jobs(docs)
    missed: dict[str, list[str]] = {}
    for kind in ("ubuntu", "nimo"):
        group = jobs[kind]
        if not group:
            missed[kind] = list(modules)
            continue
        missing: list[str] = []
        for rel in modules:
            if not all(any(spec_covers(spec, rel) for spec in job_specs(job)) for job in group):
                missing.append(rel)
        missed[kind] = missing
    return missed


def _line_is_suite(line: str) -> bool:
    """A real unittest invocation or scripts/run_tests.py. Comments do not count."""
    code = line.split("#", 1)[0]
    if not code.strip():
        return False
    if "unittest" in code:
        try:
            if any(specs_from_tokens(tokens) for tokens in iter_commands(code)):
                return True
        except ValueError:
            return False
    if "scripts/run_tests.py" not in code:
        return False
    try:
        tokens = shlex.split(code.strip(), posix=True)
    except ValueError:
        return False
    return any(token == "scripts/run_tests.py" or token.endswith("/run_tests.py") for token in tokens)


def ubuntu_yaml_gap(job: dict) -> str | None:
    """None when PyYAML is installed before the first suite invocation.

    scripts/run_tests.py counts as that invocation, same as unittest discover.
    """
    installed = False
    saw_suite = False
    for script in step_scripts(job):
        for line in script.splitlines():
            if _line_is_suite(line) and not installed:
                return "suite runs before PyYAML is installed on the ubuntu G0 job"
            if _line_is_suite(line):
                saw_suite = True
            if re.search(r"pip(?:3)?\s+install\b", line, re.I) and re.search(r"pyyaml", line, re.I):
                installed = True
    if not saw_suite:
        return "ubuntu G0 job has no unittest discover or module list"
    if not installed:
        return "ubuntu G0 job never installs PyYAML"
    return None


def load_text(text: str) -> dict:
    loaded = yaml.safe_load(text)
    if not isinstance(loaded, dict):
        raise ValueError("workflow YAML is not a mapping")
    return loaded


def repo_test_modules() -> list[str]:
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tests").rglob("test_*.py")
    )


def workflow_docs() -> list[dict]:
    docs: list[dict] = []
    for path in sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml")):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            docs.append(loaded)
    return docs


_EXPLICIT = """\
name: eval-structural
jobs:
  structural-github:
    name: G0 (ubuntu-24.04)
    runs-on: ubuntu-24.04
    steps:
      - name: listed
        run: python3 -m unittest tests.test_kept
  structural-local:
    name: G0 (self-hosted nimo)
    runs-on: [self-hosted, Linux, X64, pfy-mentat]
    steps:
      - name: all
        run: PFY_STATE_DIR="$RUNNER_TEMP/pfy-state" python3 -m unittest discover -s tests -t .
"""

_DISCOVER = """\
name: eval-structural
jobs:
  structural-github:
    name: G0 (ubuntu-24.04)
    runs-on: ubuntu-24.04
    steps:
      - name: Install PyYAML for the workflow image pin
        run: python3 -m pip install --disable-pip-version-check -q pyyaml
      - name: all
        run: python3 -m unittest discover -s tests -t .
  structural-local:
    name: G0 (self-hosted nimo)
    runs-on: [self-hosted, Linux, X64, pfy-mentat]
    steps:
      - name: all
        run: PFY_STATE_DIR="$RUNNER_TEMP/pfy-state" python3 -m unittest discover -s tests -t .
"""

_NARROW = """\
name: eval-structural
jobs:
  structural-github:
    name: G0 (ubuntu-24.04)
    runs-on: ubuntu-24.04
    steps:
      - run: python3 -m unittest discover -s tests -p 'test_old*.py'
  structural-local:
    name: G0 (self-hosted nimo)
    runs-on: [self-hosted, Linux, X64, pfy-mentat]
    steps:
      - run: python3 -m unittest discover --start-directory=tests --pattern=test_old*.py
"""


AUDIT = (
    "tests.test_dogfood2_1031_report",
    "tests.test_selfhost_1031_log",
)
_TAKES_VALUE = {"-j", "--jobs", "--root", "--receipt", "--run-dir", "--shard"}


def job_text(job: dict) -> str:
    """Step scripts, plus ci_selected_tests.sh when a step invokes it."""
    parts = list(step_scripts(job))
    blob = "\n".join(parts)
    script = ROOT / "scripts" / "ci_selected_tests.sh"
    if "scripts/ci_selected_tests.sh" in blob and script.is_file():
        parts.append(script.read_text(encoding="utf-8"))
    return "\n".join(parts)


def runner_invocations(script: str) -> list[list[str]]:
    found: list[list[str]] = []
    for raw in script.splitlines():
        text = raw.split("#", 1)[0].strip()
        if "run_tests.py" not in text:
            continue
        while True:
            match = _ENV_PREFIX.match(text)
            if not match:
                break
            text = text[match.end() :]
        try:
            tokens = shlex.split(text, posix=True)
        except ValueError:
            continue
        for index, token in enumerate(tokens):
            if token == "scripts/run_tests.py" or token.endswith("/run_tests.py"):
                found.append(tokens[index + 1 :])
    return found


def invocation_is_full_suite(args: list[str]) -> bool:
    """True when the runner is given no module path. Flags may still be set."""
    index = 0
    while index < len(args):
        token = args[index]
        if token in _TAKES_VALUE:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return False
    return True


def load_default_module_files():
    import importlib.util

    path = ROOT / "scripts" / "run_tests.py"
    spec = importlib.util.spec_from_file_location("pfy_run_tests_cover", path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.default_module_files


class CiDiscoverCoverTests(unittest.TestCase):
    def test_explicit_list_misses_a_new_module_and_discover_recovers(self) -> None:
        require_yaml(self)
        modules = ["tests/test_kept.py", "tests/test_new.py"]
        missed = outside([load_text(_EXPLICIT)], modules)
        self.assertEqual(missed["ubuntu"], ["tests/test_new.py"])
        self.assertEqual(missed["nimo"], [])
        recovered = outside([load_text(_DISCOVER)], modules)
        self.assertEqual(recovered["ubuntu"], [])
        self.assertEqual(recovered["nimo"], [])

    def test_narrow_pattern_leaves_a_new_module_out_of_both_jobs(self) -> None:
        require_yaml(self)
        modules = ["tests/test_old_one.py", "tests/test_new_gap.py"]
        missed = outside([load_text(_NARROW)], modules)
        self.assertNotIn("tests/test_old_one.py", missed["ubuntu"])
        self.assertNotIn("tests/test_old_one.py", missed["nimo"])
        self.assertEqual(missed["ubuntu"], ["tests/test_new_gap.py"])
        self.assertEqual(missed["nimo"], ["tests/test_new_gap.py"])

    def test_discover_from_fixtures_dir_misses_top_level_modules(self) -> None:
        require_yaml(self)
        text = _DISCOVER.replace(
            "python3 -m unittest discover -s tests -t .",
            "python3 -m unittest discover -s tests/fixtures -t .",
        )
        missed = outside([load_text(text)], ["tests/test_new.py"])
        self.assertEqual(missed["ubuntu"], ["tests/test_new.py"])
        self.assertEqual(missed["nimo"], ["tests/test_new.py"])

    def test_filemode_g0_job_is_not_a_suite_job(self) -> None:
        require_yaml(self)
        text = """\
name: operator-launch-filemode
jobs:
  check-filemode:
    name: G0 launcher 100755
    runs-on: ubuntu-24.04
    steps:
      - run: ./pfy help
"""
        jobs = suite_jobs([load_text(text)])
        self.assertEqual(jobs["ubuntu"], [])
        self.assertEqual(jobs["nimo"], [])

    def test_real_g0_jobs_cover_every_test_module(self) -> None:
        """G0 selects. Nightly plus default_module_files is the full backstop.

        Naming the nightly job G0 (ubuntu-24.04) would make suite_jobs see two
        ubuntu suite jobs and fail this test.
        """
        require_yaml(self)
        modules = repo_test_modules()
        self.assertGreaterEqual(len(modules), 70, modules)
        for rel in REVIEW:
            self.assertIn(rel, modules)
        listed = load_default_module_files()(ROOT)
        self.assertEqual(listed, modules, "run_tests default list drifted from tests/test_*.py")
        docs = workflow_docs()
        jobs = suite_jobs(docs)
        self.assertEqual(len(jobs["ubuntu"]), 1, "expected one ubuntu suite job")
        self.assertEqual(len(jobs["nimo"]), 1, "expected one nimo suite job")
        ubuntu_blob = job_text(jobs["ubuntu"][0])
        nimo_blob = job_text(jobs["nimo"][0])
        for blob in (ubuntu_blob, nimo_blob):
            self.assertIn("scripts/test_select.py", blob)
            self.assertIn("scripts/run_tests.py", blob)
            self.assertIn("--skip-unittests", blob)
            self.assertIn("scripts/ci_selected_tests.sh", blob)
        self.assertIn("PFY_CI_USE_CACHE=0", ubuntu_blob)
        self.assertIn("PFY_CI_USE_CACHE=1", nimo_blob)
        self.assertIn("cache hit", nimo_blob)
        for name in AUDIT:
            self.assertIn(name, ubuntu_blob)
        gap = ubuntu_yaml_gap(jobs["ubuntu"][0])
        self.assertIsNone(gap, gap)

        nightly_path = WORKFLOWS / "full-suite-nightly.yml"
        self.assertTrue(nightly_path.is_file(), nightly_path)
        nightly = load_text(nightly_path.read_text(encoding="utf-8"))
        nightly_jobs = nightly.get("jobs")
        self.assertIsInstance(nightly_jobs, dict)
        self.assertNotIn("structural-github", nightly_jobs)
        backstop = None
        for job_id, job in nightly_jobs.items():
            self.assertIsInstance(job, dict)
            name = job.get("name") if isinstance(job.get("name"), str) else ""
            self.assertFalse(name.startswith("G0"), name)
            self.assertIsNone(job_kind(str(job_id), job), job_id)
            if job.get("runs-on") == "ubuntu-24.04":
                backstop = job
        self.assertIsNotNone(backstop, "nightly has no ubuntu-24.04 job")
        invocations: list[list[str]] = []
        for script in step_scripts(backstop):
            invocations.extend(runner_invocations(script))
        self.assertTrue(invocations, "nightly does not call scripts/run_tests.py")
        self.assertTrue(
            any(invocation_is_full_suite(args) for args in invocations),
            invocations,
        )
        nightly_gap = ubuntu_yaml_gap(backstop)
        self.assertIsNone(nightly_gap, nightly_gap)

    def test_run_tests_before_pyyaml_is_a_gap(self) -> None:
        require_yaml(self)
        bare = """\
name: eval-structural
jobs:
  structural-github:
    name: G0 (ubuntu-24.04)
    runs-on: ubuntu-24.04
    steps:
      - run: python3 scripts/run_tests.py
"""
        job = suite_jobs([load_text(bare)])["ubuntu"][0]
        self.assertIn("PyYAML", ubuntu_yaml_gap(job) or "")
        installed = bare.replace(
            "      - run: python3 scripts/run_tests.py\n",
            "      - run: python3 -m pip install -q pyyaml\n"
            "      - run: python3 scripts/run_tests.py\n",
        )
        restored = suite_jobs([load_text(installed)])["ubuntu"][0]
        self.assertIsNone(ubuntu_yaml_gap(restored))

    def test_ubuntu_discover_without_pyyaml_install_is_a_gap(self) -> None:
        require_yaml(self)
        bare = _DISCOVER.replace(
            "      - name: Install PyYAML for the workflow image pin\n"
            "        run: python3 -m pip install --disable-pip-version-check -q pyyaml\n",
            "",
        )
        job = suite_jobs([load_text(bare)])["ubuntu"][0]
        self.assertIn("PyYAML", ubuntu_yaml_gap(job) or "")
        restored = suite_jobs([load_text(_DISCOVER)])["ubuntu"][0]
        self.assertIsNone(ubuntu_yaml_gap(restored))


if __name__ == "__main__":
    unittest.main()
