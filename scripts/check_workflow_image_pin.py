#!/usr/bin/env python3
"""Fail unless every GitHub-hosted workflow job pins runs-on to ubuntu-24.04.

Walks jobs.*.runs-on as a string, a label list, or a simple matrix expression
(${{ matrix.KEY }} or ${{ matrix['KEY'] }} / double quotes). A self-hosted
label list is allowed. ubuntu-latest, any other GitHub-hosted image, an
unresolved expression, malformed YAML, a repeated mapping key, a missing
runs-on, and a missing PyYAML all exit 1. A missing parser is a failure.
PyYAML keeps the last copy of a repeated key; this check rejects it, so a
later ubuntu-24.04 cannot hide an earlier ubuntu-latest.

Also walks jobs.*.container (a string or an image: mapping) and
jobs.*.services.*.image. Each image needs a tag that is not latest and not
empty. If any image in this run already uses @sha256:, every image needs
an @sha256: digest of 64 hex digits. Malformed container or service forms
fail closed.

eval-structural.yml must also install the ripgrep package from a run step
and invoke rg. The word ripgrep in a comment, a step name, or an echo is
not an install. Shell comments inside the run script are ignored.

Recovery: pin the job to ubuntu-24.04, give every container and service image
a non-latest tag (and @sha256: when any image in the run already has one),
delete the repeated YAML key, or install PyYAML for the interpreter named
in the failure (sys.executable). Pregate and the hosted G0 job both invoke
that absolute PATH python3. A different python3 later on PATH is not used.
For the structural workflow, put `apt-get install` (or `apt install`) of the
ripgrep package and `rg --version` or `command -v rg` in a run step. Do not
skip the check.

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
_SHA256 = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


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


def _strip_shell_comment(line: str) -> str:
    """Drop an unquoted # comment. Quoted hashes stay."""
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
        elif ch == "\\" and in_double and i + 1 < len(line):
            out.append(ch)
            out.append(line[i + 1])
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _run_code(data: object) -> str:
    if not isinstance(data, dict):
        return ""
    jobs = data.get("jobs")
    if not isinstance(jobs, dict):
        return ""
    lines: list[str] = []
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        for step in steps:
            if not isinstance(step, dict):
                continue
            run = step.get("run")
            if not isinstance(run, str):
                continue
            for line in run.splitlines():
                lines.append(_strip_shell_comment(line))
    return "\n".join(lines)


def _command_is_echo(tokens: list[str]) -> bool:
    """True when the line only prints the words. sudo echo counts too."""
    if not tokens:
        return False
    head = tokens[0]
    if head in ("echo", "printf"):
        return True
    return head == "sudo" and len(tokens) > 1 and tokens[1] in ("echo", "printf")


def _installs_ripgrep(code: str) -> bool:
    for line in code.splitlines():
        tokens = line.split()
        # Fail: `echo apt-get install ripgrep` counted as an install.
        # Recover: ignore an echo or printf line. A real apt-get line still counts.
        if _command_is_echo(tokens):
            continue
        if "apt-get" not in tokens and "apt" not in tokens:
            continue
        if "install" not in tokens:
            continue
        if "ripgrep" in tokens:
            return True
    return False


def _runs_rg(code: str) -> bool:
    for line in code.splitlines():
        tokens = line.split()
        # Fail: `echo rg --version` counted as running rg.
        # Recover: ignore an echo or printf line. A real rg or command -v rg still counts.
        if _command_is_echo(tokens):
            continue
        if "rg" in tokens and "--version" in tokens:
            return True
        for index, token in enumerate(tokens):
            if token == "command" and tokens[index : index + 3] == ["command", "-v", "rg"]:
                return True
    return False


def ripgrep_step_errors(path: Path, data: object) -> list[str]:
    """eval-structural.yml must install ripgrep and then invoke rg.

    Other workflow filenames are not asked to install ripgrep.
    """
    if path.name != "eval-structural.yml":
        return []
    rel = str(path)
    code = _run_code(data)
    if not _installs_ripgrep(code):
        return [f"FAIL: {rel}: does not install ripgrep"]
    if not _runs_rg(code):
        return [f"FAIL: {rel}: installs ripgrep but does not run rg"]
    return []


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
    out.extend(ripgrep_step_errors(path, data))
    return out


