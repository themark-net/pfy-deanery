"""Per-tool integration stage cards.

One file per tool under ``data/stages/<slug>.json``. Shared fields live in
``data/stages/_registry.json``. ``data/tool_integration_stages.json`` is the
retired monolith: ``validate_stage_files`` rejects it.

``load_stages`` returns the old document shape. ``last_updated`` is not stored
(that line conflicted on every parallel edit). It is filled from the latest
per-tool ``last_updated`` or date field, otherwise the git commit date of
``data/stages`` (or of the retired monolith path when the split is not
committed yet).

Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

VALID_STAGES = ("I0", "I1", "I2", "I3", "I4")
REGISTRY_NAME = "_registry.json"
LEGACY_REL = "data/tool_integration_stages.json"
STAGES_REL = Path("data") / "stages"
REGISTRY_KEYS = ("version", "policy", "default_stage", "probe_path", "coverage", "handoff")
ASSEMBLED_KEYS = (
    "version",
    "last_updated",
    "policy",
    "default_stage",
    "tools",
    "probe_path",
    "coverage",
    "handoff",
)
MONOLITH_MESSAGE = (
    "data/tool_integration_stages.json must not exist; "
    "stage cards live in data/stages/<slug>.json, one file per tool. "
    "Remove the monolith."
)
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_DATE_KEYS = {"last_updated", "updated", "date"}


class StageSlugError(ValueError):
    """Two tool names share one slug. The message names both tools."""


def slug_for(name: str) -> str:
    """Lowercase, turn each run of non-alphanumeric characters into one dash."""
    return _SLUG_RE.sub("-", str(name).lower()).strip("-")


def dumps(obj: object) -> str:
    """Stable JSON: indent 2, original key order, trailing newline."""
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def stages_dir(root: str | os.PathLike) -> Path:
    return Path(root) / STAGES_REL


def registry_path(root: str | os.PathLike) -> Path:
    return stages_dir(root) / REGISTRY_NAME


def legacy_path(root: str | os.PathLike) -> Path:
    return Path(root) / LEGACY_REL


def _rel(path: Path) -> str:
    return f"data/stages/{path.name}"


def _is_date_field(key: str) -> bool:
    lk = key.lower()
    return lk in _DATE_KEYS or lk.endswith("_date") or lk.endswith("-date")


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def _tool_paths(root: str | os.PathLike) -> list[Path]:
    directory = stages_dir(root)
    if not directory.is_dir():
        return []
    return sorted(
        p for p in directory.glob("*.json") if p.is_file() and p.name != REGISTRY_NAME
    )


def _parse_tool_file(path: Path) -> tuple[str | None, dict | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, None, f"{_rel(path)}: invalid JSON ({exc.msg})"
    if not isinstance(data, dict):
        return None, None, f"{_rel(path)}: top level is not an object"
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        return None, None, f"{_rel(path)}: missing name"
    obj = {key: value for key, value in data.items() if key != "name"}
    return name, obj, None


def _collision_message(slug: str, left: str, right: str) -> str:
    return f"slug {slug!r} collides: {left!r} and {right!r}"


def _read_registry(root: str | os.PathLike) -> dict:
    path = registry_path(root)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{_rel(path)}: top level is not an object")
    return {key: value for key, value in data.items() if key != "last_updated"}


def _git_commit_date(root: Path) -> str | None:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    for rel in ("data/stages", LEGACY_REL):
        try:
            proc = subprocess.run(
                ["git", "-C", str(root), "log", "-1", "--format=%cs", "--", rel],
                capture_output=True,
                text=True,
                timeout=15,
                env=env,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            continue
        line = (proc.stdout or "").strip()
        if line:
            return line.splitlines()[0].strip()
    return None


def _tool_stamp(tools: dict) -> str | None:
    found: list[str] = []
    for obj in tools.values():
        if not isinstance(obj, dict):
            continue
        for key, value in obj.items():
            if _is_date_field(key) and isinstance(value, str) and value.strip():
                found.append(value.strip())
    if not found:
        return None
    return max(found)


def _assemble(registry: dict, tools: dict, stamp: str | None) -> dict:
    out: dict = {}
    for key in ASSEMBLED_KEYS:
        if key == "last_updated":
            if stamp is not None:
                out[key] = stamp
            continue
        if key == "tools":
            out[key] = tools
            continue
        if key in registry:
            out[key] = registry[key]
    for key, value in registry.items():
        if key not in out and key != "tools":
            out[key] = value
    return out


def load_stages(root: str | os.PathLike) -> dict:
    """Old monolith shape: registry fields, computed last_updated, tools by name."""
    root_path = Path(root)
    directory = stages_dir(root_path)
    if not directory.is_dir():
        raise FileNotFoundError(f"data/stages is missing under {root_path}")
    registry = _read_registry(root_path)
    tools: dict[str, dict] = {}
    by_slug: dict[str, str] = {}
    for path in _tool_paths(root_path):
        name, obj, err = _parse_tool_file(path)
        if err:
            raise ValueError(err)
        assert name is not None and obj is not None
        slug = slug_for(name)
        prior = by_slug.get(slug)
        if prior is not None and prior != name:
            raise StageSlugError(_collision_message(slug, prior, name))
        if name in tools:
            raise StageSlugError(f"duplicate tool name {name!r}")
        by_slug[slug] = name
        tools[name] = obj
    ordered = {name: tools[name] for name in sorted(tools)}
    stamp = _tool_stamp(ordered)
    if stamp is None:
        stamp = _git_commit_date(root_path.resolve())
    return _assemble(registry, ordered, stamp)


def _registry_payload(meta: dict) -> dict:
    out: dict = {}
    for key in REGISTRY_KEYS:
        if key in meta and key != "last_updated":
            out[key] = meta[key]
    for key, value in meta.items():
        if key in out or key in ("tools", "last_updated"):
            continue
        out[key] = value
    return out


def write_registry(root: str | os.PathLike, meta: dict) -> Path:
    """Write shared fields. ``last_updated`` is dropped on purpose."""
    path = registry_path(root)
    text = dumps(_registry_payload(meta))
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return path
    _atomic_write(path, text)
    return path


def _tool_document(name: str, obj: dict) -> dict:
    body = {"name": name}
    for key, value in obj.items():
        if key == "name":
            continue
        body[key] = value
    return body


def write_tool(root: str | os.PathLike, name: str, obj: dict) -> Path:
    """Write one tool file. A slug shared with a different tool is an error."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("tool name is empty")
    if not isinstance(obj, dict):
        raise TypeError("tool card must be an object")
    slug = slug_for(name)
    if slug in ("", "_registry"):
        raise StageSlugError(f"tool name {name!r} has an unusable slug {slug!r}")
    directory = stages_dir(root)
    dest = directory / f"{slug}.json"
    for path in _tool_paths(root):
        other_name, _, err = _parse_tool_file(path)
        if err:
            if path == dest:
                raise ValueError(err)
            continue
        if other_name is None:
            continue
        if path == dest and other_name == name:
            continue
        other_slug = slug_for(other_name)
        if other_slug == slug or other_name == name:
            raise StageSlugError(_collision_message(slug, other_name, name))
    text = dumps(_tool_document(name, obj))
    if dest.is_file() and dest.read_text(encoding="utf-8") == text:
        return dest
    _atomic_write(dest, text)
    return dest


