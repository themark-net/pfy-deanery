#!/usr/bin/env python3
"""G0 must collect every tests/test_*.py on ubuntu-24.04 and on nimo.

How this fails: the suite job drops unittest, narrows -s or -p, or switches
to an explicit module list and leaves a file out. A new tests/test_*.py would
then never run on that job. The ubuntu image-pin tests also skip if discover
runs before PyYAML is installed for that interpreter.

How we recover: put `python3 -m unittest discover -s tests -t .` back on the
job, or add the missing module to the explicit list, and install PyYAML on
the ubuntu job before that step. Leave runs-on pinned to ubuntu-24.04.
bwrap confinement tests may still skip inside the module. This file does not
change pregate.

The filemode job is also named G0. It is not a suite job. Only
`G0 (ubuntu-24.04)` / `structural-github` and `G0 (self-hosted nimo)` /
`structural-local` have to collect the modules.
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


def ubuntu_yaml_gap(job: dict) -> str | None:
    """None when PyYAML is installed before the first unittest invocation."""
    installed = False
    saw_unittest = False
    for script in step_scripts(job):
        for line in script.splitlines():
            has_unittest = False
            if "unittest" in line:
                try:
                    has_unittest = any(specs_from_tokens(tokens) for tokens in iter_commands(line))
                except ValueError:
                    has_unittest = False
            if has_unittest and not installed:
                return "unittest runs before PyYAML is installed on the ubuntu G0 job"
            if has_unittest:
                saw_unittest = True
            if re.search(r"pip(?:3)?\s+install\b", line, re.I) and re.search(r"pyyaml", line, re.I):
                installed = True
    if not saw_unittest:
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
        require_yaml(self)
        modules = repo_test_modules()
        self.assertGreaterEqual(len(modules), 70, modules)
        for rel in REVIEW:
            self.assertIn(rel, modules)
        docs = workflow_docs()
        jobs = suite_jobs(docs)
        self.assertEqual(len(jobs["ubuntu"]), 1, "expected one ubuntu suite job")
        self.assertEqual(len(jobs["nimo"]), 1, "expected one nimo suite job")
        missed = outside(docs, modules)
        self.assertEqual(missed["ubuntu"], [], missed)
        self.assertEqual(missed["nimo"], [], missed)
        gap = ubuntu_yaml_gap(jobs["ubuntu"][0])
        self.assertIsNone(gap, gap)

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