def image_problem(ref: str, require_digest: bool) -> str | None:
    """Return a reason this image ref is not pinned, or None when it is.

    A tag is the part after the last colon that sits after the last slash,
    so a registry port (localhost:5000/app:1) is not the tag. latest and a
    missing tag fail. A digest, when present, must be @sha256: and 64 hex.
    """
    text = ref.strip()
    if not text:
        return "image is empty"
    if "${{" in text:
        return "unresolved image expression"
    digest = None
    body = text
    if "@" in text:
        body, digest = text.rsplit("@", 1)
        if not _SHA256.fullmatch(digest):
            return "image digest is not @sha256: and 64 hex"
    slash = body.rfind("/")
    colon = body.rfind(":")
    if colon > slash:
        name = body[:colon]
        tag = body[colon + 1 :]
    else:
        name = body
        tag = ""
    if not name or name.endswith("/"):
        return "image name is empty"
    if tag == "":
        return "image has no tag"
    if tag.lower() == "latest":
        return "image tag is latest"
    if require_digest and digest is None:
        return "image is missing @sha256: digest"
    return None


def _take_image(label: str, image: object) -> tuple[list[str], list[tuple[str, str]]]:
    if not isinstance(image, str):
        return [f"FAIL: {label}: image is not a string"], []
    return [], [(label, image)]


def collect_images(path: Path, data: object) -> tuple[list[str], list[tuple[str, str]]]:
    """Structural problems, plus (location, ref) for every image string.

    A missing container or services key is fine. A present key in a shape
    GitHub will not run fails closed instead of being skipped.
    """
    if not isinstance(data, dict):
        return [], []
    jobs = data.get("jobs")
    if not isinstance(jobs, dict):
        return [], []
    fails: list[str] = []
    refs: list[tuple[str, str]] = []
    rel = str(path)
    for name, job in jobs.items():
        if not isinstance(job, dict):
            continue
        where = f"{rel}: job {name}"
        if "container" in job:
            label = where + " container"
            raw = job.get("container")
            if isinstance(raw, str):
                refs.append((label, raw))
            elif isinstance(raw, dict):
                if "image" not in raw:
                    fails.append(f"FAIL: {label}: container has no image")
                else:
                    more, found = _take_image(label, raw.get("image"))
                    fails.extend(more)
                    refs.extend(found)
            else:
                fails.append(f"FAIL: {label}: container is not a string or a mapping")
        if "services" not in job:
            continue
        services = job.get("services")
        if not isinstance(services, dict):
            fails.append(f"FAIL: {where} services: services is not a mapping")
            continue
        if not services:
            fails.append(f"FAIL: {where} services: services is empty")
            continue
        for svc_name, spec in services.items():
            label = f"{where} service {svc_name}"
            if not isinstance(spec, dict):
                fails.append(f"FAIL: {label}: service is not a mapping")
                continue
            if "image" not in spec:
                fails.append(f"FAIL: {label}: service has no image")
                continue
            more, found = _take_image(label, spec.get("image"))
            fails.extend(more)
            refs.extend(found)
    return fails, refs


def load_workflow(yaml_mod, text: str):
    """Load workflow YAML and reject a repeated mapping key.

    The default loader keeps the last value. A job could then hide
    ubuntu-latest under a later ubuntu-24.04 and look pinned.
    """

    class UniqueKeyLoader(yaml_mod.SafeLoader):
        pass

    def construct_mapping(loader, node, deep=False):
        seen: list[str] = []
        for key_node, _value_node in node.value:
            if not isinstance(key_node, yaml_mod.ScalarNode):
                continue
            if key_node.value in seen:
                raise yaml_mod.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key_node.value!r}",
                    key_node.start_mark,
                )
            seen.append(key_node.value)
        return yaml_mod.constructor.SafeConstructor.construct_mapping(loader, node, deep)

    UniqueKeyLoader.add_constructor(
        yaml_mod.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping,
    )
    return yaml_mod.load(text, Loader=UniqueKeyLoader)


def check_file(yaml_mod, path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"FAIL: cannot read {path}: {exc}"], []
    try:
        data = load_workflow(yaml_mod, text)
    except yaml_mod.YAMLError as exc:
        err = " ".join(str(exc).split())
        return [f"FAIL: malformed YAML in {path}: {err}"], []
    fails = check_document(path, data)
    image_fails, refs = collect_images(path, data)
    return fails + image_fails, refs


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
        exe = sys.executable or sys.argv[0]
        print(
            "FAIL: PyYAML is not importable in %s; refusing to skip the workflow image pin check"
            % exe
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
    refs: list[tuple[str, str]] = []
    for path in files:
        file_fails, file_refs = check_file(yaml, path)
        failures.extend(file_fails)
        refs.extend(file_refs)
    # One pinned digest in the set means every image in the set must pin one.
    # A short or non-sha256 digest still counts as "pins digests" when it
    # contains the @sha256: marker, and that ref fails its own format check.
    require_digest = any("@sha256:" in ref for _where, ref in refs)
    for where, ref in refs:
        reason = image_problem(ref, require_digest)
        if reason:
            failures.append(f"FAIL: {where}: {reason}")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"PASS workflow image pin: {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
