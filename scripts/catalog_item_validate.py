#!/usr/bin/env python3
"""Validate catalog item v2 fields on data/toolsets.json (stdlib only; no jsonschema).

Rows that declare ``kind``, plus code-graph, core-skills, and rea, must have
the v2 required keys. Also runs pfylib.registry.validate.

Rejects manifests whose args or env *values* look like a key (reuse
pfylib.redact.looks_like_key). Fail text names the field path and does not
print the secret. ``./pfy catalog validate`` is the operator verb; this
script is also run by make eval-structural.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pfylib import registry  # noqa: E402
from pfylib.redact import looks_like_key  # noqa: E402

REQUIRED = ("id", "title", "kind", "provides", "install", "presets", "secrets")
KINDS = frozenset({"skill", "mcp", "external", "env", "bundle"})
STRATEGIES = frozenset({"native", "delegate"})
MUST = ("code-graph", "core-skills", "rea")


def secret_looking_problems(toolsets: dict) -> list[str]:
    """Problems for args/env values that look like a stored key.

    A provides.env list of names is not scanned. Env dict values and args
    list entries are. The secret itself is never included in the message.
    """
    rows = toolsets.get("toolsets") if isinstance(toolsets, dict) else None
    if not isinstance(rows, list):
        return []
    problems: list[str] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        tid = row.get("id")
        label = tid if isinstance(tid, str) and tid else "toolsets[%d]" % index
        problems.extend(_secret_walk(row, label, ""))
    return problems


def _secret_walk(obj: object, label: str, path: str) -> list[str]:
    problems: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            here = ("%s.%s" % (path, key)) if path else str(key)
            low = str(key).lower()
            if low in {"args", "argv"} and isinstance(value, list):
                for i, item in enumerate(value):
                    item_path = "%s[%d]" % (here, i)
                    if isinstance(item, str) and looks_like_key(item):
                        problems.append("%s: %s looks like a key" % (label, item_path))
                    elif isinstance(item, (dict, list)):
                        problems.extend(_secret_walk(item, label, item_path))
                continue
            if low in {"env", "environment"}:
                if isinstance(value, dict):
                    for env_key, env_val in value.items():
                        if isinstance(env_val, str) and looks_like_key(env_val):
                            problems.append(
                                "%s: %s.%s looks like a key" % (label, here, env_key)
                            )
                # A list of env *names* is not a stored key.
                continue
            problems.extend(_secret_walk(value, label, here))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            problems.extend(_secret_walk(item, label, "%s[%d]" % (path, i)))
    return problems


def _check_item(item: dict, problems: list[str]) -> None:
    tid = item.get("id")
    label = tid if isinstance(tid, str) and tid else "?"
    for key in REQUIRED:
        if key not in item:
            problems.append("%s: missing %s" % (label, key))
    if "kind" in item and item.get("kind") not in KINDS:
        problems.append("%s: illegal kind %r" % (label, item.get("kind")))
    install = item.get("install")
    strategy = install.get("strategy") if isinstance(install, dict) else None
    if "install" in item and strategy not in STRATEGIES:
        problems.append("%s: install.strategy must be native|delegate (got %r)" % (label, strategy))
    secrets = item.get("secrets")
    presets = item.get("presets")
    if "secrets" in item and not isinstance(secrets, list):
        problems.append("%s: secrets must be a list" % label)
    if "presets" in item and not isinstance(presets, list):
        problems.append("%s: presets must be a list" % label)
    if isinstance(presets, list) and presets and secrets != []:
        problems.append("%s: non-empty presets requires secrets == []" % label)


def validate_root(root: Path) -> list[str]:
    path = root / "data" / "toolsets.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ["catalog-item-v2: %s" % exc]
    rows = data.get("toolsets") if isinstance(data, dict) else None
    problems: list[str] = []
    if not isinstance(rows, list):
        problems.append("toolsets.json: toolsets[] missing")
        rows = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            problems.append("toolsets.json: non-object row")
            continue
        tid = row.get("id")
        if isinstance(tid, str):
            seen.add(tid)
        if (isinstance(tid, str) and tid in MUST) or "kind" in row:
            _check_item(row, problems)
    for iid in MUST:
        if iid not in seen:
            problems.append("missing required item %s" % iid)
    for problem in registry.validate(root_dir=root):
        problems.append("registry: %s" % problem)
    problems.extend(secret_looking_problems(data if isinstance(data, dict) else {}))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate catalog item v2 manifests.")
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repo root containing data/toolsets.json (default: this repo)",
    )
    args = parser.parse_args(argv)
    problems = validate_root(args.root.resolve())
    if problems:
        for problem in problems:
            print("FAIL %s" % problem)
        return 1
    print("PASS catalog-item-v2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