def validate_stage_files(root: str | os.PathLike) -> list[str]:
    """Problems for catalog_check. Empty means the split tree is usable."""
    root_path = Path(root)
    problems: list[str] = []
    if legacy_path(root_path).exists():
        problems.append(MONOLITH_MESSAGE)
    directory = stages_dir(root_path)
    if not directory.is_dir():
        problems.append(f"data/stages is missing under {root_path}")
        return problems
    reg = registry_path(root_path)
    if not reg.is_file():
        problems.append("data/stages/_registry.json is missing")
    else:
        try:
            payload = json.loads(reg.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            problems.append(f"data/stages/_registry.json: invalid JSON ({exc.msg})")
        else:
            if not isinstance(payload, dict):
                problems.append("data/stages/_registry.json: top level is not an object")
    by_slug: dict[str, str] = {}
    seen_names: dict[str, str] = {}
    for path in _tool_paths(root_path):
        name, obj, err = _parse_tool_file(path)
        if err or name is None or obj is None:
            problems.append(err or f"{_rel(path)}: unreadable")
            continue
        slug = slug_for(name)
        if path.stem != slug:
            problems.append(
                f"{_rel(path)}: slug {path.stem} does not match name {name!r} (expected {slug})"
            )
        stage = obj.get("integration_stage")
        if stage not in VALID_STAGES:
            problems.append(
                f"{_rel(path)}: integration_stage {stage!r} is not one of {', '.join(VALID_STAGES)}"
            )
        prior = by_slug.get(slug)
        if prior is not None and prior != name:
            problems.append(_collision_message(slug, prior, name))
        else:
            by_slug[slug] = name
        previous_file = seen_names.get(name)
        if previous_file is not None:
            problems.append(f"duplicate tool name {name!r} in {previous_file} and {path.name}")
        else:
            seen_names[name] = path.name
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Assemble per-tool integration stage files.")
    parser.add_argument("--dump", action="store_true", help="Print the assembled document")
    parser.add_argument("--root", default=".", help="Repo root (default: cwd)")
    args = parser.parse_args(argv)
    if not args.dump:
        parser.print_help()
        return 2
    try:
        doc = load_stages(args.root)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    sys.stdout.write(dumps(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
