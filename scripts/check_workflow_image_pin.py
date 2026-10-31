#!/usr/bin/env python3
"""Fail unless every GitHub-hosted workflow job pins runs-on to ubuntu-24.04.

Walks jobs.*.runs-on as a string, a label list, or a simple matrix expression
(${{ matrix.KEY }} or ${{ matrix['KEY'] }} / double quotes). A self-hosted
label list is allowed. ubuntu-latest, any other GitHub-hosted image, an
unresolved expression, malformed YAML, a missing runs-on, and a missing
PyYAML all exit 1. A missing parser is a failure.

Recovery: pin the job to ubuntu-24.04, or install PyYAML for the interpreter
that runs this script, then re-run. Do not skip the check.

Usage:
  python3 scripts/check_workflow_image_pin.py [FILE_OR_DIR ...]
  # default directory: .github/workflows (*.yml and *.yaml, not recursive)
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

PIN = "ubuntu-24.04"
# Family prefix. re.match so "ubuntu-24.04" and "ubuntu-latest" both count,
# while "Linux" and "self-hosted" do not.
HOSTED = re.compile(r"^(ubuntu|windows|macos)(-|$)")
_MATRIX_DOT = re.compile(
    r"^\$\{\{\s*matrix\.([A-Za-z_][A-Za-z0-9_]*)\s*\}\}$"
)
_MATRIX_BRACKET = re.compile(
    r"""^\$\{\{\s*matrix\[\s*(['"])([A-Za-z_][A-Za-z0-9_]*)\1\s*\]\s*\}\}$"""
)


def matrix_key(expr: str) -> str | None:
    text = expr.strip()
    dot = _MATRIX_DOT.fullmatch(text)
    if dot:
        return dot.group(1)
    bracket = _MATRIX_BRACKET.fullmatch(text)
    if bracket:
        return bracket.group(2)
    return None


def as_label(value: object) -> str | None:
    if not isinstance(value, str) or "${{" in value:
        return None
    text = value.strip()
    return text or None


def matrix_candidates(job: dict, key: str) -> list | None:
    strategy = job.get("strategy")
    if not isinstance(strategy, dict):
        return None
    matrix = strategy.get("matrix")
    if not isinstance(matrix, dict):
        return None
    found: list = []
    saw = False
    if key in matrix:
        saw = True
        raw = matrix[key]
        if isinstance(raw, list):
            found.extend(raw)
        else:
            found.append(raw)
    include = matrix.get("include")
    if include is None:
        include = []
    elif isinstance(include, dict):
        include = [include]
    if not isinstance(include, list):
        return None
    for row in include:
        if isinstance(row, dict) and key in row:
            saw = True
            found.append(row[key])
    if not saw or not found:
        return None
    return found


def expand(job: dict, raw: object) -> tuple[list[list[str]] | None, str | None]:
    """Return every concrete label set this runs-on can select."""
    if isinstance(raw, str):
        if "${{" in raw:
            key = matrix_key(raw)
            if key is None:
                return None, "unresolved runs-on expression"
            values = matrix_candidates(job, key)
            if not values:
                return None, "matrix expression resolved to nothing"
            sets: list[list[str]] = []
            for value in values:
                if isinstance(value, list):
                    labels: list[str] = []
                    for item in value:
                        label = as_label(item)
                        if label is None:
                            return None, "unresolved matrix value"
                        labels.append(label)
                    if not labels:
                        return None, "matrix expression resolved to nothing"
                    sets.append(labels)
                else:
                    label = as_label(value)
                    if label is None:
                        return None, "unresolved matrix value"
                    sets.append([label])
            return sets, None
        label = as_label(raw)
        if label is None:
            return None, "runs-on is empty"
        return [[label]], None

    if isinstance(raw, list):
        parts: list[list[str]] = []
        for item in raw:
            if isinstance(item, str) and "${{" in item:
                key = matrix_key(item)
                if key is None:
                    return None, "unresolved runs-on expression"
                values = matrix_candidates(job, key)
                if not values:
                    return None, "matrix expression resolved to nothing"
                opts: list[str] = []
                for value in values:
                    label = as_label(value)
                    if label is None:
                        return None, "unresolved matrix value"
                    opts.append(label)
                parts.append(opts)
            else:
                label = as_label(item) if isinstance(item, str) else None
                if label is None:
                    return None, "runs-on label is not a string"
                parts.append([label])
        sets = [[]]
        for opts in parts:
            sets = [prev + [opt] for prev in sets for opt in opts]
        if not sets or any(not one for one in sets):
            return None, "runs-on is empty"
        return sets, None

    return None, "runs-on is not a string or a list"


def label_set_problem(labels: list[str]) -> str | None:
    if not labels:
        return "runs-on is empty"
    hosted = [label for label in labels if HOSTED.match(label)]
    if hosted:
        if labels == [PIN]:
            return None
        shown = ", ".join(hosted)
        return f"unpinned GitHub-hosted runs-on ({shown}); pin {PIN}"
    if any(label.lower() == "self-hosted" for label in labels):
        return None
    shown = ", ".join(labels)
    return f"runs-on is not {PIN} and is not self-hosted ({shown})"


def check_runs_on(rel: str, name: str, job: dict, raw: object) -> list[str]:
    sets, err = expand(job, raw)
    if err:
        return [f"FAIL: {rel}: job {name}: {err}"]
    out: list[str] = []
    assert sets is not None
    for labels in sets:
        reason = label_set_problem(labels)
        if reason:
            out.append(f"FAIL: {rel}: job {name}: {reason}")
    return out


def check_document(path: Path, data: object) -> list[str]:
    rel = str(path)
    if not isinstance(data, dict):
        return [f"FAIL: {rel}: workflow root is not a mapping"]
    jobs = data.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        return [f"FAIL: {rel}: no jobs mapping"]
    out: list[str] = []
    for name, job in jobs.items():
        job_name = str(name)
        if not isinstance(job, dict):
            out.append(f"FAIL: {rel}: job {job_name} is not a mapping")
            continue
        if "runs-on" not in job:
            # A reusable-workflow call has no runner of its own.
            if "uses" in job:
                continue
            out.append(f"FAIL: {rel}: job {job_name} has no runs-on")
            continue
        out.extend(check_runs_on(rel, job_name, job, job.get("runs-on")))
    return out


def check_file(yaml_mod, path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"FAIL: cannot read {path}: {exc}"]
    try:
        data = yaml_mod.safe_load(text)
    except yaml_mod.YAMLError as exc:
        err = " ".join(str(exc).split())
        return [f"FAIL: malformed YAML in {path}: {err}"]
    return check_document(path, data)


def collect(args: list[str]) -> list[Path]:
    targets = args or [".github/workflows"]
    found: list[Path] = []
    for target in targets:
        path = Path(target)
        if path.is_dir():
            found.extend(path.glob("*.yml"))
            found.extend(path.glob("*.yaml"))
        elif path.is_file():
            found.append(path)
        else:
            raise FileNotFoundError(f"workflow path not found: {target}")
    return sorted(set(found))


def main(argv: list[str]) -> int:
    try:
        import yaml
    except ImportError:
        print(
            "FAIL: PyYAML is not importable; refusing to skip the workflow image pin check"
        )
        return 1
    try:
        files = collect(argv[1:])
    except FileNotFoundError as exc:
        print(f"FAIL: {exc}")
        return 1
    if not files:
        print("FAIL: no workflow files to check")
        return 1
    failures: list[str] = []
    for path in files:
        failures.extend(check_file(yaml, path))
    if failures:
        print("\n".join(failures))
        return 1
    print(f"PASS workflow image pin: {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
